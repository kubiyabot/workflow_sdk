"""
Test Client - Demonstrates all MCP features working end-to-end.

This shows:
1. Defining workflows from inline Python code
2. Executing workflows with parameters
3. GraphQL queries
4. Custom tools
"""

import asyncio
from kubiya_workflow_sdk.mcp import Client, FastMCP


async def test_inline_workflow_definition():
    """Test defining a workflow from inline Python code."""
    print("\n🔧 TEST 1: Define Workflow from Inline Python Code")
    print("=" * 60)

    # Create server
    mcp = FastMCP("Test Server")

    # Create client
    client = Client(mcp, transport="direct")

    async with client:
        # Define a workflow using inline Python code
        workflow_code = '''
@workflow(name="data-pipeline", version="1.0.0")
def data_pipeline():
    """Extract, transform, and load data"""
    
    extract = (
        step("extract", "Extract data from API")
        .http("GET", "https://api.example.com/data")
        .output("raw_data")
    )
    
    transform = (
        step("transform", "Transform data")
        .python("""
import json
data = json.loads('{{output.extract.body}}')
transformed = [{"id": d["id"], "value": d["value"] * 2} for d in data]
print(json.dumps(transformed))
""")
        .output("transformed_data")
        .depends("extract")
    )
    
    load = (
        step("load", "Load to database")
        .docker("postgres:latest")
        .shell("psql -c 'INSERT INTO results VALUES ($DATA)'")
        .env(DATA="{{output.transform.transformed_data}}")
        .depends("transform")
    )
    
    return extract >> transform >> load
'''

        # Define the workflow
        result = await client.define_workflow(
            name="data-pipeline", code=workflow_code, description="ETL pipeline example"
        )

        print(f"✅ Workflow defined: {result['workflow']['name']}")
        print(f"   Steps: {result['workflow']['steps']}")
        print(f"   Validation: {'PASSED' if result['validation']['valid'] else 'FAILED'}")

        if result["validation"]["errors"]:
            print(f"   Errors: {result['validation']['errors']}")


async def test_workflow_execution():
    """Test executing workflows with parameters."""
    print("\n🚀 TEST 2: Execute Workflow with Parameters")
    print("=" * 60)

    mcp = FastMCP("Test Server")
    client = Client(mcp, transport="direct")

    async with client:
        # Define a parameterized workflow
        workflow_code = '''
@workflow(name="parameterized-deploy")
def deploy_with_params():
    """Deploy with version parameter"""
    
    deploy = (
        step("deploy", "Deploy application")
        .shell("echo Deploying version {{params.VERSION}} to {{params.ENV}}")
        .output("result")
    )
    
    notify = (
        step("notify", "Send notification")
        .shell("echo Deployed {{params.VERSION}} successfully")
        .depends("deploy")
    )
    
    return deploy >> notify
'''

        # Define it
        await client.define_workflow("parameterized-deploy", workflow_code)

        # Execute with parameters
        exec_result = await client.execute_workflow(
            "parameterized-deploy",
            params={"VERSION": "v2.1.0", "ENV": "production"},
            stream=False,  # For simplicity in test
        )

        print(f"✅ Execution ID: {exec_result['execution_id']}")
        print(f"   Status: {exec_result['status']}")
        print(f"   Mocked: {exec_result.get('mocked', False)}")


async def test_graphql_queries():
    """Test GraphQL queries for workflow introspection."""
    print("\n📊 TEST 3: GraphQL Queries")
    print("=" * 60)

    mcp = FastMCP("Test Server")

    # Pre-populate some workflows
    workflow_code1 = """
@workflow(name="backup")
def backup(): 
    return step("backup", "Backup database").shell("pg_dump mydb")
"""

    workflow_code2 = """
@workflow(name="cleanup")
def cleanup():
    return (
        step("find", "Find old files").shell("find /tmp -mtime +7")
        >> step("delete", "Delete old files").shell("xargs rm -f")
    )
"""

    client = Client(mcp, transport="direct")

    async with client:
        # Define workflows
        await client.define_workflow("backup", workflow_code1)
        await client.define_workflow("cleanup", workflow_code2)

        # Query all workflows
        query1 = """
        {
            workflows {
                name
                description
                steps {
                    name
                    type
                }
            }
        }
        """

        result1 = await client.query_graphql(query1)

        if result1.get("success"):
            print("✅ Query 1 - List all workflows:")
            for wf in result1["data"]["workflows"]:
                print(f"   - {wf['name']}: {len(wf['steps'])} steps")
                for step in wf["steps"]:
                    print(f"     • {step['name']} ({step['type']})")
        else:
            print(f"❌ GraphQL not available: {result1.get('error', 'Unknown error')}")

        # Query specific workflow
        query2 = """
        {
            workflow(name: "cleanup") {
                name
                params
                steps {
                    name
                    depends_on
                }
            }
        }
        """

        result2 = await client.query_graphql(query2)

        if result2.get("success") and result2["data"]["workflow"]:
            wf = result2["data"]["workflow"]
            print(f"\n✅ Query 2 - Workflow details for '{wf['name']}':")
            print(f"   Parameters: {wf['params']}")
            print(f"   Step dependencies:")
            for step in wf["steps"]:
                deps = step["depends_on"] or []
                print(f"   - {step['name']} depends on: {deps}")


