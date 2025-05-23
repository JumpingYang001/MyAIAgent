# MCP Client

This is a Model Context Protocol (MCP) client implementation that can communicate with MCP servers using JSON-RPC 2.0 protocol.

## Features

- Full MCP client implementation with JSON-RPC 2.0 support
- Asynchronous response handling using threading
- Clean server process management
- Request/Response queue system
- Automatic request ID management
- Error handling

## Setup

1. Install the requirements:
```bash
pip install -r requirements.txt
```

## Usage

```python
from mcp_client import MCPClient

# Create a client instance with server command and arguments
client = MCPClient("python", ["path/to/your/mcp_server.py"])

try:
    # Start the client (this will also initialize the server)
    client.start()
    
    # Send a request to the server
    request = {
        "jsonrpc": "2.0",
        "method": "yourMethod",
        "params": {"key": "value"},
        "id": client._get_next_id()
    }
    
    response = client.send_request(request)
    print(f"Response received: {response}")
    
finally:
    # Clean up resources
    client.stop()
```
