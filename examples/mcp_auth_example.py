#!/usr/bin/env python3
"""
Example: Kubiya MCP Server with OAuth/OIDC Authentication

This example demonstrates how to set up a Kubiya MCP server with proper
authentication using OAuth 2.0 or OpenID Connect providers.
"""

import os
import asyncio
import logging
from kubiya_workflow_sdk.mcp.server_auth import create_mcp_server_auth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """Run MCP server with authentication."""
    
    # Example 1: Using Auth0
    print("Example 1: Auth0 Configuration")
    print("-" * 50)
    
    # Create server with Auth0
    server = create_mcp_server_auth(
        name="Kubiya MCP Server (Auth0)",
        auth_server_url="https://your-tenant.auth0.com",
        auth_server_type="oidc",
        required_scopes=["read", "write", "execute"]
    )
    
    print("Server configured with Auth0")
    print("Metadata endpoint: /.well-known/oauth-authorization-server")
    print("Required scopes: read, write, execute")
    print()
    
    # Example 2: Using Okta
    print("Example 2: Okta Configuration")
    print("-" * 50)
    
    server_okta = create_mcp_server_auth(
        name="Kubiya MCP Server (Okta)",
        auth_server_url="https://your-domain.okta.com/oauth2/default",
        auth_server_type="oauth",
        required_scopes=["workflows:read", "workflows:write", "workflows:execute"]
    )
    
    print("Server configured with Okta")
    print()
    
    # Example 3: Using environment variables
    print("Example 3: Environment-based Configuration")
    print("-" * 50)
    
    # Set environment variables
    os.environ["KUBIYA_AUTH_SERVER"] = "https://auth.example.com"
    
    server_env = create_mcp_server_auth(
        name="Kubiya MCP Server",
        auth_server_url=os.getenv("KUBIYA_AUTH_SERVER"),
        auth_server_type="oidc"
    )
    
    print("Server configured from environment")
    print(f"Auth server: {os.getenv('KUBIYA_AUTH_SERVER')}")
    print()
    
    # Create Starlette app
    app = server.create_app()
    
    # Example JWT claims structure
    print("Example JWT Claims Structure:")
    print("-" * 50)
    print("""
{
  "sub": "user123",
  "name": "John Doe",
  "email": "john@example.com",
  "scope": "read write execute",
  "kubiya_api_key": "kb-1234567890abcdef",  // Include Kubiya API key here
  "iat": 1677654321,
  "exp": 1677657921
}
    """)
    
    print("\nTo run the server:")
    print("1. With uvicorn:")
    print("   uvicorn examples.mcp_auth_example:app --host 0.0.0.0 --port 8000")
    print()
    print("2. With command line:")
    print("   python -m kubiya_workflow_sdk.mcp.server_auth --auth-server https://your-auth.com")
    print()
    print("3. Test authentication:")
    print("   curl -H 'Authorization: Bearer YOUR_JWT_TOKEN' http://localhost:8000/")

if __name__ == "__main__":
    asyncio.run(main())

# For uvicorn
app = create_mcp_server_auth(
    auth_server_url=os.getenv("KUBIYA_AUTH_SERVER", "https://auth.example.com")
).create_app() 