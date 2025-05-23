"""
MCP Client Implementation
Provides client-side communication with MCP servers
"""

from typing import Dict, Any, Optional
import json
import sys
import subprocess
import threading
import asyncio
import logging
from queue import Queue, Empty
import socket
from asyncio import StreamReader, StreamWriter

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RPCError(Exception):
    """Exception raised for JSON-RPC errors."""
    def __init__(self, error_data):
        self.code = error_data.get('code')
        self.message = error_data.get('message')
        self.data = error_data.get('data')
        super().__init__(f"RPC Error {self.code}: {self.message}")

class MCPClient:
    def __init__(self, server_name: str = None, config_path: str = "server_config.json", force_stdio: bool = False, force_tcp: bool = False, tcp_host: str = None, tcp_port: int = None):
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing MCPClient with server: {server_name}")
        
        # Add detailed connection state logging
        self.connection_state = "initializing"
        self._log_connection_state()
        
        self.server_process = None
        self.tcp_reader = None
        self.tcp_writer = None
        self.request_queue = Queue()
        self.response_queue = Queue()
        self.next_request_id = 1
        self.initialized = False
        self.capabilities = set()
        self.config = self._load_config(config_path)
        self.server_name = server_name or self.config.get("default")
        self.server_info = self.config["servers"].get(self.server_name)
        
        if not self.server_info:
            raise ValueError(f"Server '{self.server_name}' not found in configuration")
        
        # Override connection type based on force flags
        if force_stdio:
            self.connection_type = "stdio"
            if "args" not in self.server_info:
                self.server_info["args"] = []
            if "--stdio" not in self.server_info["args"]:
                self.server_info["args"].append("--stdio")
        elif force_tcp:
            self.connection_type = "tcp"
            if tcp_host:
                self.server_info["host"] = tcp_host
            if tcp_port:
                self.server_info["port"] = tcp_port
        else:
            self.connection_type = self.server_info.get("type", "stdio")
            
        # Set connection parameters
        if self.connection_type == "tcp":
            self.host = self.server_info["host"]
            self.port = self.server_info["port"]
        else:
            self.server_command = self.server_info["command"]
            self.server_args = self.server_info["args"]

    def _log_connection_state(self):
        """Log detailed connection state information"""
        self.logger.info(f"Connection state: {self.connection_state}")
        if hasattr(self, 'process'):
            self.logger.debug(f"Server process state - pid: {self.process.pid if self.process else 'None'}")
            if self.process:
                self.logger.debug(f"Process returncode: {self.process.returncode}")
                self.logger.debug(f"Process poll result: {self.process.poll()}")
                if hasattr(self.process, 'stdin'):
                    self.logger.debug(f"Process stdin closed: {self.process.stdin.closed if self.process.stdin else 'N/A'}")
                if hasattr(self.process, 'stdout'):
                    self.logger.debug(f"Process stdout closed: {self.process.stdout.closed if self.process.stdout else 'N/A'}")

    async def start(self):
        """Start the connection to MCP server."""
        logger.info(f"Starting connection for {self.server_name}")
        
        self.connection_state = "starting"
        
        if self.connection_type == "tcp":
            try:
                # Connect via TCP
                reader, writer = await asyncio.open_connection(self.host, self.port)
                self.tcp_reader = reader
                self.tcp_writer = writer
                logger.info(f"TCP connection established to {self.host}:{self.port}")
                
                # Start TCP reader task
                self.reader_task = asyncio.create_task(self._read_tcp_responses())
                
            except Exception as e:
                logger.error(f"Failed to establish TCP connection: {str(e)}")
                raise
        else:
            if self.server_process:
                logger.debug("Server process already started")
                return
                
            try:
                await self._start_process()
                self.connection_state = "started"
                
            except Exception as e:
                self.connection_state = "error"
                logger.error(f"Failed to start server process: {str(e)}")
                raise
                
            # Initialize the connection
            await self.initialize()

    async def _start_process(self):
        """Start the server process with detailed process and IO management"""
        self.connection_state = "starting_process"
        self._log_connection_state()
        
        try:
            # Create startup info to prevent console window on Windows
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Start process with binary mode and appropriate buffering
            # Use 0 for unbuffered binary streams
            self.server_process = subprocess.Popen(
                [self.server_command] + self.server_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,  # Unbuffered binary streams
                startupinfo=startupinfo
            )
            
            logger.info(f"Server process started with PID: {self.server_process.pid}")
            
            # Check immediate process health
            if self.server_process.poll() is not None:
                stderr = self.server_process.stderr.read() if self.server_process.stderr else "No error output"
                raise RuntimeError(f"Server process failed to start. Exit code: {self.server_process.returncode}, Stderr: {stderr}")
            
            # Start reader thread
            self.reader_thread = threading.Thread(target=self._read_responses, daemon=True)
            self.reader_thread.start()
            logger.debug("Response reader thread started")
            
            # Wait for reader thread to be ready
            ready_event = threading.Event()
            def check_reader():
                if self.reader_thread.is_alive():
                    ready_event.set()
            
            check_thread = threading.Thread(target=check_reader)
            check_thread.start()
            if not ready_event.wait(timeout=5.0):
                raise RuntimeError("Response reader thread failed to start")
            
            # Update state after reader is confirmed ready
            self.connection_state = "process_started"
            return True
            
        except Exception as e:
            self.connection_state = "process_start_failed"
            logger.error(f"Failed to start server process: {str(e)}", exc_info=True)
            raise
    async def initialize(self):
        """Send initialize request to the server."""
        logger.info("Initializing server connection")
        if self.initialized:
            logger.debug("Server already initialized")
            return  # Already initialized
            
        try:
            initialize_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {},
                "id": self._get_next_request_id()
            }
            logger.debug(f"Sending initialize request: {initialize_request}")
            response = await self.send_request(request_data=initialize_request)
            logger.debug(f"Received initialize response: {response}")
            self._update_capabilities(response)
            self.initialized = True
            logger.info("Server initialization complete")
            return response
        except Exception as e:
            logger.error(f"Server initialization failed: {str(e)}")
            raise

    async def send_request(self, request_data: Dict = None, method: str = None, params: Any = None, timeout: float = 30.0) -> Dict:
        """Send a JSON-RPC request and wait for response"""
        if request_data is None:
            request_data = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
                "id": self._get_next_request_id()
            }
        
        client_id = f"Client-{id(self)}"
        self.logger.info(f"[CLIENT {client_id}->SERVER] Preparing request #{request_data['id']}: method={request_data['method']}")
        self.logger.debug(f"[CLIENT {client_id}->SERVER] Request parameters: {json.dumps(request_data['params'], indent=2)}")
        
        try:
            request_str = json.dumps(request_data) + "\n"
            self.logger.debug(f"[CLIENT {client_id}->SERVER] Sending request #{request_data['id']}")
            
            # Send the request based on connection type
            if self.connection_type == "tcp":
                if not self.tcp_writer:
                    raise ConnectionError("TCP connection not established")
                self.tcp_writer.write(request_str.encode())
                await self.tcp_writer.drain()
            else:
                if not self.server_process or self.server_process.stdin.closed:
                    raise ConnectionError("Server process not running or stdin closed")
                self.server_process.stdin.write(request_str.encode())
                self.server_process.stdin.flush()
                
            self.logger.info(f"[CLIENT {client_id}->SERVER] Request #{request_data['id']} sent successfully")
            
            # Wait for response with timeout
            start_time = asyncio.get_event_loop().time()
            while True:
                if (asyncio.get_event_loop().time() - start_time) > timeout:
                    raise TimeoutError(f"No response received from server within {timeout} seconds")
                
                try:
                    response = self.response_queue.get_nowait()
                    if response.get('id') == request_data['id']:
                        processing_time = asyncio.get_event_loop().time() - start_time
                        self.logger.info(f"[SERVER->CLIENT {client_id}] Response received for request #{request_data['id']} in {processing_time:.3f}s")
                        self.logger.debug(f"[SERVER->CLIENT {client_id}] Response content: {json.dumps(response, indent=2)}")
                        
                        if "error" in response:
                            self.logger.error(f"[SERVER->CLIENT {client_id}] Error in response: {response['error']}")
                            raise RPCError(response["error"])
                        
                        return response.get("result")
                except Empty:
                    await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                    continue
                
        except Exception as e:
            self.logger.error(f"[CLIENT {client_id}] Request #{request_data['id']} failed: {str(e)}", exc_info=True)
            raise

    def _read_responses(self):
        """Read responses from the server process with improved error handling"""
        logger.info("Starting response reader thread")
        self.connection_state = "handling_responses"
        
        # Buffer for incomplete lines
        partial_line = b""
        
        while self.server_process and not self.server_process.stdout.closed:
            try:
                # Read in chunks from the FileIO object
                chunk = self.server_process.stdout.read(4096)
                if not chunk:
                    rc = self.server_process.poll()
                    logger.warning(f"Server process output stream closed (EOF), return code: {rc}")
                    break
                
                # Combine with any previous partial line
                data = partial_line + chunk
                
                # Split into lines
                lines = data.split(b'\n')
                
                # The last line might be incomplete
                partial_line = lines[-1]
                
                # Process all complete lines
                for line in lines[:-1]:
                    if line:  # Skip empty lines
                        try:
                            response_str = line.decode('utf-8').strip()
                            logger.debug(f"Raw response received: {response_str}")
                            response = json.loads(response_str)
                            logger.debug(f"Parsed response: {response}")
                            self.response_queue.put(response)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse response JSON: {str(e)}, raw: {line}")
                        except Exception as e:
                            logger.error(f"Error processing response: {str(e)}", exc_info=True)
                
            except Exception as e:
                logger.error(f"Error reading response: {str(e)}", exc_info=True)
                break
        
        # Process any remaining partial line if complete
        if partial_line.endswith(b'\n'):
            try:
                response_str = partial_line[:-1].decode('utf-8').strip()
                if response_str:
                    logger.debug(f"Processing final response: {response_str}")
                    response = json.loads(response_str)
                    self.response_queue.put(response)
            except Exception as e:
                logger.error(f"Error processing final response: {str(e)}", exc_info=True)
        
        # Update connection state when reader ends
        self.connection_state = "disconnected"
        logger.info("Response reader thread ending")

    async def _read_tcp_responses(self):
        """Read responses from TCP connection."""
        logger.info("Starting TCP response reader")
        try:
            while True:
                try:
                    # Read line from TCP connection
                    line = await self.tcp_reader.readline()
                    if not line:
                        logger.warning("TCP connection closed by server")
                        break
                        
                    line_str = line.decode().strip()
                    logger.debug(f"Raw TCP response received: {line_str}")
                    
                    try:
                        response = json.loads(line_str)
                        logger.debug(f"Parsed TCP response: {response}")
                        self.response_queue.put(response)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse TCP response JSON: {str(e)}, raw: {line_str}")
                        
                except Exception as e:
                    logger.error(f"Error reading TCP response: {str(e)}")
                    break
                    
        finally:
            logger.info("TCP response reader ending")
    def _get_next_request_id(self) -> int:
        """Get the next request ID."""
        current_id = self.next_request_id
        self.next_request_id += 1
        return current_id

    def stop(self):
        """Stop the connection and clean up."""
        if self.connection_type == "tcp":
            if self.tcp_writer:
                self.tcp_writer.close()
                self.tcp_writer = None
                self.tcp_reader = None
        else:
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait()
                self.server_process = None
        self.initialized = False

    def _load_config(self, config_path: str) -> Dict:
        """Load server configuration from JSON file"""
        try:
            with open(config_path) as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Error loading config: {str(e)}")

    def can_handle(self, method: str) -> bool:
        """Check if server supports the given method"""
        return method in self.capabilities

    async def get_capabilities(self) -> set:
        """Get server capabilities from initialize response"""
        if not self.initialized:
            raise RuntimeError("Server not initialized")
        return self.capabilities
    def _update_capabilities(self, response: Dict):
        """Update capabilities from server response"""
        if isinstance(response, dict):
            # Direct response format
            if 'capabilities' in response:
                caps = response['capabilities']
                if 'supportedMethods' in caps:
                    self.capabilities.update(caps['supportedMethods'])
            # Nested response format
            elif 'result' in response and 'capabilities' in response['result']:
                caps = response['result']['capabilities']
                if 'supportedMethods' in caps:
                    self.capabilities.update(caps['supportedMethods'])
                # Also check modelProperties for model-specific capabilities
                if 'modelProperties' in caps and 'supportedMethods' in caps['modelProperties']:
                    self.capabilities.update(caps['modelProperties']['supportedMethods'])

if __name__ == "__main__":
    async def main():
        # Example usage with our MCP server
        client = MCPClient("model-server")  # Use configured server
        try:
            await client.start()
            
            # Example request
            request = {
                "jsonrpc": "2.0",
                "method": "generate",
                "params": {"ask": "Hello, how are you?"},
                "id": client._get_next_request_id()
            }
            
            response = await client.send_request(request)
            print(f"Response received: {response}")
            
        finally:
            client.stop()
    
    # Run the async main function
    asyncio.run(main())
