"""Run the Kubiya MCP Server."""

import argparse
import logging
import os
import sys

from .core import create_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)


def main():
    """Main entry point for the MCP server."""
    parser = argparse.ArgumentParser(
        description="Kubiya MCP Server - Smart workflow compilation and execution"
    )
    
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="Transport type (default: stdio)"
    )
    
    parser.add_argument(
        "--name",
        default="Kubiya Workflow MCP",
        help="Server name"
    )
    
    parser.add_argument(
        "--base-url",
        default="https://api.kubiya.ai",
        help="Kubiya API base URL"
    )
    
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Disable authentication (not recommended for production)"
    )
    
    parser.add_argument(
        "--runner",
        default="kubiya-hosted",
        help="Default runner name"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP/SSE transport (default: 8000)"
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for HTTP/SSE transport (default: 0.0.0.0)"
    )
    
    args = parser.parse_args()
    
    # Create server
    server = create_server(
        name=args.name,
        base_url=args.base_url,
        enable_auth=not args.no_auth,
        default_runner=args.runner
    )
    
    # Log configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {args.name}")
    logger.info(f"Transport: {args.transport}")
    logger.info(f"Base URL: {args.base_url}")
    logger.info(f"Authentication: {'enabled' if not args.no_auth else 'disabled'}")
    logger.info(f"Default runner: {args.runner}")
    
    # Check for API key
    if not args.no_auth and not os.getenv("KUBIYA_API_KEY"):
        logger.warning(
            "No KUBIYA_API_KEY environment variable found. "
            "Authentication will rely on HTTP headers or explicit parameters."
        )
    
    # Run based on transport
    if args.transport == "stdio":
        logger.info("Running in stdio mode - connect via MCP client")
        server.run("stdio")
    elif args.transport == "http":
        logger.info(f"Starting HTTP server on {args.host}:{args.port}")
        # For HTTP mode, we'd need to wrap with FastAPI
        # This is handled by the FastMCP framework
        server.run("http")
    elif args.transport == "sse":
        logger.info(f"Starting SSE server on {args.host}:{args.port}")
        server.run("sse")


if __name__ == "__main__":
    main() 