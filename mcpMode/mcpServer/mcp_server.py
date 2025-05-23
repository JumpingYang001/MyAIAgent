from typing import Dict, Any, Optional
import json
import sys
import asyncio
from asyncio import StreamReader, StreamWriter
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BaseMCPServer:
    def __init__(self, server_type: str = "base", version: str = "1.0.0", host: str = "localhost", port: int = 8000):
        self.server_type = server_type
        self.version = version
        self.supported_methods = set()
        self.initialized = False
        self.host = host
        self.port = port
        self.server = None
        self.initialize()
        logger.info(f"Initialized {server_type} server version {version}")

    def initialize(self):
        """Initialize the server and set up supported methods"""
        self.supported_methods.add("initialize")
        self.initialized = True
        logger.info("Server initialized with basic capabilities")

    def can_handle(self, method: str) -> bool:
        """Check if method is supported"""
        return method in self.supported_methods

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a JSON-RPC request"""
        method = request.get('method')
        params = request.get('params', {})
        logger.debug(f"Handling request - method: {method}, params: {params}")
        
        # Handle initialize request
        if method == 'initialize':
            if not self.initialized:
                self.initialize()
            response = {
                'result': {
                    'capabilities': {
                        'serverType': self.server_type,
                        'version': self.version,
                        'supportedMethods': list(self.supported_methods)
                    }
                }
            }
            logger.info(f"Initialize response: {response}")
            return response

        # Check if method is supported
        if not self.can_handle(method):
            error = {
                'error': {
                    'code': -32601,
                    'message': f'Method {method} not found or not supported'
                }
            }
            logger.warning(f"Method not supported: {method}")
            return error

        # Dispatch method to appropriate handler
        handler = getattr(self, f'handle_{method}', None)
        if handler:
            try:
                result = asyncio.get_event_loop().run_until_complete(handler(params)) if asyncio.iscoroutinefunction(handler) else handler(params)
                logger.info(f"Method {method} executed successfully")
                return {'result': result}
            except Exception as e:
                logger.error(f"Error executing method {method}: {str(e)}", exc_info=True)
                return {
                    'error': {
                        'code': -32000,
                        'message': str(e)
                    }
                }
                
        logger.error(f"Method handler not implemented: {method}")
        return {
            'error': {
                'code': -32601,
                'message': f'Method handler for {method} not implemented'
            }
        }

    async def handle_client(self, reader: StreamReader, writer: StreamWriter):
        """Handle individual client connection"""
        peer = writer.get_extra_info('peername')
        logger.info(f"New client connection from {peer}")
        request_count = 0
        
        try:
            while True:
                data = await reader.readline()
                if not data:
                    logger.info(f"Client {peer} closed connection (EOF received)")
                    break
                    
                request_count += 1
                request_str = data.decode().strip()
                logger.info(f"[{peer}] Request #{request_count} received: {request_str[:200]}{'...' if len(request_str) > 200 else ''}")
                
                try:
                    request = json.loads(request_str)
                    response = self.handle_request(request)
                    
                    # Add jsonrpc version and id if missing
                    if 'jsonrpc' not in response:
                        response['jsonrpc'] = '2.0'
                    if 'id' in request and 'id' not in response:
                        response['id'] = request['id']
                    
                    # Send response
                    response_str = json.dumps(response) + "\n"
                    writer.write(response_str.encode())
                    await writer.drain()
                    logger.info(f"[{peer}] Response sent: {response_str[:200]}{'...' if len(response_str) > 200 else ''}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"[{peer}] Invalid JSON in request #{request_count}: {str(e)}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": f"Parse error: {str(e)}"
                        },
                        "id": None
                    }
                    writer.write((json.dumps(error_response) + "\n").encode())
                    await writer.drain()
                    
        except Exception as e:
            logger.error(f"[{peer}] Connection error: {str(e)}", exc_info=True)
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f"[{peer}] Connection closed after handling {request_count} requests")

    async def start_server(self):
        """Start TCP server"""
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        
        addr = self.server.sockets[0].getsockname()
        logger.info(f'Server listening on {addr}')
        
        async with self.server:
            logger.info("Server ready to accept connections")
            await self.server.serve_forever()

    async def handle_stdio(self):
        """Handle stdio communication"""
        logger.info("Starting stdio handler")
        
        # Configure stdio for line buffering
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
        if hasattr(sys.stdin, 'reconfigure'):
            sys.stdin.reconfigure(encoding='utf-8', line_buffering=True)
            
        while True:
            try:
                # Read request synchronously
                line = sys.stdin.readline()
                if not line:
                    logger.warning("Received EOF on stdin")
                    break
                    
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    request = json.loads(line)
                    response = self.handle_request(request)
                    
                    # Add jsonrpc version and id
                    response['jsonrpc'] = '2.0'
                    if 'id' in request:
                        response['id'] = request['id']
                    
                    # Write response
                    response_str = json.dumps(response) + "\n"
                    sys.stdout.write(response_str)
                    sys.stdout.flush()
                    logger.debug(f"Response sent: {response_str.strip()}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {str(e)}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        },
                        "id": None
                    }
                    sys.stdout.write(json.dumps(error_response) + "\n")
                    sys.stdout.flush()
                    
            except Exception as e:
                logger.error(f"Fatal error in stdio handler: {str(e)}", exc_info=True)
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32099,
                        "message": f"Server error: {str(e)}"
                    },
                    "id": None
                }
                try:
                    sys.stdout.write(json.dumps(error_response) + "\n")
                    sys.stdout.flush()
                except:
                    pass
                continue
                
        logger.warning("Stdio handler loop ended")

    def run(self):
        """Run the server main loop"""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                    
                request = json.loads(line)
                response = self.handle_request(request)
                
                # Add jsonrpc version and id from request
                response['jsonrpc'] = '2.0'
                if 'id' in request:
                    response['id'] = request['id']
                
                # Write response
                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()
                
            except Exception as e:
                error_response = {
                    'jsonrpc': '2.0',
                    'error': {'code': -32603, 'message': str(e)}
                }
                if 'id' in request:
                    error_response['id'] = request['id']
                sys.stdout.write(json.dumps(error_response) + '\n')
                sys.stdout.flush()

class ModelMCPServer(BaseMCPServer):
    def __init__(self):
        super().__init__(server_type="model", version="1.0.0")
        self.model = None
        self.tokenizer = None
        logger.info("Initialized ModelMCPServer")
        
    def initialize(self):
        """Initialize model server and set supported methods"""
        super().initialize()
        self.supported_methods.add("generate")
        self.supported_methods.add("model_info")
        logger.info("Model server initialized with methods: generate, model_info")
        
    async def handle_generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle model generation request"""
        prompt = params.get("ask", "")
        logger.info(f"Handling generate request with prompt: {prompt[:100]}...")
        try:
            # TODO: Replace with actual model generation
            result = {
                "answer": f"Model response to: {prompt}"
            }
            logger.info("Generate request completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error during generate: {str(e)}", exc_info=True)
            raise
        
    async def handle_model_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return model information"""
        logger.info("Handling model_info request")
        try:
            info = {
                "modelType": "example-model",
                "capabilities": ["text-generation", "chat"]
            }
            logger.info(f"Model info: {info}")
            return info
        except Exception as e:
            logger.error(f"Error getting model info: {str(e)}", exc_info=True)
            raise

class TaskMCPServer(BaseMCPServer):
    def __init__(self):
        super().__init__(server_type="task", version="1.0.0")
        self.current_task = None
        logger.info("Initialized TaskMCPServer")
        
    def initialize(self):
        """Initialize task server and set supported methods"""
        super().initialize()
        self.supported_methods.add("handle_task")
        self.supported_methods.add("get_state")
        self.supported_methods.add("monitor_environment")
        logger.info("Task server initialized with methods: handle_task, get_state, monitor_environment")
        
    async def handle_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task execution request"""
        goal = params.get("goal", "")
        logger.info(f"Handling task request with goal: {goal}")
        try:
            # TODO: Replace with actual task handling
            self.current_task = goal
            result = {
                "status": "success",
                "result": f"Completed task: {goal}"
            }
            logger.info(f"Task completed successfully: {goal}")
            return result
        except Exception as e:
            logger.error(f"Error executing task: {str(e)}", exc_info=True)
            raise
        
    async def handle_get_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current server state"""
        logger.info("Getting current server state")
        try:
            state = {
                "status": "running",
                "activeTask": self.current_task
            }
            logger.debug(f"Current state: {state}")
            return state
        except Exception as e:
            logger.error(f"Error getting state: {str(e)}", exc_info=True)
            raise
        
    async def handle_monitor_environment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor environment state"""
        logger.info("Monitoring environment")
        try:
            status = {
                "status": "monitoring",
                "events": []
            }
            logger.debug(f"Environment status: {status}")
            return status
        except Exception as e:
            logger.error(f"Error monitoring environment: {str(e)}", exc_info=True)
            raise

