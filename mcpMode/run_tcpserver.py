#!/usr/bin/env python
"""
TCP Server for MCP system
Starts a server that listens for TCP connections
"""

import asyncio
import sys
import logging
import argparse
import platform
from mcpServer.tool_server import ToolServer
from mcpServer.model_server import ModelServer
from mcpServer.agent_server import AgentServer
from mcpServer.planning_system import PlanningServer

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tcp_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_server_class(server_type):
    """Get the appropriate server class based on type"""
    server_types = {
        'tool': ToolServer,
        'model': ModelServer,
        'agent': AgentServer,
        'planning': PlanningServer
    }
    return server_types.get(server_type)

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='MCP TCP Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to listen on')
    parser.add_argument('--type', choices=['tool', 'model', 'agent', 'planning'],
                      default='tool', help='Server type')
    args = parser.parse_args()
    
    # Set Windows event loop policy if needed
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        # Create and start server
        logger.info(f"Starting {args.type} server on {args.host}:{args.port}")
        ServerClass = get_server_class(args.type)
        if not ServerClass:
            raise ValueError(f"Invalid server type: {args.type}")
            
        server = ServerClass()
        
        # Create event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Initialize and start server
        await server.start(loop)
        if hasattr(server, 'start_server'):
            await server.start_server(args.host, args.port)
        else:
            logger.error("Server class does not implement start_server method")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down due to keyboard interrupt...")
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
