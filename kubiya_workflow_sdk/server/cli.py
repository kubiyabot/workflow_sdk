"""CLI entry point for the Kubiya Workflow SDK server."""

import asyncio
import argparse
import sys
import os
from typing import Optional

import uvicorn

from .app import create_server


def main(argv: Optional[list] = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Kubiya Workflow SDK Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("HOST", "127.0.0.1"),
        help="Host to bind to (default: 127.0.0.1)",
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port to bind to (default: 8000)",
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("RELOAD", "false").lower() == "true",
        help="Enable auto-reload for development",
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default=os.getenv("LOG_LEVEL", "info"),
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Log level (default: info)",
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("WORKERS", "1")),
        help="Number of worker processes (default: 1)",
    )
    
    args = parser.parse_args(argv)
    
    # Create the app
    app = create_server()
    
    # Run the server
    try:
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level,
            workers=args.workers if not args.reload else 1,
            access_log=True,
        )
        return 0
    except KeyboardInterrupt:
        print("\nShutting down server...")
        return 0
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 