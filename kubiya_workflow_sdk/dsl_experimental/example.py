import inspect

from .models import *  # noqa


def build_workflow(
        kubiya_host: str,
        kubiya_api_key: str,
) -> Workflow:
    step_1 = ToolStep(
        name='get_github_token',
        description='Get GitHub token from Kubiya storage',
        output='GITHUB_TOKEN',
        executor=ToolExecutor(
            type='tool',
            config=ToolExecutorConfig(
                tool_def=ToolDef(
                    name='get-github-token',
                    type='docker',
                    image='python:3.12-slim',
                    content="""set -e
pip install -qqq -r /opt/scripts/reqs.txt
python /opt/scripts/get_creds.py
""",
                    with_files=[
                        FileDefinition(
                            destination='/opt/scripts/get_creds.py',
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
"""
                        ),
                        FileDefinition(
                            destination='/opt/scripts/reqs.txt',
                            content='httpx==0.28.1'
                        ),
                    ],
                    args=[
                        ArgDefinition(name='INTEGRATION_NAME', type='string', required=True),
                    ],
                ),
                args={
                    'INTEGRATION_NAME': 'github_app',
                },
            ),
        ),
    )

    step_2 = KubiyaStep(
        name='get-slack-token',
        description='Get Slack App integration token',
        output='SLACK_TOKEN',
        executor=KubiyaExecutor(
            config=KubiyaExecutorConfig(
                url='api/v1/integration/slack/token/1',
                method='GET',
            )
        )
    )

    step_3 = AgentStep(
        name='string-analyzer',
        description='Analyze array of strings',
        depends=[
            step_1.name,
            step_2.name,
        ],
        output='AGENT_RESULT',
        executor=AgentExecutor(
            config=AgentExecutorConfig(
                agent_name='demo-teammate',
                message=f"""
For the given array of strings find the one with highest amount of unique symbols.
Value 1: ${step_1.output};
Value 2: ${step_2.output}].
Do not create and execute any program on any language for this purpose.
Return result as a tuple of values, first one is index, second one is amount of unique symbols.
Example: (1, 25)
Do not return any other text, only answer in required format.
    """
            )
        )
    )

    step_4 = CommandStep(
        name='show-secrets',
        description='Show secrets from Kubiya storage',
        output='RESULT',
        depends=[
            step_3.name,
        ],
        command=f'echo "Github Token: ${step_1.output}; Slack Token: ${step_2.output}; Result: ${step_3.output}"'
    )

    workflow = Workflow(
        name='prototype-workflow',
        description='Prototype workflow to demonstrate alternative implementation',
        steps=Steps([
            step_1,
            step_2,
            step_3,
            step_4,
        ]),
        secrets=[
            {'KUBIYA_HOST': kubiya_host},
            {'KUBIYA_API_KEY': kubiya_api_key},
        ]
    )

    return workflow
