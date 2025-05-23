"""
Agent Interface Client Implementation using MCP
Provides a user interface that communicates with the MCP server
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress
from rich.prompt import Prompt
import aioconsole
from mcpClient.mcp_client import MCPClient
from mcpClient.server_manager import ServerManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Setup rich console
console = Console()

class AgentClient:
    def __init__(self, server_type: str = None, force_stdio: bool = False, force_tcp: bool = False, 
                 tcp_host: str = None, tcp_port: int = None, config_path: str = None):
        """Initialize the agent client"""
        self.server_type = server_type
        self.current_server = server_type
        self.force_stdio = force_stdio
        self.force_tcp = force_tcp
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.config_path = config_path
        
        # Initialize server manager
        self.server_manager = ServerManager(config_path=self.config_path)
        
        # Initialize client with specific communication mode
        if force_stdio:
            self.client = MCPClient(server_type, config_path=self.config_path, force_stdio=True)
        elif force_tcp:
            self.client = MCPClient(server_type, config_path=self.config_path, force_tcp=True, tcp_host=tcp_host, tcp_port=tcp_port)
        else:
            self.client = MCPClient(server_type, config_path=self.config_path)
        
    async def start(self):
        """Start the agent client"""
        try:            
            await self.client.start()
            
            console.print("[bold blue]AI Agent Interface[/bold blue]")
            console.print("Type 'exit' to end the session\n")
            
            while True:
                try:
                    user_input = await aioconsole.ainput("> ")
                    input_lower = user_input.lower()
                    
                    if input_lower in ['exit', 'quit']:
                        break
                    elif input_lower == 'servers':
                        # List available servers
                        servers = self.list_available_servers()
                        console.print("\n[bold]Available Servers:[/bold]")
                        for server in servers:
                            if server == self.current_server:
                                console.print(f"* [green]{server}[/green] (current)")
                            else:
                                console.print(f"  {server}")
                        continue
                    elif input_lower == 'capabilities':
                        # Show current server capabilities
                        caps = await self.get_server_capabilities()
                        console.print("\n[bold]Current Server Capabilities:[/bold]")
                        for cap in caps:
                            console.print(f"- {cap}")
                        continue
                    elif input_lower.startswith('use '):
                        # Switch to a different server
                        server_name = input_lower[4:].strip()
                        await self.switch_server(server_name)
                        continue
                    elif input_lower == 'help':
                        await self.show_help()
                        continue
                    
                    # Handle tool server commands
                    capabilities = await self.client.get_capabilities()
                    method = None
                    params = {}
                    
                    # Parse command and parameters
                    parts = user_input.split(maxsplit=1)
                    command = parts[0].lower()
                    args = parts[1] if len(parts) > 1 else ""
                    
                    # Map commands to tool server methods
                    if command == "file_read" and "file_read" in capabilities:
                        method = "file_read"
                        params = {"path": args.strip()}
                    elif command == "file_write" and "file_write" in capabilities:
                        try:
                            filepath, content = args.split(maxsplit=1)
                            method = "file_write"
                            params = {"path": filepath.strip(), "content": content}
                        except ValueError:
                            console.print("[red]Error: file_write requires both path and content[/red]")
                            continue
                    elif command == "file_search" and "file_search" in capabilities:
                        method = "file_search"
                        params = {"pattern": args.strip()}
                    elif command == "code_search" and "code_search" in capabilities:
                        method = "code_search"
                        params = {"query": args.strip()}
                    elif command == "execute_command" and "execute_command" in capabilities:
                        method = "execute_command"
                        params = {"command": args.strip()}
                    elif command == "check_errors" and "check_errors" in capabilities:
                        method = "check_errors"
                        params = {"file": args.strip() if args else None}
                    elif "generate" in capabilities:
                        method = "generate"
                        params = {"ask": user_input}
                    else:
                        console.print("[red]Command not supported. Type 'help' to see available commands.[/red]")
                        continue

                    if method:
                        with Progress() as progress:
                            task = progress.add_task("[cyan]Processing request...", total=1)
                            
                            # Send request to server
                            request = {
                                "jsonrpc": "2.0",
                                "method": method,
                                "params": params,
                                "id": self.client._get_next_request_id()
                            }
                            
                            response = await self.client.send_request(request)
                            progress.update(task, completed=1)
                              # Handle response
                            if "result" in response:
                                result = response["result"]
                                if method == "file_search" and isinstance(result, dict) and "files" in result:
                                    console.print("[green]Found files:[/green]")
                                    for file in result["files"]:
                                        console.print(f"- {file}")
                                elif isinstance(result, dict):
                                    console.print(Panel(
                                        Markdown(str(result)),
                                        border_style="green"
                                    ))
                                else:
                                    console.print(Panel(
                                        str(result),
                                        border_style="green"
                                    ))
                            elif "error" in response:
                                error = response["error"]
                                console.print(Panel(
                                    f"Error: {error.get('message', 'Unknown error')}",
                                    border_style="red"
                                ))
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Error: {str(e)}")
                    console.print(f"[red]Error: {str(e)}[/red]")
                    
        finally:
            # Clean up resources
            self.client.stop()
            
    async def switch_server(self, server_name: str) -> bool:
        """Switch to a different MCP server"""
        servers = ServerManager().get_available_servers()
        if server_name not in servers:
            console.print(f"[red]Server '{server_name}' not available[/red]")
            return False
            
        try:
            # Clean up current client
            if self.client:
                self.client.stop()
            
            # Initialize new client with same force flags
            self.client = MCPClient(server_name, force_stdio=self.force_stdio, force_tcp=self.force_tcp)
            await self.client.start()
            self.current_server = server_name
            
            # Get and display capabilities
            caps = await self.get_server_capabilities()
            console.print(f"[green]Successfully switched to server: {server_name}[/green]")
            console.print("[cyan]Server capabilities:[/cyan]")
            for cap in caps:
                console.print(f"  - {cap}")
            return True
            
        except Exception as e:
            console.print(f"[red]Error switching to server {server_name}: {str(e)}[/red]")
            # Try to revert to previous server
            if self.current_server and self.current_server != server_name:
                self.client = MCPClient(self.current_server)
                await self.client.start()
            return False
        
    def list_available_servers(self) -> List[str]:
        """Get list of available servers"""
        return self.server_manager.list_servers()
        
    async def get_server_capabilities(self) -> List[str]:
        """Get capabilities of current server"""
        if not self.client:
            return []
        return list(await self.client.get_capabilities())

    async def show_help(self):
        """Show help message with available commands"""
        console.print("\n[bold]Available Commands:[/bold]")
        console.print("- servers: List available MCP servers")
        console.print("- capabilities: Show current server capabilities")
        console.print("- use <server>: Switch to a different server")
        console.print("- help: Show this help message")
        console.print("- exit/quit: End the session\n")

        # Get current server capabilities
        capabilities = await self.client.get_capabilities()
        if capabilities:
            console.print("[bold]Tool Server Commands:[/bold]")
            if "file_read" in capabilities:
                console.print("- file_read <path>: Read contents of a file")
            if "file_write" in capabilities:
                console.print("- file_write <path> <content>: Write content to a file")
            if "file_search" in capabilities:
                console.print("- file_search <pattern>: Search for files matching pattern")
            if "code_search" in capabilities:
                console.print("- code_search <query>: Search code contents")
            if "execute_command" in capabilities:
                console.print("- execute_command <command>: Execute a shell command")
            if "check_errors" in capabilities:
                console.print("- check_errors [file]: Check for errors in file(s)")
            if "generate" in capabilities:
                console.print("- <text>: Generate response using AI model")
            console.print("")

async def main():
    client = AgentClient()
    await client.start()

if __name__ == "__main__":
    asyncio.run(main())
