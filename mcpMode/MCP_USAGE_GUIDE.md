# Model Context Protocol (MCP) Usage Guide

## Overview

The Model Context Protocol (MCP) system is a modular framework that integrates TinyLlama-1.1B-Chat-v1.0 for AI-powered task planning and execution. The system consists of client and server components that communicate using JSON-RPC 2.0 protocol.

## System Components

### 1. MCP Server

The server component includes several key subsystems:

- **Model Manager**: Handles TinyLlama model operations
- **Planning System**: Generates task execution plans
- **Tool Manager**: Executes various tools and commands
- **Memory System**: Manages context and task history

### 2. MCP Client

The client provides:

- Command-line interface for user interaction
- Server type switching capability
- Task submission and monitoring
- Response formatting and display

### 3. Available Server Types

1. **Agent Server**
   - Handles complex task planning
   - Manages tool execution
   - Monitors task progress

2. **Model Server**
   - Direct TinyLlama model access
   - Text generation capabilities
   - Model information queries

3. **Tool Server**
   - File operations
   - Code search and analysis
   - Command execution

4. **Planning Server**
   - Plan creation and evaluation
   - Task execution monitoring
   - Progress tracking

## Getting Started

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/MyAgent.git

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

1. Create or modify `server_config.json`. The system supports both local process communication (stdio) and network communication (tcp):
```json
{
    "servers": {
        "agent-server": {
            "type": "stdio",
            "command": "python",
            "args": ["mcpServer/agent_server.py"],
            "capabilities": ["handle_task", "get_state", "monitor_environment"]
        },
        "model-server": {
            "type": "stdio",
            "command": "python",
            "args": ["mcpServer/model_server.py"],
            "capabilities": ["generate", "model_info"]
        },
        "remote-agent-server": {
            "type": "tcp",
            "host": "remote-machine-ip",
            "port": 8000,
            "capabilities": ["handle_task", "get_state", "monitor_environment"]
        },
        "local-tcp-server": {
            "type": "tcp",
            "host": "localhost",
            "port": 8000,
            "capabilities": ["handle_task", "get_state", "monitor_environment"]
        }
    },
    "default": "agent-server"
}
```

2. Verify model configuration in `model_config.toml`:
```toml
[model]
name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
device = "auto"  # Uses CUDA if available, CPU otherwise
max_length = 2048
```

### 3. Starting the System

To start the interactive MCP system, run the following command in your terminal:

```bash
# Start with default server (agent-server)
python run.py

# Or start with a specific server
python run.py model-server
```

This will start an interactive terminal session where you can enter commands and interact with the system.

## Using the System

### 1. Available Commands

- `servers`: List available MCP servers
- `capabilities`: Show current server's capabilities
- `use <server>`: Switch to a different server
- `help`: Show command help
- `exit`/`quit`: End session

### 2. Working with Tasks

```python
# Submit a task
> Analyze the file structure of the project

# File operation task
> Read and summarize README.md

# Code analysis task
> Check src/main.py for potential errors
```

### 3. Server Switching

```python
# List available servers
> servers

# Check server capabilities
> capabilities

# Switch to model server
> use model-server

# Direct model interaction
> What is the purpose of this codebase?
```

## Server Types and Capabilities

### 1. Agent Server
- Task planning and execution
- Tool coordination
- Progress monitoring
- State management

### 2. Model Server
- Text generation
- Code completion
- Query answering
- Context understanding

### 3. Tool Server
- File operations (read/write)
- Code search and analysis
- Command execution
- Error checking

### 4. Planning Server
- Plan generation
- Task breakdown
- Execution monitoring
- Result aggregation

## Best Practices

### 1. Task Description
- Be specific about requirements
- Include relevant file paths
- Specify expected outcomes
- Provide necessary context

### 2. Server Selection
- Use agent-server for complex tasks
- Use model-server for direct AI interaction
- Use tool-server for specific operations
- Use planning-server for task planning

### 3. Error Handling
- Check task status regularly
- Review error messages
- Use appropriate fallback strategies
- Monitor resource usage

## Common Workflows

### 1. Code Analysis

```python
# Switch to agent server
> use agent-server

# Submit analysis task
> Analyze src/main.py for potential improvements
```

### 2. Model Interaction

```python
# Switch to model server
> use model-server

# Direct model query
> How can I optimize this function?
```

### 3. File Operations

