from kubiya_workflow_sdk import validate_workflow_definition
from kubiya_workflow_sdk.dsl_experimental import *


def build_workflow(
    kubiya_host: str,
    kubiya_api_key: str,
) -> Workflow:
    """Build a comprehensive workflow demonstrating various step types and features"""

    # Step 1: Tool step to get GitHub token
    get_github_token_step = ExecutorStep(
        name="get_github_token",
        description="Get GitHub token from Kubiya storage using custom tool",
        output="GITHUB_TOKEN",
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                tool_def=ToolDef(
                    name="get-github-token",
                    type="docker",
                    image="python:3.12-slim",
                    content="""set -e
pip install -qqq -r /opt/scripts/reqs.txt
python /opt/scripts/get_creds.py
""",
                    with_files=[
                        FileDefinition(
                            destination="/opt/scripts/get_creds.py",
                            content="""import os
from urllib.parse import urljoin

import httpx


def get_github_vendor_id(kubiya_api_key: str, kubiya_host: str, integration_name: str) -> str:
    path = f'api/v2/integrations/{integration_name}'
    url = urljoin(kubiya_host, path)
    resp = httpx.get(url, headers={'Authorization': f'UserKey {kubiya_api_key}'})
    vendor_id = resp.json()['configs'][0]['vendor_specific']['id']
    return vendor_id


def get_github_token(kubiya_api_key: str, kubiya_host: str, integration_name: str, vendor_id: str) -> str:
    path = f'api/v1/integration/{integration_name}/token/{vendor_id}'
    url = urljoin(kubiya_host, path)
    resp = httpx.get(url, headers={'Authorization': f'UserKey {kubiya_api_key}'})
    token = resp.json()['token']
    return token


if __name__ == '__main__':
    kubiya_host = os.environ.get('KUBIYA_HOST')
    kubiya_api_key = os.environ.get('KUBIYA_API_KEY')
    integration_name = os.environ.get('INTEGRATION_NAME')

    vendor_id = get_github_vendor_id(
        kubiya_host=kubiya_host,
        kubiya_api_key=kubiya_api_key,
        integration_name=integration_name,
    )
    token = get_github_token(
        kubiya_host=kubiya_host,
        kubiya_api_key=kubiya_api_key,
        integration_name=integration_name,
        vendor_id=vendor_id,
    )

    print(token)
""",
                        ),
                        FileDefinition(
                            destination="/opt/scripts/reqs.txt", content="httpx==0.28.1"
                        ),
                    ],
                    args=[
                        ArgDefinition(name="INTEGRATION_NAME", type="string", required=True),
                    ],
                ),
                args={
                    "INTEGRATION_NAME": "github_app",
                },
            ),
        ),
    )

    # Step 2: Kubiya HTTP step to get Slack token
    get_slack_token_step = ExecutorStep(
        name="get_slack_token",
        description="Get Slack App integration token via Kubiya API",
        output="SLACK_TOKEN",
        executor=Executor(
            type=ExecutorType.KUBIYA,
            config=KubiyaExecutorConfig(
                url="api/v1/integration/slack/token/1",
                method=HTTPMethod.GET,
            ),
        ),
    )

    # Step 3: Agent step for string analysis
    string_analyzer_step = ExecutorStep(
        name="string_analyzer",
        description="Analyze array of strings using AI agent",
        depends=[
            get_github_token_step.name,
            get_slack_token_step.name,
        ],
        output="AGENT_RESULT",
        executor=Executor(
            type=ExecutorType.AGENT,
            config=AgentExecutorConfig(
                agent_name="demo-teammate",
                message=f"""
For the given array of strings find the one with highest amount of unique symbols.
Value 1: ${get_github_token_step.output};
Value 2: ${get_slack_token_step.output}.
Do not create and execute any program on any language for this purpose.
Return result as a tuple of values, first one is index, second one is amount of unique symbols.
Example: (1, 25)
Do not return any other text, only answer in required format.
""",
                context={
                    "task_type": "string_analysis",
                    "expected_format": "tuple",
                },
            ),
        ),
    )

    # Step 4: Command step to display results
    show_results_step = CommandStep(
        name="show_results",
        description="Display all collected tokens and analysis results",
        depends=[
            string_analyzer_step.name,
        ],
        output="FINAL_RESULT",
        command=f'echo "Github Token: ${get_github_token_step.output}; Slack Token: ${get_slack_token_step.output}; Analysis Result: ${string_analyzer_step.output}"',
    )

    # Create the complete workflow
    workflow = Workflow(
        name="enhanced_prototype_workflow",
        description="Enhanced prototype workflow demonstrating comprehensive feature usage",
        steps=[
            get_github_token_step,
            get_slack_token_step,
            string_analyzer_step,
            show_results_step,
        ],
        tags=["prototype", "integration", "api", "demo"],
        group="Development",
    )

    return workflow


if __name__ == "__main__":
    # Example usage
    kubiya_host = "https://api.kubiya.ai"
    kubiya_api_key = "your-api-key-here"

    # Build the main workflow
    main_workflow = build_workflow(kubiya_host, kubiya_api_key)
    print("Main Workflow:")
    print(main_workflow.model_dump_json(indent=2, exclude_none=True))

    if errors := validate_workflow_definition(main_workflow.model_dump(exclude_none=True)):
        print("\nValidation errors:")
        for error in errors:
            print(f"\t{error}")
    else:
        print("\nWorkflow validation passed.")

    print("\nWorkflow examples created successfully!")
