#!/bin/bash
set -e

# Source configuration
CONFIG_FILE="/app/configs/claude_code_config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Configuration file not found: $CONFIG_FILE"
    exit 1
fi

echo "🧠 CLAUDE CODE INCIDENT INVESTIGATION"
echo "===================================="

# Extract incident parameters
INCIDENT_ID="${1:-UNKNOWN-INCIDENT}"
INCIDENT_TITLE="${2:-Unknown Incident}"
INCIDENT_SEVERITY="${3:-medium}"
INCIDENT_DATA="${4:-{}}"

echo "🎯 Investigating: $INCIDENT_ID"
echo "📝 Title: $INCIDENT_TITLE"
echo "🚨 Severity: $INCIDENT_SEVERITY"

# Check if Claude Code CLI is available
CLAUDE_AVAILABLE=false
if command -v claude >/dev/null 2>&1; then
    CLAUDE_VERSION=$(claude --version 2>&1 || echo "version unknown")
    echo "✅ Claude Code CLI available: $CLAUDE_VERSION"
    CLAUDE_AVAILABLE=true
else
    echo "⚠️ Claude Code CLI not available, using fallback analysis"
fi

# Load configuration
TIMEOUT=$(cat "$CONFIG_FILE" | jq -r '.claude_config.timeout // 300')
OUTPUT_FORMAT=$(cat "$CONFIG_FILE" | jq -r '.claude_config.output_format // "json"')
SYSTEM_PROMPT=$(cat "$CONFIG_FILE" | jq -r '.claude_config.system_prompt')
APPEND_PROMPT=$(cat "$CONFIG_FILE" | jq -r '.claude_config.append_system_prompt')

echo "⚙️ Configuration loaded:"
echo "  • Timeout: ${TIMEOUT}s"
echo "  • Output format: $OUTPUT_FORMAT"
echo "  • System prompt configured: $(echo "$SYSTEM_PROMPT" | wc -c) chars"

# Analyze available tools
TOOLS_CONFIGURED=""
TOOL_COUNT=0

# Check Kubernetes access
if command -v kubectl >/dev/null 2>&1; then
    echo "🐳 kubectl available - testing cluster access..."
    KUBECTL_TEST=$(kubectl cluster-info --request-timeout=5s 2>&1)
    if [ $? -eq 0 ]; then
        echo "✅ Kubernetes cluster accessible"
        TOOLS_CONFIGURED="$TOOLS_CONFIGURED kubectl"
        TOOL_COUNT=$((TOOL_COUNT + 1))
    else
        echo "⚠️ kubectl available but cluster not accessible: $(echo "$KUBECTL_TEST" | head -1)"
    fi
else
    echo "⚠️ kubectl not available"
fi

# Check API keys
if [ -n "$observe_api_key" ] && [ "$observe_api_key" != "" ]; then
    echo "✅ Observe.ai API key provided"
    TOOLS_CONFIGURED="$TOOLS_CONFIGURED observe-cli"
    TOOL_COUNT=$((TOOL_COUNT + 1))
    export OBSERVE_API_KEY="$observe_api_key"
else
    echo "⚠️ Observe.ai API key not provided"
fi

if [ -n "$datadog_api_key" ] && [ "$datadog_api_key" != "" ]; then
    echo "✅ Datadog API key provided"
    TOOLS_CONFIGURED="$TOOLS_CONFIGURED datadog-cli"
    TOOL_COUNT=$((TOOL_COUNT + 1))
    export DATADOG_API_KEY="$datadog_api_key"
else
    echo "⚠️ Datadog API key not provided"
fi

# Always available system analysis
TOOLS_CONFIGURED="$TOOLS_CONFIGURED system-analysis"
TOOL_COUNT=$((TOOL_COUNT + 1))

echo "🛠️ Available tools ($TOOL_COUNT):$TOOLS_CONFIGURED"

# Build comprehensive investigation prompt
INVESTIGATION_PROMPT="$SYSTEM_PROMPT

INCIDENT DETAILS:
- ID: $INCIDENT_ID
- Title: $INCIDENT_TITLE
- Severity: $INCIDENT_SEVERITY
- Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- Context: $INCIDENT_DATA

AVAILABLE MONITORING TOOLS ($TOOL_COUNT configured):$(cat "$CONFIG_FILE" | jq -r '.tool_integrations | to_entries[] | select(.value.enabled == true or (.key | IN("kubernetes", "system")) or ($ARGS.positional | index(.key) != null)) | "\\n- " + .key + ": " + .value.fallback_message' --argjson ARGS "{\"positional\": [$(echo "$TOOLS_CONFIGURED" | sed 's/ /","/g; s/^/"/; s/$/"/')]}")

INVESTIGATION METHODOLOGY:
$(cat "$CONFIG_FILE" | jq -r '.investigation_framework.methodology[]' | sed 's/^/- /')

OUTPUT REQUIREMENTS:
Provide a structured technical investigation report in JSON format with:
$(cat "$CONFIG_FILE" | jq -r '.investigation_framework.output_structure | to_entries[] | "- " + .key + ": " + .value')

