"""
Executor convenience functions for easy step creation.

These functions provide shortcuts for creating steps with specific executor types.
"""

from typing import Dict, Any, List, Optional
from .step import Step


def python_executor(name: str, script: str, **kwargs) -> Step:
    """
    Create a Python script step.

    Example:
        python_executor("process", '''
            import json
            data = json.loads(input())
            print(json.dumps({"result": len(data)}))
        ''')
    """
    return Step(name).python(script)


def shell_executor(name: str, command: str, shell: str = "sh", **kwargs) -> Step:
    """
    Create a shell command step.

    Example:
        shell_executor("backup", "tar -czf backup.tar.gz /data")
    """
    step = Step(name, command)
    if shell != "sh":
        step.shell_type(shell)
    return step


def docker_executor(
    name: str, image: str, command: Optional[str] = None, content: Optional[str] = None, **kwargs
) -> Step:
    """
    Create a Docker container step.

    Example:
        docker_executor("build", "node:18", "npm run build")
    """
    return Step(name).docker(image, command, content)


def http_executor(
    name: str,
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Any] = None,
    **kwargs,
) -> Step:
    """
    Create an HTTP request step.

    Example:
        http_executor("webhook", "https://api.example.com/webhook",
                     method="POST",
                     headers={"Content-Type": "application/json"},
                     body={"status": "started"})
    """
    return Step(name).http(url, method, headers, body)


def ssh_executor(
    name: str,
    host: str,
    user: str,
    command: str,
    port: int = 22,
    key_file: Optional[str] = None,
    **kwargs,
) -> Step:
    """
    Create an SSH remote execution step.

    Example:
        ssh_executor("deploy", "server.example.com", "deploy",
                    "./deploy.sh", key_file="/home/user/.ssh/id_rsa")
    """
    return Step(name).ssh(host, user, command, port, key_file)


def inline_agent_executor(
    name: str,
    message: str,
    agent_name: str,
    ai_instructions: str,
    runners: List[str] = ["core-testing-2"],
    llm_model: str = "gpt-4o-mini",
    tools: Optional[List[Dict[str, Any]]] = None,
    **kwargs,
) -> Step:
    """
    Create an inline AI agent step.

    Example:
        inline_agent_executor(
            "analyze-logs",
            "Analyze these logs and find errors: {{logs}}",
            agent_name="log-analyzer",
            ai_instructions="You are a log analysis expert. Find patterns and errors.",
            llm_model="gpt-4o"
        )
    """
    return Step(name).inline_agent(
        message=message,
        agent_name=agent_name,
        ai_instructions=ai_instructions,
        runners=runners,
        llm_model=llm_model,
        tools=tools,
        **kwargs,
    )


def tool_executor(
    name: str, tool_name: str = None, tool_def: Dict[str, Any] = None, **tool_args
) -> Step:
    """
    Create a tool executor step.

    Example with pre-registered tool:
        tool_executor("get-pods", tool_name="kubectl", command="get pods -n default")

    Example with inline tool definition:
        tool_executor("notify",
                     tool_def={
                         "name": "slack-notifier",
                         "type": "docker",
                         "image": "curlimages/curl:latest",
                         "content": "#!/bin/sh\\ncurl -X POST...",
                         "args": [{"name": "channel", "type": "string"}]
                     },
                     channel="#alerts",
                     message="Error detected!")
    """
    if tool_def:
        # Inline tool definition
        step = Step(name).tool_def(
            name=tool_def["name"],
            type=tool_def["type"],
            image=tool_def["image"],
            content=tool_def["content"],
            args=tool_def["args"],
            description=tool_def.get("description"),
            with_files=tool_def.get("with_files"),
        )
        if tool_args:
            step.args(**tool_args)
        return step
    elif tool_name:
        # Pre-registered tool
        return Step(name).tool(tool_name, **tool_args)
    else:
        raise ValueError("Either tool_name or tool_def must be provided")


def kubiya_executor(name: str, url: str, method: str = "GET", **config) -> Step:
    """
    Create a Kubiya API executor step.

    Example:
        kubiya_executor("get-secret", "api/v1/secret/get_secret_value/MY_SECRET")
    """
    return Step(name).kubiya(url, method, **config)


def jq_executor(name: str, query: str, **kwargs) -> Step:
    """
    Create a jq JSON processing step.

    Example:
        jq_executor("extract-ids", '.data[] | select(.active == true) | .id')
    """
    return Step(name).jq(query)
