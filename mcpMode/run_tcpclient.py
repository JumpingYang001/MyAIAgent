#!/usr/bin/env python
"""
TCP Client for MCP system
Connects to an MCP server over TCP
"""

import asyncio
import sys
import logging
import argparse
from mcpClient.agent_client import AgentClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tcp_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='MCP TCP Client')
    parser.add_argument('--host', default='localhost', help='Server host to connect to')
    parser.add_argument('--port', type=int, default=8000, help='Server port to connect to')
    parser.add_argument('--type', default=None, help='Server type to connect to')
    args = parser.parse_args()
    
    try:
        # Initialize and start client with TCP mode
        logger.info(f"Starting TCP client connecting to {args.host}:{args.port}")
        client = AgentClient(args.type, force_tcp=True, tcp_host=args.host, tcp_port=args.port)
        await client.start()
    except KeyboardInterrupt:
        logger.info("Shutting down due to keyboard interrupt...")
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