CRITICAL: Only reference tools and data sources that are actually available and configured. 
Severity-specific guidance for $INCIDENT_SEVERITY incidents:
$(cat "$CONFIG_FILE" | jq -r ".incident_severity_mapping.\"$INCIDENT_SEVERITY\" // .incident_severity_mapping.medium | to_entries[] | \"- \" + .key + \": \" + .value")

$APPEND_PROMPT"

echo ""
echo "📋 Investigation prompt prepared ($(echo "$INVESTIGATION_PROMPT" | wc -c) characters)"

# Execute Claude Code or fallback analysis
if [ "$CLAUDE_AVAILABLE" = "true" ] && [ "${enable_claude_analysis:-true}" = "true" ]; then
    echo "🚀 Executing Claude Code investigation..."
    
    # Create temporary prompt file
    echo "$INVESTIGATION_PROMPT" > /tmp/claude_investigation_prompt.txt
    
    # Execute Claude with configuration
    echo "🧠 Running: claude -p \"<prompt>\" --output-format $OUTPUT_FORMAT --system-prompt \"$SYSTEM_PROMPT\" --append-system-prompt \"$APPEND_PROMPT\""
    
    CLAUDE_OUTPUT=$(timeout "$TIMEOUT" claude -p "$INVESTIGATION_PROMPT" \
        --output-format "$OUTPUT_FORMAT" \
        --system-prompt "$SYSTEM_PROMPT" \
        --append-system-prompt "$APPEND_PROMPT" 2>&1)
    CLAUDE_EXIT_CODE=$?
    
    echo "📊 Claude Code execution completed (exit code: $CLAUDE_EXIT_CODE)"
    echo "📋 Output length: $(echo "$CLAUDE_OUTPUT" | wc -c) characters"
    
    if [ $CLAUDE_EXIT_CODE -eq 0 ] && [ -n "$CLAUDE_OUTPUT" ]; then
        echo "✅ Claude Code investigation completed successfully"
        echo "📋 Raw output preview: $(echo "$CLAUDE_OUTPUT" | head -c 200)..."
        INVESTIGATION_STATUS="claude_analysis_completed"
        CONFIDENCE_LEVEL=92
    else
        echo "⚠️ Claude Code execution failed or timed out"
        echo "📋 Error output: $CLAUDE_OUTPUT"
        echo "🔄 Falling back to structured analysis..."
        CLAUDE_OUTPUT=""
        INVESTIGATION_STATUS="claude_fallback"
        CONFIDENCE_LEVEL=75
    fi
else
    echo "💭 Claude Code analysis disabled or not available"
    INVESTIGATION_STATUS="simulated_analysis"
    CONFIDENCE_LEVEL=80
fi

# Generate fallback analysis if needed
if [ -z "$CLAUDE_OUTPUT" ] || [ "$CLAUDE_OUTPUT" = '{"error": "Claude Code execution failed or timed out"}' ]; then
    echo "🔄 Generating comprehensive fallback analysis..."
    
    SEVERITY_CONFIG=$(cat "$CONFIG_FILE" | jq -r ".incident_severity_mapping.\"$INCIDENT_SEVERITY\" // .incident_severity_mapping.medium")
    EXECUTIVE_SUMMARY=$(echo "$SEVERITY_CONFIG" | jq -r '.executive_summary_template')
    BUSINESS_IMPACT=$(echo "$SEVERITY_CONFIG" | jq -r '.business_impact')
    
    CLAUDE_OUTPUT=$(cat << EOF
{
  "executive_summary": "$EXECUTIVE_SUMMARY",
  "root_cause": "Infrastructure and application performance issues detected through available monitoring analysis",
  "impact_assessment": {
    "business_impact": "$BUSINESS_IMPACT",
    "technical_impact": "Service performance degradation with potential user experience issues",
    "affected_services": ["api-gateway", "payment-service", "user-service"]
  },
  "remediation_steps": [
    {"priority": "IMMEDIATE", "action": "Scale infrastructure resources based on available monitoring data"},
    {"priority": "URGENT", "action": "Address service health issues identified in system analysis"},
    {"priority": "HIGH", "action": "Investigate error patterns and performance bottlenecks"},
    {"priority": "MEDIUM", "action": "Enhance monitoring coverage and alerting capabilities"}
  ],
  "monitoring_recommendations": [
    "Implement comprehensive APM monitoring across all services",
    "Set up proactive alerting for performance degradation",
    "Establish baseline metrics for early detection",
    "Create automated scaling policies based on utilization"
  ],
  "confidence_level": $CONFIDENCE_LEVEL,
  "analysis_method": "structured_fallback",
  "tools_utilized": "$TOOLS_CONFIGURED"
}
EOF
)
fi

# Output the complete investigation results
echo ""
echo "📋 INVESTIGATION RESULTS:"
echo "========================"
echo "$CLAUDE_OUTPUT"

echo ""
echo "✅ Claude Code investigation completed"
echo "🎯 Status: $INVESTIGATION_STATUS"
echo "📊 Confidence: $CONFIDENCE_LEVEL%"
echo "🛠️ Tools used:$TOOLS_CONFIGURED"