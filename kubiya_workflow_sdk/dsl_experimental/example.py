from . import *
import inspect


def build_workflow(
        kubiya_host: str,
        kubiya_api_key: str,

        pipeline_name: str,

        pr_title: str,
        pr_url: str,
        repo_url: str,
        pr_number: int,
        workflow_run_id: int,
        author: str,
        workflow_url: str,
        triggered_at: str,
) -> Workflow:
    step_1 = ExecutorStep(
        name='get-github-token',
        description='Get GitHub token from Kubiya storage',
        output='GITHUB_TOKEN',
        executor=Executor(
            type=ExecutorType.TOOL,
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
                            content='# Placeholder for get_secrets function',
                        ),
                        FileDefinition(
                            destination='/opt/scripts/reqs.txt',
                            content='httpx==0.28.1',
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

    step_2 = ExecutorStep(
        name='get-gh-pr-view',
        description='Get GitHub PR view details',
        depends=[step_1.name],
        output='GH_PR_VIEW',
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                tool_def=ToolDef(
                    name='get-gh-pr-view',
                    description='View details of a specific pull request.',
                    type='docker',
                    image='maniator/gh:latest',
                    content="""#!/bin/sh
set -e
# Set operation type for disclaimer
OPERATION_TYPE="github_pr_view"
if ! command -v jq >/dev/null 2>&1; then
    apk add --quiet jq >/dev/null 2>&1
fi
echo "🔍 Viewing pull request #$pr_number in $repo_url..."
echo "📎 Link: https://github.com/$repo_url/pull/$pr_number"
gh pr view --repo $repo_url $pr_number
""",
                ),
                secrets={
                    'GH_TOKEN': f'${step_1.output}'
                }
            )
        )
    )

    step_3 = ExecutorStep(
        name='get-gh-pr-diff',
        depends=[step_1.name],
        description='Get GitHub PR diff',
        output='GH_PR_DIFF',
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                tool_def=ToolDef(
                    name='github_pr_diff',
                    description='Shows github PR Diff',
                    type='docker',
                    image='maniator/gh:latest',
                    secrets=['GH_TOKEN'],
                    content="""set -e
gh pr diff --repo $repo_url $pr_number"""
                ),
                secrets={
                    'GH_TOKEN': f'${step_1.output}'
                }
            )
        )
    )

    step_3_1 = Step(
        name='get-workflow-run-logs-failed',
        description='Get failed workflow run logs',
        output='FAILED_LOGS',
        depends=[step_1.name],
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                tool_def=ToolDef(
                    name='workflow_run_logs_failed',
                    description='View failed job outputs from GitHub Actions workflow run with advanced error detection',
                    type='docker',
                    image='maniator/gh:latest',
                    secrets=['GH_TOKEN'],
                    content="""#!/bin/sh
set -e

# Set operation type for disclaimer
OPERATION_TYPE="workflow_run_logs_failed"

if ! command -v jq >/dev/null 2>&1; then
    apk add --quiet jq >/dev/null 2>&1
fi

# Function to extract relevant error context from logs efficiently
function extract_error_context() {
    awk '
        BEGIN {
            # Configure sizes
            max_buffer = 100    # Lines to keep before error
            after_lines = 20    # Lines to show after error
            buffer_size = 0     # Current buffer size
            buffer_start = 0    # Start position in circular buffer
            printing = 0        # Number of lines left to print after match
            found_error = 0     # Track if we found any errors
            
            # Error patterns
            err_pattern = "(error|Error|ERROR|exited|Exited|failed|Failed|FAILED|exit code|Exception|EXCEPTION|fatal|Fatal|FATAL)"
            # Noise patterns to filter
            noise_pattern = "(Download|Progress|download|progress)"
        }
        
        # Skip noisy lines early
        $0 ~ noise_pattern { next }
        
        {
            # Store in circular buffer
            buffer_pos = (buffer_start + buffer_size) % max_buffer
            buffer[buffer_pos] = $0
            
            if (buffer_size < max_buffer) {
                buffer_size++
            } else {
                buffer_start = (buffer_start + 1) % max_buffer
            }
            
            # Check for errors
            if ($0 ~ err_pattern) {
                found_error = 1
                # Generate a hash of the surrounding context to avoid duplicates
                context = ""
                for (i = 0; i < 3; i++) {  # Use 3 lines for context hash
                    pos = (buffer_pos - i + max_buffer) % max_buffer
                    if (buffer[pos]) {
                        context = context buffer[pos]
                    }
                }
                context_hash = context
                
                # Only print if we have not seen this context
                if (!(context_hash in seen)) {
                    seen[context_hash] = 1
                    
                    # Print separator for readability
                    print "\\n=== Error Context ===\\n"
                    
                    # Print buffer content (previous lines)
                    for (i = 0; i < buffer_size; i++) {
                        pos = (buffer_start + i) % max_buffer
                        print buffer[pos]
                    }
                    
                    # Start printing aftermath
                    printing = after_lines
                }
            }
            else if (printing > 0) {
                print
                printing--
                if (printing == 0) {
                    print "\\n=== End of Context ===\\n"
                }
            }
        }
        
        END {
            if (!found_error) {
                print "No error patterns found in the logs."
            }
        }
    '
}

# Enforce maximum lines limit
MAX_LINES=150
LINES=${tail_lines:-100}

if [ $LINES -gt $MAX_LINES ]; then
    LINES=$MAX_LINES
fi

echo "📊 Fetching failed job logs for run ID: $workflow_run_id"

# First attempt - try getting failed logs directly
LOGS=$(gh run view --repo $repo_url $workflow_run_id --log-failed 2>/dev/null)
if [ -z "$LOGS" ]; then
    echo "⚠️ No failed logs found directly, attempting to get full logs..."
    # Second attempt - get full logs and filter for errors
    LOGS=$(gh run view --repo $repo_url $workflow_run_id --log 2>/dev/null)
fi

if [ -z "$LOGS" ]; then
    echo "❌ No logs available for this run. The run may still be in progress or logs have expired."
    exit 1
fi

if [ -n "$pattern" ]; then
    echo "🔍 Searching for pattern '$pattern' in logs..."
    echo "$LOGS" | search_logs_with_context "$pattern" "${before_context:-2}" "${after_context:-2}"
else
    echo "🔍 Extracting error context from logs..."
    echo "$LOGS" | extract_error_context | tail -n $LINES
fi"""
                ),
                secrets={
                    'GH_TOKEN': f'${step_1.output}'
                }
            )
        )
    )

    step_3_2 = Step(
        name='get-workflow-run-view',
        description='Get GitHub workflow run view details',
        output='WORKFLOW_RUN_VIEW',
        depends=[step_1.name],
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                tool_def=ToolDef(
                    name='github_workflow_run_view',
                    description='View details of a specific workflow run.',
                    type='docker',
                    image='maniator/gh:latest',
                    secrets=['GH_TOKEN'],
                    content="""#!/bin/sh
set -e

# Set operation type for disclaimer
OPERATION_TYPE="github_workflow_run_view"

if ! command -v jq >/dev/null 2>&1; then
    apk add --quiet jq >/dev/null 2>&1
fi

gh run view --repo $repo_url $workflow_run_id"""
                ),
                args={
                    'repo': '${WORKFLOW_DETAILS.repository_full_name}',
                    'run_id': '${WORKFLOW_DETAILS.workflow_run_id}'
                },
                secrets={
                    'GH_TOKEN': '${GITHUB_TOKEN.token}'
                }
            )
        )
    )

    step_4 = ExecutorStep(
        name='failure-analysis',
        description='Analyze the collected data and generate comprehensive failure report',
        depends=[
            step_2.name,
            step_3.name,
        ],
        output='ANALYSIS_REPORT',
        executor=Executor(
            type=ExecutorType.AGENT,
            config=AgentExecutorConfig(
                agent_name='demo-teammate',
                message=f"""Analyze the CI/CD pipeline failure using the collected data:

PR View: ${step_2.output}
PR Files: ${step_3.output}

Your task is to:
1. Highlights key information first:
   - What failed
   - Why it failed 
   - How to fix it

2. Provide a comprehensive analysis of the failure including:
   - Root cause analysis
   - Impact assessment
   - Recommended fixes
   - Prevention strategies

Format your response with clear sections and actionable insights."""
            )
        )
    )

    step_5 = Step(
        name='post-pr-summary',
        depends=[step_4.name],
        output='PR_MESSAGE_URL',
        description='Post failure analysis comment on the GitHub PR',
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                tool_def=ToolDef(
                    name='github_pr_comment_workflow_failure',
                    description='Post failure analysis comment on the GitHub PR',
                    type='docker',
                    image='maniator/gh:latest',
                    secrets=['GH_TOKEN'],
                    content="""#!/bin/sh
set -euo pipefail

echo "=== GitHub PR Comment Tool Started ==="
echo "Repo: $repo_url"
echo "PR Number: $pr_number"
echo "Analysis report length: $(echo "$analysis_report" | wc -c) characters"
echo "Failed logs length: $(echo "$failed_logs" | wc -c) characters"

# Check if GH_TOKEN is available
if [ -z "$GH_TOKEN" ]; then
    echo "❌ ERROR: GH_TOKEN is not set"
    exit 1
fi

echo "Token length: ${#GH_TOKEN} characters"
echo "Token preview: ${GH_TOKEN:0:10}..."

# Ensure jq is available
if ! command -v jq >/dev/null 2>&1; then
    echo "Installing jq..."
    apk add --no-cache jq
fi

# Test GitHub API access first
echo "=== Testing GitHub API Access ==="
API_TEST=$(gh api user 2>&1) || {
    echo "❌ GITHUB API ERROR: Failed to authenticate with GitHub API"
    echo "Error: $API_TEST"
    exit 1
}

echo "✅ GitHub API authentication successful"
echo "Authenticated as: $(echo "$API_TEST" | jq -r '.login' 2>/dev/null || echo 'Unknown')"

# Check if PR exists
echo "=== Checking if PR exists ==="
PR_CHECK=$(gh api "repos/$repo_url/pulls/$pr_number" 2>&1) || {
    echo "❌ PR ERROR: Could not find PR #$pr_number in $repo_url"
    echo "Error: $PR_CHECK"
    exit 1
}

echo "✅ PR #$pr_number exists in $repo_url"
echo "PR Title: $(echo "$PR_CHECK" | jq -r '.title' 2>/dev/null || echo 'Unknown')"

# Process analysis report and logs safely
analysis_summary=$(echo "$analysis_report" | head -c 2000 | sed 's/`/\\\\`/g')
log_summary=$(echo "$failed_logs" | head -c 1500 | sed 's/`/\\\\`/g')

# Create the comment content with better formatting
read -r -d '' COMMENT_TEMPLATE << 'EOF' || true
## 🚨 CI/CD Pipeline Failure Analysis

### 📊 Summary
The workflow execution failed during the CI/CD pipeline. Here's the automated analysis:

### 🔍 Root Cause Analysis
```
%s
```

### 📋 Error Details
```
%s
```

### 🔗 Quick Links
- [View Workflow Run](%s)
- [Repository Actions](https://github.com/%s/actions)

---
<sub>🤖 This analysis was automatically generated by the CI/CD failure detection system</sub>
EOF

# Get workflow URL from the run view
workflow_url=$(echo "$workflow_run_view" | grep -o 'https://github.com/[^/]*/[^/]*/actions/runs/[0-9]*' | head -1 || echo "https://github.com/$repo_url/actions")

# Format the comment using printf
COMMENT=$(printf "$COMMENT_TEMPLATE" "$analysis_summary" "$log_summary" "$workflow_url" "$repo_url")

echo "=== Posting PR Comment ==="
echo "Comment length: ${#COMMENT} characters"

# Create a temporary file for the comment to handle special characters properly
COMMENT_FILE=$(mktemp)
echo "$COMMENT" > "$COMMENT_FILE"

# Post the comment and capture response
COMMENT_RESPONSE=$(gh api "repos/$repo_url/issues/$pr_number/comments" \\
    --method POST \\
    --input "$COMMENT_FILE" \\
    --field body=@- 2>&1) || {
    echo "❌ COMMENT ERROR: Failed to post comment to PR #$pr_number"
    echo "Error: $COMMENT_RESPONSE"
    rm -f "$COMMENT_FILE"
    exit 1
}

# Clean up temporary file
rm -f "$COMMENT_FILE"

echo "✅ SUCCESS: Comment posted successfully to PR #$pr_number"
echo "Comment ID: $(echo "$COMMENT_RESPONSE" | jq -r '.id' 2>/dev/null || echo 'Unknown')"
echo "Comment URL: $(echo "$COMMENT_RESPONSE" | jq -r '.html_url' 2>/dev/null || echo 'Unknown')"

echo "=== GitHub PR Comment Tool Completed Successfully ==="
"""
                ),
                args={
                    'repo': '${WORKFLOW_DETAILS.repository_full_name}',
                    'number': '${WORKFLOW_DETAILS.pr_number}'
                },
                env={
                    'analysis_report': '${ANALYSIS_REPORT}',
                    'failed_logs': '${FAILED_LOGS}',
                    'workflow_run_view': '${WORKFLOW_RUN_VIEW}'
                },
                secrets={
                    'GH_TOKEN': '${GITHUB_TOKEN.token}'
                }
            )
        )
    )

    step_6 = Step(
        name='send-ms-teams-message',
        description='Send message to MS Teams',
        depends=[step_5.name],
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                tool_def=ToolDef(
                    name='send-ms-teams',
                    type='docker',
                    image='python:3.12-slim',
                    content=f"""set -e
pip install -qqq -r /opt/scripts/reqs.txt
export PAYLOAD=$(python /opt/scripts/teams_workflow_summary.py $pr_title $pr_url $author $workflow_url ${step_5.output} --triggered-at "$triggered_at")
python /opt/scripts/send_message_to_webhook.py $pipeline_name $PAYLOAD
""",
                    with_files=[
                        FileDefinition(
                            destination='/opt/scripts/reqs.txt',
                            content='httpx==0.28.1'
                        ),
                        FileDefinition(
                            destination='/opt/scripts/constant.py',
                            content=inspect.getsource(constant)
                        ),
                        FileDefinition(
                            destination='/opt/scripts/send_message_to_webhook.py',
                            content=inspect.getsource(send_message_to_webhook)
                        ),
                        FileDefinition(
                            destination='/opt/scripts/teams_workflow_summary.py',
                            content=inspect.getsource(teams_workflow_summary)
                        ),
                    ],
                ),
            ),
        ),
    )

    workflow = Workflow(
        name='prototype-workflow',
        description='Prototype workflow to demonstrate alternative implementation',
        steps=[
            step_1,
            step_2,
            step_3,
            step_4,
            step_5,
            step_6,
        ],
        env=[
            EnvironmentVariable(name='KUBIYA_HOST', value=kubiya_host),
            EnvironmentVariable(name='KUBIYA_API_KEY', value=kubiya_api_key),
        ],
        params=[
            Parameter(name='pipeline_name', value=pipeline_name),
            Parameter(name='pr_title', value=pr_title),
            Parameter(name='pr_url', value=pr_url),
            Parameter(name='repo_url', value=repo_url),
            Parameter(name='pr_number', value=pr_number),
            Parameter(name='author', value=author),
            Parameter(name='workflow_url', value=workflow_url),
            Parameter(name='workflow_run_id', value=workflow_run_id),
            Parameter(name='triggered_at', value=triggered_at),
        ]
    )

    return workflow
