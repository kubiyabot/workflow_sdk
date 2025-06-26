#!/usr/bin/env python3
"""Dummy MCP server for testing the infrastructure."""

import sys
import asyncio
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from kubiya_workflow_sdk.mcp.server import create_server


async def main():
    """Run the MCP server."""
    server = create_server()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