# Example usage
if __name__ == "__main__":
    import argparse
    import platform
    
    # Set Windows event loop policy to use ProactorEventLoop
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    parser = argparse.ArgumentParser(description='MCP Server')
    parser.add_argument('--host', default='localhost', help='Host address to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to listen on')
    parser.add_argument('--type', choices=['base', 'model', 'task'], default='base', help='Server type')
    parser.add_argument('--stdio', action='store_true', help='Use stdio mode instead of TCP')
    args = parser.parse_args()
    
    logger.info(f"Starting {args.type} server")
    logger.info(f"Platform: {platform.system()} {platform.release()}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Mode: {'stdio' if args.stdio else 'TCP'}")
    
    # Create appropriate server instance based on type
    if args.type == 'model':
        server = ModelMCPServer()
    elif args.type == 'task':
        server = TaskMCPServer()
    else:
        server = BaseMCPServer()
    
    server.host = args.host
    server.port = args.port
    
    # Create and set event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Run server based on mode
    try:
        if args.stdio:
            logger.info("Starting server in stdio mode")
            loop.run_until_complete(server.handle_stdio())
        else:
            logger.info(f"Starting server in TCP mode on {args.host}:{args.port}")
            loop.run_until_complete(server.start_server())
    except KeyboardInterrupt:
        logger.info("Server shutting down due to keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        loop.close()
        logger.info("Server shutdown complete")