```python
# List available servers
> servers
Available Servers:
* agent-server (current)
  model-server
  tool-server
  planning-server

# Switch to tool server
> use tool-server

# Tool server supports both stdio and TCP modes
# For stdio mode (defined in server_config.json):
{
    "tool-server": {
        "type": "stdio",
        "command": "python",
        "args": ["mcpServer/tool_server.py", "--stdio"],
        "capabilities": ["file_read", "file_write", "file_search", 
                        "code_search", "execute_command", "check_errors"]
    }
}

# For TCP mode, start the server:
python mcpServer/tool_server.py --host localhost --port 8000

# Then configure in server_config.json:
{
    "tool-server": {
        "type": "tcp",
        "host": "localhost",
        "port": 8000,
        "capabilities": ["file_read", "file_write", "file_search", 
                        "code_search", "execute_command", "check_errors"]
    }
}

# Common Tool Server Operations:

# 1. File Reading
> Read config.json
Reading file: config.json
{
    "setting1": "value1",
    "setting2": "value2"
}

# 2. File Search
> Search for Python files
Searching for: **/*.py
Found:
- src/main.py
- tests/test_main.py

# 3. Code Search
> Search for "initialize" function
Searching in code...
Found in:
- tool_server.py: async def initialize(self, params: Dict = None)
- model_server.py: def initialize(self)

# 4. Error Checking
> Check src/main.py for errors
Analyzing src/main.py...
No errors found.

# 5. Command Execution
> Execute 'ls -l'
Running command...
total 5
-rw-r--r-- 1 user user  234 Apr 13 12:54 README.md
-rw-r--r-- 1 user user 1234 Apr 13 12:54 config.json
```

### 4. Tool Server Communication

The tool server supports two communication modes:

1. **STDIO Mode**:
   - Direct process communication
   - Configured in server_config.json
   - Uses JSON-RPC 2.0 over standard input/output
   - Better for local operations
   - Example:
   ```json
   {
       "tool-server": {
           "type": "stdio",
           "command": "python",
           "args": ["mcpServer/tool_server.py", "--stdio"],
           "capabilities": ["file_read", "file_write", "file_search"]
       }
   }
   ```

2. **TCP Mode**:
   - Network-based communication
   - Supports remote connections
   - Uses JSON-RPC 2.0 over TCP
   - Better for distributed setups

   Setting up TCP mode requires configuration on both server and client sides:

   **Server Side Setup**:
   1. Start the server with TCP mode:
   ```bash
   # Start tool server in TCP mode
   python mcpServer/tool_server.py --host localhost --port 8000

   # Or listen on all interfaces
   python mcpServer/tool_server.py --host 0.0.0.0 --port 8000
   ```

   Expected output:
   ```
   2025-04-13 12:42:48,832 - asyncio - DEBUG - Using proactor: IocpProactor
   2025-04-13 12:42:48,844 - __main__ - INFO - Serving on ('::1', 8000, 0, 0)
   ```

   **Client Side Setup**:
   1. Configure server_config.json for TCP mode:
   ```json
   {
       "tool-server": {
           "type": "tcp",
           "host": "localhost",  # Use actual IP if connecting remotely
           "port": 8000,
           "capabilities": [
               "file_read",
               "file_write", 
               "file_search",
               "code_search",
               "execute_command",
               "check_errors"
           ]
       }
   }
   ```

   2. Use the server normally:
   ```bash
   > use tool-server
   Connected to tool-server via TCP on localhost:8000
   ```

   **Key Differences between TCP and STDIO modes**:

   1. **Configuration**:
      - TCP mode requires explicit host/port settings
      - STDIO mode uses process pipes for communication

   2. **server_config.json differences**:
      ```json
      // TCP Mode
      {
          "tool-server": {
              "type": "tcp",
              "host": "localhost",
              "port": 8000,
              "capabilities": ["file_read", "file_write", ...]
          }
      }

      // STDIO Mode
      {
          "tool-server": {
              "type": "stdio",
              "command": "python",
              "args": ["mcpServer/tool_server.py", "--stdio"],
              "capabilities": ["file_read", "file_write", ...]
          }
      }
      ```

   3. **Process Management**:
      - TCP: Server runs independently, can handle multiple clients
      - STDIO: One server process per client, direct pipe communication

   4. **Network Features**:
      - TCP: Supports remote connections, needs port forwarding
      - STDIO: Local only, no network configuration needed

   5. **Error Handling**:
      - TCP: Network-related errors need handling (timeouts, disconnects)
      - STDIO: Process-related errors (EOF, pipe breaks)

   6. **Performance**:
      - TCP: Better for multiple clients, higher latency
      - STDIO: Lower latency, but one client per process

### 5. Tool Server Capabilities

The tool server provides several key capabilities:

