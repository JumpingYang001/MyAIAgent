# Custom MCP Server

This is a Model Context Protocol (MCP) server implementation that provides a basic framework for handling MCP requests.

## Setup

1. Install the requirements:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python mcp_server.py
```

## Features

- Basic MCP server implementation
- Handles initialize requests
- Implements JSON-RPC 2.0 protocol
- Error handling for unknown methods

## Development

The server is configured to run as a stdio-based server and can be debugged using VS Code's built-in debugging capabilities.
