"""
Example MCP Server - Demonstrates all features working end-to-end.

Run with: python example_server.py
Test with: python test_client.py
"""

import asyncio
from kubiya_workflow_sdk.mcp import FastMCP, create_mcp_server
from kubiya_workflow_sdk.dsl import workflow, step


# Create MCP server
mcp = create_mcp_server("My DevOps Automation Server")


# Add custom tools beyond the built-ins
@mcp.tool
def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}! Welcome to Kubiya MCP."


@mcp.tool
async def deploy_status(service: str) -> dict:
    """Check deployment status of a service."""
    # Simulate checking deployment
    await asyncio.sleep(0.5)
    return {
        "service": service,
        "status": "healthy",
        "version": "2.1.0",
        "uptime": "3 days",
        "replicas": 3
    }


@mcp.tool(description="Create a deployment workflow from template")
async def create_deployment_workflow(service_name: str, 
                                   environment: str = "staging",
                                   auto_rollback: bool = True) -> dict:
    """Create a complete deployment workflow from template."""
    
    workflow_code = f'''
@workflow(name="deploy-{service_name}", version="1.0.0")
def deployment_workflow():
    """Deploy {service_name} to {environment}"""
    
    # Validation step
    validate = (
        step("validate", "Validate deployment config")
        .shell("kubectl apply --dry-run=client -f deploy.yaml")
        .output("validation_result")
    )
    
    # Build step
    build = (
        step("build", "Build container image")
        .docker("docker:latest")
        .shell("docker build -t {service_name}:$VERSION .")
        .env(VERSION="${{VERSION}}")
        .output("image_id")
        .depends("validate")
    )
    
    # Deploy step
    deploy = (
        step("deploy", "Deploy to {environment}")
        .tool("kubectl", action="apply", args=["-f", "deploy.yaml"])
        .env(NAMESPACE="{environment}")
        .depends("build")
        .retry(limit=3, interval_sec=30)
    )
    
    # Health check
    health = (
        step("health-check", "Verify deployment health")
        .http("GET", "https://{service_name}.{environment}.svc/health")
        .retry(limit=5, interval_sec=10)
        .depends("deploy")
    )
    '''
    
    if auto_rollback:
        workflow_code += '''
    
    # Auto-rollback on failure
    rollback = (
        step("rollback", "Rollback on failure")
        .shell("kubectl rollout undo deployment/{service_name}")
        .when("{{output.health-check.status}}", not_equals=200)
        .depends("health-check")
    )
    
    return validate >> build >> deploy >> health >> rollback
    '''
    else:
        workflow_code += '''
    
    return validate >> build >> deploy >> health
    '''
    
    # Define the workflow
    result = await mcp.call_tool("define_workflow", {
        "name": f"deploy-{service_name}",
        "code": workflow_code,
        "description": f"Deployment workflow for {service_name}"
    })
    
    return result


# Pre-defined example workflows
@workflow(name="simple-backup")
def backup_workflow():
    """Simple backup workflow example."""
    return (
        step("snapshot", "Create database snapshot")
        .shell("pg_dump mydb > backup.sql")
        >>
        step("compress", "Compress backup")
        .shell("gzip backup.sql")
        >>
        step("upload", "Upload to S3")
        .tool("aws", action="s3", args=["cp", "backup.sql.gz", "s3://backups/"])
    )


# Register pre-defined workflow
mcp.workflows["simple-backup"] = backup_workflow()


# Main entry point
if __name__ == "__main__":
    print("""
    🚀 Kubiya MCP Server Example
    
    This server demonstrates:
    - Defining workflows from inline Python code
    - Executing workflows with parameters
    - GraphQL queries for workflow introspection
    - Custom tools and pre-defined workflows
    
    Available tools:
    """)
    
    for tool in mcp.list_tools():
        print(f"    - {tool['name']}: {tool['description']}")
    
    print("\n    Ready for connections!\n")
    
    # Run the server
    mcp.run() 