1. **File Operations**:
   - Reading files
   - Writing files
   - File searching
   - Pattern matching

2. **Code Analysis**:
   - Code searching
   - Error checking
   - Pattern matching in code
   - Language-specific analysis

3. **Command Execution**:
   - Shell command execution
   - Command output capture
   - Error handling
   - Process management

4. **Error Management**:
   - Syntax error checking
   - Code validation
   - Error reporting
   - Fix suggestions

### 6. STDIO Communication Details

When using STDIO mode, the following considerations are important:

1. **Buffering Configuration**:
   - Line buffering is essential for reliable communication
   - Configure both stdin and stdout properly:
   ```python
   # Server-side buffering configuration
   sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)  # Line buffering
   sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 1)  # Separate error logging
   ```

2. **Error Recovery**:
   - Server maintains operation even after errors
   - Each request is handled independently
   - Error responses follow JSON-RPC 2.0 format:
   ```json
   {
       "jsonrpc": "2.0",
       "error": {
           "code": -32099,
           "message": "Error details here"
       },
       "id": null
   }
   ```

3. **Process Management**:
   - Client monitors server process health
   - Automatic recovery from connection issues
   - Proper cleanup of resources
   - Example error handling:
   ```python
   > use tool-server
   2025-04-13 12:54:41,557 - Server process output stream closed
   2025-04-13 12:54:41,558 - Attempting reconnection...
   2025-04-13 12:54:41,559 - Successfully reconnected
   ```

4. **Debug Logging**:
   - Detailed logging for troubleshooting
   - Separate log files for server and client
   - Log rotation to manage file sizes
   - Log levels: DEBUG, INFO, WARNING, ERROR

## Network Communication

### 1. Server Setup for Network Access

To run an MCP server that accepts network connections:

```bash
# Start server listening on all interfaces (0.0.0.0)
python mcpServer/mcp_server.py --host 0.0.0.0 --port 8000

# Start server listening only on localhost
python mcpServer/mcp_server.py --host localhost --port 8000
```

### 2. Client Configuration for Network Access

To connect to a remote MCP server:

1. Add a TCP server configuration in `server_config.json`
2. Use the configured server name with the `use` command
3. The client will automatically handle the TCP connection

### 3. Security Considerations for Network Setup

When running MCP servers over the network:

- Use firewalls to restrict access to trusted IPs
- Consider using SSH tunneling for secure communication
- Monitor server logs for unauthorized access attempts
- Implement rate limiting for remote connections

### 4. Network Troubleshooting

Common network-related issues and solutions:

1. Connection Refused
   - Check if server is running
   - Verify port is not blocked by firewall
   - Ensure correct IP address and port

2. Connection Timeout
   - Check network connectivity
   - Verify server is accessible
   - Check for firewall rules

3. Connection Lost
   - Implement reconnection logic
   - Monitor network stability
   - Check server logs for issues

## Running Different Communication Protocols

The MCP system provides three different ways to run servers and clients depending on your needs:

### 1. STDIO Protocol (run_stdio.py)

The STDIO protocol is best for local development and single-client scenarios. It provides direct process communication with minimal setup:

```bash
# Start with default server
python run_stdio.py

# Start with specific server type
python run_stdio.py model-server
python run_stdio.py tool-server
python run_stdio.py agent-server
```

Benefits of STDIO mode:
- Simpler setup - no network configuration needed
- Lower latency - direct process communication
- Automatic process management
- Better for local development

### 2. TCP Server (run_tcpserver.py)

The TCP server mode allows multiple clients to connect and is suitable for networked environments:

```bash
# Start tool server on localhost
python run_tcpserver.py --type tool --host localhost --port 8000

# Start model server on all interfaces
python run_tcpserver.py --type model --host 0.0.0.0 --port 8000

# Available server types:
# - tool    (Tool Server)
# - model   (Model Server)
# - agent   (Agent Server)
# - planning (Planning Server)
```

Benefits of running as TCP server:
- Supports multiple simultaneous clients
- Network accessible
- Better for production deployments
- Can be run on different machines

### 3. TCP Client (run_tcpclient.py)

The TCP client can connect to any running TCP server:

```bash
# Connect to local server
python run_tcpclient.py --host localhost --port 8000 --type tool

# Connect to remote server
python run_tcpclient.py --host remote-server-ip --port 8000 --type model
```

Benefits of TCP client:
- Can connect to remote servers
- Supports different server types
- Network transparent
- Good for distributed setups

### Example Scenarios

1. **Local Development** (STDIO):
   ```bash
   # Simple local development setup
   python run_stdio.py tool-server
   ```

