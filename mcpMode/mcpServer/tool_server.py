"""
Tool Server Implementation for MCP
Provides a JSON-RPC 2.0 interface for file operations, code search, and command execution
"""

import sys
import json
import logging
import asyncio
import os
import glob
import subprocess
import platform
from typing import Dict, Any, List, Optional

# Set Windows event loop policy before anything else
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Setup logging with more detailed formatting
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'tool_server.log')
os.makedirs(log_dir, exist_ok=True)  # Ensure directory exists

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d - %(name)s - [%(levelname)s] - %(threadName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file, mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger('tool_server')

class ToolServer:
    def __init__(self):
        logger.info("Initializing ToolServer instance")
        self.initialized = False
        self.start_time = None
        self.methods = {
            'initialize': self.initialize,
            'file_read': self.handle_file_read,
            'file_write': self.handle_file_write,
            'file_search': self.handle_file_search,
            'code_search': self.handle_code_search,
            'execute_command': self.handle_execute_command,
            'check_errors': self.handle_check_errors
        }
        logger.info(f"Registered {len(self.methods)} methods: {', '.join(self.methods.keys())}")
        logger.debug(f"Server instance created in memory at {hex(id(self))}")
    async def start(self, loop=None):
        """Start the server and set the start time using the provided or current event loop"""
        self.start_time = (loop or asyncio.get_running_loop()).time()
        logger.debug(f"Server start time set to {self.start_time}")
        
        # Auto-initialize when starting
        if not self.initialized:
            await self.initialize()

    async def initialize(self, params: Dict = None) -> Dict:
        """Initialize the tool server"""
        try:
            logger.info("Received initialize request")
            logger.debug(f"Initialize params: {params}")
            
            # Step 1: Set initialized flag
            logger.debug("Setting initialized flag")
            self.initialized = True
            
            # Step 2: Prepare capabilities response
            logger.debug("Preparing capabilities response")
            capabilities = {
                "capabilities": {
                    "serverType": "tool-server",
                    "version": "1.0.0",
                    "supportedMethods": list(self.methods.keys())
                }
            }
            logger.info(f"Server initialized with capabilities: {capabilities}")
            
            # Step 3: Return response
            logger.debug("Returning initialize response")
            return capabilities
            
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}", exc_info=True)
            raise
        
    async def handle_file_read(self, params: Dict) -> Dict:
        """Read file contents"""
        try:
            path = params.get('path')
            logger.info(f"Received file read request for path: {path}")
            if not path or not os.path.exists(path):
                raise ValueError(f"Invalid or nonexistent path: {path}")
                
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.debug(f"File read successfully: {path}")
            return {"content": content}
        except Exception as e:
            logger.error(f"File read error: {str(e)}")
            raise
            
    async def handle_file_write(self, params: Dict) -> Dict:
        """Write content to file"""
        try:
            path = params.get('path')
            content = params.get('content')
            logger.info(f"Received file write request for path: {path}")
            if not path or content is None:
                raise ValueError("Missing path or content")
                
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.debug(f"File written successfully: {path}")
            return {"success": True}
        except Exception as e:
            logger.error(f"File write error: {str(e)}")
            raise
            
    async def handle_file_search(self, params: Dict) -> Dict:
        """Search for files matching pattern"""
        try:
            pattern = params.get('pattern')
            logger.info(f"Received file search request for pattern: {pattern}")
            if not pattern:
                raise ValueError("Missing search pattern")
              # Convert Windows path separators if present
            pattern = pattern.replace('\\', '/')
            
            # If pattern doesn't include directory traversal, search everywhere
            if '/' not in pattern:
                pattern = '**/' + pattern
            
            matches = []
            try:
                for file in glob.glob(pattern, recursive=True):
                    # Convert to relative path and normalize separators
                    rel_path = os.path.relpath(file).replace('\\', '/')
                    matches.append(rel_path)
                
                logger.debug(f"File search found {len(matches)} matches")
                logger.debug(f"Matches: {matches}")
                return {"files": matches}
                
            except Exception as glob_error:
                logger.error(f"Glob error: {str(glob_error)}")
                raise ValueError(f"Pattern matching failed: {str(glob_error)}")
                
        except Exception as e:
            logger.error(f"File search error: {str(e)}")
            raise
            
    async def handle_code_search(self, params: Dict) -> Dict:
        """Search code contents"""
        try:
            query = params.get('query')
            file_pattern = params.get('filePattern', '**/*.{py,js,ts,java,cpp,c,h,hpp}')
            logger.info(f"Received code search request for query: {query}, file pattern: {file_pattern}")
            
            if not query:
                raise ValueError("Missing search query")
                
            results = []
            for file in glob.glob(file_pattern, recursive=True):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if query.lower() in content.lower():
                            results.append({
                                "file": file,
                                "content": content
                            })
                except Exception as e:
                    logger.warning(f"Error reading file {file}: {str(e)}")
                    
            logger.debug(f"Code search results: {results}")
            return {"results": results}
        except Exception as e:
            logger.error(f"Code search error: {str(e)}")
            raise
            
    async def handle_execute_command(self, params: Dict) -> Dict:
        """Execute shell command"""
        try:
            command = params.get('command')
            logger.info(f"Received command execution request: {command}")
            if not command:
                raise ValueError("Missing command")
                
            # Execute command and capture output
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            logger.debug(f"Command execution completed with exit code {process.returncode}")
            return {
                "exitCode": process.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else ""
            }
        except Exception as e:
            logger.error(f"Command execution error: {str(e)}")
            raise
            
    async def handle_check_errors(self, params: Dict) -> Dict:
        """Check for code errors in files"""
        try:
            files = params.get('files', [])
            logger.info(f"Received check errors request for files: {files}")
            if not files:
                raise ValueError("No files specified")
                
            errors = []
            for file in files:
                # For Python files, use pylint
                if file.endswith('.py'):
                    try:
                        process = await asyncio.create_subprocess_shell(
                            f"pylint {file}",
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await process.communicate()
                        if stdout:
                            errors.append({
                                "file": file,
                                "errors": stdout.decode()
                            })
                    except Exception as e:
                        logger.warning(f"Error checking {file}: {str(e)}")
                        
            logger.debug(f"Check errors results: {errors}")
            return {"errors": errors}
        except Exception as e:
            logger.error(f"Error checking error: {str(e)}")
            raise
            
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle individual client connection"""
        peer = writer.get_extra_info('peername')
        client_id = f"{peer[0]}:{peer[1]}" if peer else "unknown"
        logger.info(f"[SERVER->CLIENT {client_id}] New client connection established")
        request_count = 0
        
        try:
            while True:
                try:
                    # Read request line with timeout
                    logger.debug(f"[SERVER] Waiting for request from client {client_id}...")
                    data = await asyncio.wait_for(reader.readline(), timeout=30.0)
                    if not data:
                        logger.info(f"[CLIENT {client_id}->SERVER] Connection closed (EOF received)")
                        break
                    
                    request_count += 1
                    request_str = data.decode().strip()
                    logger.info(f"[CLIENT {client_id}->SERVER] Request #{request_count} received: {request_str[:200]}{'...' if len(request_str) > 200 else ''}")
                    
                    start_time = asyncio.get_event_loop().time()
                    try:
                        request = json.loads(request_str)
                        method = request.get('method')
                        params = request.get('params', {})
                        request_id = request.get('id')
                        
                        logger.debug(f"[SERVER] Processing request from {client_id} - Method: {method}, ID: {request_id}")
                        logger.debug(f"[SERVER] Request parameters from {client_id}: {json.dumps(params, indent=2)}")
                        
                        if method in self.methods:
                            result = await self.methods[method](params)
                            response = {
                                "jsonrpc": "2.0",
                                "result": result,
                                "id": request_id
                            }
                        else:
                            logger.warning(f"[SERVER] Method not found for client {client_id}: {method}")
                            response = {
                                "jsonrpc": "2.0",
                                "error": {
                                    "code": -32601,
                                    "message": f"Method {method} not found"
                                },
                                "id": request_id
                            }
                        
                        # Calculate and log processing time
                        processing_time = asyncio.get_event_loop().time() - start_time
                        logger.info(f"[SERVER] Request from {client_id} completed in {processing_time:.3f}s")
                        
                        # Send response
                        logger.debug(f"[SERVER->CLIENT {client_id}] Preparing to send response...")
                        response_str = json.dumps(response) + "\n"
                        writer.write(response_str.encode())
                        await writer.drain()
                        logger.info(f"[SERVER->CLIENT {client_id}] Response sent for request #{request_count}: {response_str[:200]}{'...' if len(response_str) > 200 else ''}")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"[CLIENT {client_id}->SERVER] Invalid JSON in request #{request_count}: {str(e)}")
                        error_response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32700,
                                "message": f"Parse error: {str(e)}"
                            },
                            "id": None
                        }
                        logger.debug(f"[SERVER->CLIENT {client_id}] Sending error response for invalid JSON")
                        writer.write((json.dumps(error_response) + "\n").encode())
                        await writer.drain()
                        
                except asyncio.TimeoutError:
                    logger.warning(f"[CLIENT {client_id}->SERVER] Request timeout after 30 seconds")
                    break
                    
        except Exception as e:
            logger.error(f"[SERVER] Connection error with client {client_id}: {str(e)}", exc_info=True)
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f"[SERVER] Connection with client {client_id} closed after handling {request_count} requests")

    async def handle_stdio(self):
        """Handle stdio communication"""
        logger.info("Starting server in stdio communication mode")
        
        # Configure binary mode for Windows
        if sys.platform == 'win32':
            import msvcrt
            msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
            msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)
            
        request_count = 0
        
        # Wait for and process requests
        while True:
            try:
                # Read request
                line = sys.stdin.buffer.readline()
                if not line:
                    logger.warning("Received EOF on stdin")
                    break
                
                request_count += 1
                request_str = line.decode('utf-8').strip()
                logger.info(f"Request #{request_count} received: {request_str}")
                
                try:
                    # Parse request
                    request = json.loads(request_str)
                    method = request.get('method')
                    params = request.get('params', {})
                    request_id = request.get('id')
                    
                    # Handle request
                    try:
                        result = await self.methods[method](params)
                        response = {
                            "jsonrpc": "2.0",
                            "result": result,
                            "id": request_id
                        }
                    except KeyError:
                        response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32601,
                                "message": f"Method {method} not found"
                            },
                            "id": request_id
                        }
                    except Exception as e:
                        response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32000,
                                "message": str(e)
                            },
                            "id": request_id
                        }
                        
                    # Send response
                    response_str = json.dumps(response) + "\n"
                    response_bytes = response_str.encode('utf-8')
                    sys.stdout.buffer.write(response_bytes)
                    sys.stdout.buffer.flush()
                    logger.info(f"Response sent for request #{request_count}")
                    
                except json.JSONDecodeError as e:
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": f"Parse error: {str(e)}"
                        },
                        "id": None
                    }
                    error_bytes = (json.dumps(error_response) + "\n").encode('utf-8')
                    sys.stdout.buffer.write(error_bytes)
                    sys.stdout.buffer.flush()
                    
            except Exception as e:
                logger.error(f"Fatal error in stdio handler: {str(e)}", exc_info=True)
                try:
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32099,
                            "message": f"Server error: {str(e)}"
                        },
                        "id": None
                    }
                    error_bytes = (json.dumps(error_response) + "\n").encode('utf-8')
                    sys.stdout.buffer.write(error_bytes)
                    sys.stdout.buffer.flush()
                except Exception as write_error:
                    logger.critical(f"Failed to write error response: {str(write_error)}", exc_info=True)
                continue  # Keep server running even after errors
                
        logger.warning(f"Stdio handler loop ended after processing {request_count} requests")
        
    def _write_response(self, response: Dict):
        """Helper method to write JSON-RPC response to stdout"""
        try:
            response_str = json.dumps(response) + "\n"
            logger.debug(f"Preparing to write response [{len(response_str)} chars]")
            logger.debug(f"Response content: {response_str[:100]}{'...' if len(response_str) > 100 else ''}")
            logger.debug(f"stdout state before write - closed: {sys.stdout.closed}, isatty: {sys.stdout.isatty()}")
            
            sys.stdout.write(response_str)
            sys.stdout.flush()
            
            logger.debug("Response written and flushed successfully")
            logger.debug(f"stdout state after write - closed: {sys.stdout.closed}, isatty: {sys.stdout.isatty()}")
        except Exception as e:
            logger.error(f"Error writing response: {str(e)}", exc_info=True)
            # Try to log the failed response for debugging
            logger.error(f"Failed response content: {json.dumps(response, indent=2)}")

async def start_server(host: str = 'localhost', port: int = 8000):
    """Start the TCP server"""
    logger.info(f"Starting TCP server on {host}:{port}")
    server = ToolServer()
    
    async def handle_client_wrapper(reader, writer):
        await server.handle_client(reader, writer)
    
    try:
        tcp_server = await asyncio.start_server(
            handle_client_wrapper,
            host,
            port
        )
        
        addr = tcp_server.sockets[0].getsockname()
        logger.info(f'Server successfully bound and listening on {addr}')
        logger.info(f'Server process ID: {os.getpid()}')
        logger.info(f'Python version: {sys.version}')
        
        async with tcp_server:
            logger.info("Server ready to accept connections")
            await tcp_server.serve_forever()
    except Exception as e:
        logger.error(f"Critical server error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    import argparse
    import platform
    import msvcrt
    
    try:
        # Log system information
        logger.info(f"Starting tool server on {platform.system()} {platform.release()}")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {os.getcwd()}")
        
        parser = argparse.ArgumentParser()
        parser.add_argument('--host', default='localhost')
        parser.add_argument('--port', type=int, default=8000)
        parser.add_argument('--stdio', action='store_true', help='Use stdio for communication')
        args = parser.parse_args()
        
        logger.info(f"Parsed command line arguments: {vars(args)}")
        
        # Configure stdio if needed
        if args.stdio:
            logger.info("Configuring stdio mode")
            
            # Configure binary mode for stdin/stdout on Windows
            if sys.platform == 'win32':
                msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
                msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
                msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)
                logger.debug("Configured binary mode for Windows")
            
            # Set up event loop
            if platform.system() == 'Windows':
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create and start server
            server = ToolServer()
            logger.info("Created ToolServer instance")
            
            try:
                loop.run_until_complete(server.start(loop))
                logger.info("Server initialization complete")
                loop.run_until_complete(server.handle_stdio())
            except KeyboardInterrupt:
                logger.info("Server stopped by user")
            except Exception as e:
                logger.error(f"Server error: {str(e)}", exc_info=True)
            finally:
                loop.close()
        else:
            asyncio.run(start_server(args.host, args.port))
            
    except Exception as e:
        logger.critical(f"Critical startup error: {str(e)}", exc_info=True)
        sys.exit(1)
