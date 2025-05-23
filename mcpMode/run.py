#!/usr/bin/env python
"""
Interactive terminal for MCP system
"""

import asyncio
from mcpClient.agent_client import AgentClient

async def main():
    # Get server type from command line or use default
    import sys
    server_type = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        # Initialize and start client
        client = AgentClient(server_type)
        await client.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