2. **Single Machine, Multiple Clients** (TCP):
   ```bash
   # Terminal 1 - Start server
   python run_tcpserver.py --type tool --host localhost --port 8000
   
   # Terminal 2 - Start first client
   python run_tcpclient.py --host localhost --port 8000 --type tool
   
   # Terminal 3 - Start second client
   python run_tcpclient.py --host localhost --port 8000 --type tool
   ```

3. **Networked Environment** (TCP):
   ```bash
   # On server machine
   python run_tcpserver.py --type model --host 0.0.0.0 --port 8000
   
   # On client machines
   python run_tcpclient.py --host server-ip --port 8000 --type model
   ```

### Configuration Requirements

1. **STDIO Mode**:
   - No special configuration needed
   - Works out of the box
   - Uses default server_config.json settings

2. **TCP Server Mode**:
   - Requires available network port
   - Firewall rules might need adjustment
   - Consider security implications if exposing to network

3. **TCP Client Mode**:
   - Requires server host and port
   - Network access to server
   - Correct server type specification

### Choosing the Right Mode

1. Use **STDIO** when:
   - Developing locally
   - Single client needed
   - Simplest setup desired
   - Maximum performance required

2. Use **TCP Server/Client** when:
   - Multiple clients needed
   - Network access required
   - Running on different machines
   - Scaling beyond single user

### Security Considerations

1. **STDIO Mode**:
   - Inherently secure - local only
   - Process isolation provided by OS
   - No network exposure

2. **TCP Mode**:
   - Use firewalls to restrict access
   - Consider using SSL/TLS
   - Implement authentication if needed
   - Monitor for unauthorized access

For more details on security and network setup, see the Security Guidelines and Network Communication sections.

## Troubleshooting

### 1. Server Issues
- Check server status
- Verify configuration
- Monitor resource usage
- Check log files

### 2. Model Problems
- Verify model downloads
- Check memory usage
- Monitor GPU status
- Review model responses

### 3. Connection Issues
- Check server process status
- Verify port availability and conflicts
- Review network settings and firewall rules
- Check file and network permissions
- Use netstat to verify listening ports
- Monitor server logs for connection attempts
- Test connectivity with basic tools (ping, telnet)
- Check for SSL/TLS certificate issues if using secure connections

## Security Guidelines

### 1. System Security
- Use secure configurations
- Monitor system access
- Review log files
- Update regularly

### 2. Data Protection
- Validate inputs
- Sanitize file paths
- Protect sensitive data
- Use proper permissions

### 3. Model Security
- Use trusted sources
- Monitor usage
- Implement rate limits
- Clean up resources

## Performance Tips

### 1. Model Optimization
- Use GPU when available
- Clean up resources
- Monitor memory usage
- Use appropriate batch sizes

### 2. Server Management
- Choose appropriate server
- Monitor resource usage
- Implement timeouts
- Cache frequent operations

### 3. Task Execution
- Break down complex tasks
- Use appropriate tools
- Monitor progress
- Handle errors properly

### 4. Network Performance
- Use connection pooling for multiple requests
- Implement request batching when possible
- Consider local caching of frequent requests
- Monitor network latency and throughput
- Use compression for large payloads
- Implement proper timeout handling
- Consider load balancing for high traffic

### 7. Tool Server Command Usage

The tool server supports the following commands that can be used directly in the interactive interface:

1. **File Reading**:
   ```
   > file_read <path>
   ```
   Reads and displays the contents of the specified file.
   Example:
   ```
   > file_read workspace/test.txt
   ```

2. **File Writing**:
   ```
   > file_write <path> <content>
   ```
   Writes the specified content to a file.
   Example:
   ```
   > file_write workspace/test.txt Hello World
   ```

3. **File Search**:
   ```
   > file_search <pattern>
   ```
   Searches for files matching the specified pattern.
   Example:
   ```
   > file_search *.py
   ```

4. **Code Search**:
   ```
   > code_search <query>
   ```
   Searches for code matching the specified query.
   Example:
   ```
   > code_search "def initialize"
   ```

5. **Command Execution**:
   ```
   > execute_command <command>
   ```
   Executes a system command and displays the output.
   Example:
   ```
   > execute_command dir
   ```

6. **Error Checking**:
   ```
   > check_errors <file>
   ```
   Checks the specified file for errors.
   Example:
   ```
   > check_errors mcpServer/tool_server.py
   ```

These commands can be used after connecting to the tool server using:
```
> use tool-server
```

Each command will return its results in a formatted panel, with success messages in green and error messages in red.

### 8. Tool Server Response Format
// ...existing code...
