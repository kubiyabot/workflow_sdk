"""Incident parsing components."""

import json
from typing import Dict, Any
from ..models.incident import IncidentEvent, IncidentData


class IncidentParser:
    """Handles parsing of incident events from various sources."""
    
    @staticmethod
    def generate_parsing_script() -> str:
        """Generate shell script for parsing incident events."""
        
        return '''#!/bin/sh
set -e
apk add --no-cache jq

echo "🔍 [STEP 1/7] Parsing incident event..."
echo "📅 Timestamp: $(date)"

# Parse the event JSON
echo "$event" > /tmp/raw_event.json
echo "📄 Raw event saved to /tmp/raw_event.json"

# Extract incident details using standardized format
INCIDENT_ID=$(echo "$event" | jq -r '.id // "UNKNOWN"')
INCIDENT_TITLE=$(echo "$event" | jq -r '.title // "Untitled Incident"')
INCIDENT_SEVERITY=$(echo "$event" | jq -r '.severity // "medium"')
INCIDENT_DESCRIPTION=$(echo "$event" | jq -r '.body // ""')
INCIDENT_URL=$(echo "$event" | jq -r '.url // ""')
SLACK_CHANNEL_SUGGESTION=$(echo "$event" | jq -r '.kubiya.slack_channel_id // ""')

# Additional fields that might be present
SOURCE_SYSTEM=$(echo "$event" | jq -r '.source // "unknown"')
CREATED_AT=$(echo "$event" | jq -r '.created_at // ""')

# Extract tags if present
TAGS=$(echo "$event" | jq -r '.tags // {}')

echo "✅ Successfully parsed incident:"
echo "  🆔 ID: $INCIDENT_ID"
echo "  📝 Title: $INCIDENT_TITLE"
echo "  🚨 Severity: $INCIDENT_SEVERITY"
echo "  🔗 URL: $INCIDENT_URL"
echo "  💬 Slack suggestion: $SLACK_CHANNEL_SUGGESTION"
echo "  🏷️ Source: $SOURCE_SYSTEM"

# Validate required fields
if [ "$INCIDENT_ID" = "UNKNOWN" ] || [ -z "$INCIDENT_ID" ]; then
    echo "❌ Error: Incident ID is required"
    exit 1
fi

if [ -z "$INCIDENT_TITLE" ]; then
    echo "❌ Error: Incident title is required"
    exit 1
fi

if [ -z "$SLACK_CHANNEL_SUGGESTION" ]; then
    echo "⚠️ Warning: No Slack channel suggestion provided"
    SLACK_CHANNEL_SUGGESTION="#incident-$(echo "$INCIDENT_ID" | tr '[:upper:]' '[:lower:]')"
    echo "  💡 Using auto-generated: $SLACK_CHANNEL_SUGGESTION"
fi

# Create structured incident data
cat << EOF
{
  "incident_id": "$INCIDENT_ID",
  "incident_title": "$INCIDENT_TITLE", 
  "incident_severity": "$INCIDENT_SEVERITY",
  "incident_description": "$INCIDENT_DESCRIPTION",
  "incident_url": "$INCIDENT_URL",
  "slack_channel_suggestion": "$SLACK_CHANNEL_SUGGESTION",
  "source_system": "$SOURCE_SYSTEM",
  "created_at": "$CREATED_AT",
  "tags": $TAGS,
  "parsed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "step_status": "completed",
  "validation": {
    "has_id": $([ "$INCIDENT_ID" != "UNKNOWN" ] && echo "true" || echo "false"),
    "has_title": $([ -n "$INCIDENT_TITLE" ] && echo "true" || echo "false"),
    "has_slack_channel": $([ -n "$SLACK_CHANNEL_SUGGESTION" ] && echo "true" || echo "false"),
    "severity_valid": $(echo "$INCIDENT_SEVERITY" | grep -E "^(critical|high|medium|low)$" >/dev/null && echo "true" || echo "false")
  }
}
EOF

echo "✅ [STEP 1/7] Incident parsing completed successfully"'''
    
    @staticmethod
    def validate_incident_data(data: Dict[str, Any]) -> bool:
        """Validate parsed incident data."""
        required_fields = ['incident_id', 'incident_title', 'incident_severity']
        
        for field in required_fields:
            if field not in data or not data[field]:
                return False
        
        # Validate severity
        valid_severities = ['critical', 'high', 'medium', 'low']
        if data['incident_severity'] not in valid_severities:
            return False
        
        return True
    
    @staticmethod
    def create_test_event() -> IncidentEvent:
        """Create a test incident event for development."""
        from ..models.incident import KubiyaMetadata
        
        return IncidentEvent(
            id="INC-2024-PROD-TEST-001",
            title="Production Payment Gateway Database Crisis",
            url="https://app.datadoghq.com/incidents/INC-2024-PROD-TEST-001",
            severity="critical",
            body="""🚨 CRITICAL PRODUCTION INCIDENT 🚨

Payment gateway experiencing severe issues:

**Symptoms:**
- Error rate: 35% (threshold: 2%)
- Response time: 4.2s (SLA: 500ms)  
- Database connections: 98% capacity
- Failed transactions: 2,847
- Revenue impact: $47,000

**Timeline:**
- 14:32 UTC: First alerts triggered
- 14:35 UTC: Error rate spike detected
- 14:38 UTC: Database connection saturation
- 14:40 UTC: Payment failures escalating

**Impact:**
- Payment processing completely degraded
- Customer complaints increasing
- Revenue loss accelerating

**Needs immediate investigation:**
- Database connection pool analysis
- Recent deployment correlation
- Resource utilization review
- Error log analysis""",
            kubiya=KubiyaMetadata(slack_channel_id="#inc-payment-gateway-crisis"),
            source="datadog",
            tags={
                "service": "payment-gateway",
                "environment": "production", 
                "team": "platform",
                "priority": "p0"
            }
        )