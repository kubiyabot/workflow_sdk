"""
Comprehensive examples demonstrating all DSL features.

Shows how to create workflows matching the specification patterns.
"""

from .workflow import workflow, chain, graph
from .step import step, Step
from .executors import *


class Examples:
    """Collection of workflow examples demonstrating all features."""

    @staticmethod
    def basic_sequential():
        """Basic sequential steps."""
        return (
            chain("basic-sequential")
            .description("Simple sequential workflow")
            .step("first", "echo 'Step 1'")
            .step("second", "echo 'Step 2'")
        )

    @staticmethod
    def parallel_execution():
        """Parallel execution with concurrency control."""
        return workflow("parallel-processor").parallel_steps(
            "process-items",
            items=["file1.csv", "file2.csv", "file3.csv"],
            command="python process.py ${ITEM}",
            max_concurrent=2,
        )

    @staticmethod
    def tool_with_definition():
        """Tool executor with inline definition."""
        wf = workflow("slack-notification")

        notify_step = (
            step("notify-slack")
            .tool_def(
                name="slack-notifier",
                type="docker",
                image="curlimages/curl:latest",
                content='#!/bin/sh\nset -e\ncurl -X POST "$SLACK_WEBHOOK" -H "Content-Type: application/json" -d "{\\"text\\": \\"$message\\"}"',
                args=[
                    {"name": "message", "type": "string", "required": True},
                    {"name": "SLACK_WEBHOOK", "type": "string", "required": True},
                ],
            )
            .args(message="Workflow completed successfully!", SLACK_WEBHOOK="${SLACK_WEBHOOK_URL}")
        )

        wf.data["steps"].append(notify_step.to_dict())
        return wf

    @staticmethod
    def inline_agent_workflow():
        """Workflow using inline AI agents."""
        wf = workflow("ai-powered-analysis")

        agent_step = (
            step("analyze-logs")
            .inline_agent(
                message="Analyze these logs and identify errors: ${LOG_CONTENT}",
                agent_name="log-analyzer",
                ai_instructions="You are a log analysis expert. Identify errors, patterns, and provide recommendations.",
                runners=["core-testing-2"],
                llm_model="gpt-4o",
                tools=[
                    {
                        "name": "parse-json",
                        "type": "docker",
                        "image": "alpine:latest",
                        "content": "#!/bin/sh\necho '$1' | jq .",
                        "args": [{"name": "json", "type": "string"}],
                    }
                ],
            )
            .output("ANALYSIS")
        )

        wf.data["steps"].append(agent_step.to_dict())
        return wf


# Export examples
examples = Examples()
