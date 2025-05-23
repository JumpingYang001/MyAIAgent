#!/usr/bin/env python
"""
STDIO Client for MCP system
Communicates with MCP server using standard input/output
"""

import asyncio
import sys
import logging
import argparse
import os
from mcpClient.agent_client import AgentClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stdio_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description='STDIO client for MCP system')
    parser.add_argument('server_type', nargs='?', help='Type of server to connect to')
    args = parser.parse_args()

    try:
        # Use absolute path for config
        config_path = os.path.join(os.path.dirname(__file__), 'mcpClient', 'server_config.json')
        logger.info("Starting client in STDIO mode")
        client = AgentClient(args.server_type, force_stdio=True, config_path=config_path)
        await client.start()
    except KeyboardInterrupt:
        logger.info("Client terminated by user")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