async def test_complex_workflow():
    """Test a complex real-world workflow."""
    print("\n🏗️ TEST 4: Complex Real-World Workflow")
    print("=" * 60)

    mcp = FastMCP("Test Server")
    client = Client(mcp, transport="direct")

    async with client:
        # Define a complex incident response workflow
        workflow_code = '''
from datetime import datetime

@workflow(name="incident-response", version="2.0.0")
def incident_response():
    """Automated incident response with intelligent routing"""
    
    # Detect incident
    detect = (
        step("detect", "Monitor for incidents")
        .tool("datadog", 
              query="avg:system.cpu.user{*} > 90",
              time_range="5m")
        .output("incident_data")
    )
    
    # Analyze with AI
    analyze = (
        step("analyze", "AI-powered analysis")
        .inline_agent(
            message="Analyze this incident: {{output.detect.incident_data}}",
            agent_name="incident-analyzer",
            ai_instructions="You are an SRE expert. Analyze and categorize: critical/high/medium/low",
            runners=["default"]
        )
        .output("analysis")
        .depends("detect")
    )
    
    # Page on-call if critical
    page_oncall = (
        step("page", "Page on-call engineer")
        .tool("pagerduty",
              action="create_incident",
              severity="critical",
              summary="{{output.analyze.summary}}")
        .when("{{output.analyze.severity}}", equals="critical")
        .depends("analyze")
    )
    
    # Auto-remediate if possible
    remediate = (
        step("remediate", "Attempt auto-remediation")
        .shell("kubectl scale deployment myapp --replicas=5")
        .when("{{output.analyze.remediation_possible}}", equals=True)
        .depends("analyze")
        .retry(limit=3, interval_sec=30)
    )
    
    # Create ticket for tracking
    ticket = (
        step("ticket", "Create tracking ticket")
        .tool("jira",
              action="create_issue",
              project="OPS",
              type="Incident",
              summary="{{output.analyze.summary}}",
              description="{{output.analyze.details}}")
        .depends("analyze")
    )
    
    # Notify team
    notify = (
        step("notify", "Notify team via Slack")
        .tool("slack",
              channel="#incidents",
              message="Incident detected: {{output.analyze.summary}}")
        .depends(["page_oncall", "remediate", "ticket"])
    )
    
    return detect >> analyze >> [page_oncall, remediate, ticket] >> notify
'''

        # Define the workflow
        result = await client.define_workflow(
            name="incident-response",
            code=workflow_code,
            description="Intelligent incident response automation",
        )

        print(f"✅ Complex workflow defined: {result['workflow']['name']}")
        print(f"   Version: 2.0.0")
        print(f"   Steps: {result['workflow']['steps']}")
        print(f"   Features demonstrated:")
        print(f"   - AI-powered analysis with inline agents")
        print(f"   - Conditional execution based on severity")
        print(f"   - Parallel execution branches")
        print(f"   - Integration with multiple tools")
        print(f"   - Retry policies for remediation")


async def test_custom_tools():
    """Test custom tool registration and usage."""
    print("\n🛠️ TEST 5: Custom Tools")
    print("=" * 60)

    mcp = FastMCP("Test Server")

    # Register custom tools
    @mcp.tool
    def calculate_metrics(values: list, metric_type: str = "average") -> dict:
        """Calculate metrics from a list of values."""
        if metric_type == "average":
            result = sum(values) / len(values) if values else 0
        elif metric_type == "sum":
            result = sum(values)
        elif metric_type == "max":
            result = max(values) if values else 0
        else:
            result = 0

        return {"metric_type": metric_type, "result": result, "count": len(values)}

    @mcp.tool(description="Generate a performance report")
    async def generate_report(service: str, timeframe: str = "24h") -> dict:
        """Generate performance report for a service."""
        # Simulate async operation
        await asyncio.sleep(0.5)

        return {
            "service": service,
            "timeframe": timeframe,
            "metrics": {
                "availability": "99.95%",
                "response_time": "142ms",
                "error_rate": "0.05%",
                "throughput": "1.2M req/hour",
            },
            "generated_at": "2024-01-15T10:30:00Z",
        }

    client = Client(mcp, transport="direct")

    async with client:
        # Test custom tools
        metrics_result = await client.call_tool(
            "calculate_metrics", {"values": [10, 20, 30, 40, 50], "metric_type": "average"}
        )
        print(f"✅ Custom tool 'calculate_metrics': {metrics_result}")

        report_result = await client.call_tool(
            "generate_report", {"service": "api-gateway", "timeframe": "7d"}
        )
        print(f"\n✅ Custom tool 'generate_report':")
        print(f"   Service: {report_result['service']}")
        print(f"   Metrics:")
        for metric, value in report_result["metrics"].items():
            print(f"     - {metric}: {value}")


async def main():
    """Run all tests."""
    print(
        """
╔════════════════════════════════════════════════════════════╗
║        Kubiya MCP Server - End-to-End Test Suite           ║
║                                                            ║
║  Testing all features:                                     ║
║  • Inline Python workflow definitions                      ║
║  • Workflow execution with parameters                      ║
║  • GraphQL queries for introspection                       ║
║  • Complex real-world workflows                            ║
║  • Custom tool integration                                 ║
╚════════════════════════════════════════════════════════════╝
    """
    )

    try:
        await test_inline_workflow_definition()
        await test_workflow_execution()
        await test_graphql_queries()
        await test_complex_workflow()
        await test_custom_tools()

        print("\n✅ All tests completed successfully!")
        print("\n💡 Next steps:")
        print("   1. Run example_server.py to start a real MCP server")
        print("   2. Connect from Claude Desktop or any MCP client")
        print("   3. Build your own workflows with inline Python!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
