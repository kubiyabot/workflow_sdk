"""
Streaming support for ADK Provider.

Implements SSE and Vercel AI SDK format streaming for real-time
workflow generation and execution feedback.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class SSEFormatter:
    """Format events as Server-Sent Events (SSE)."""
    
    def format_text(self, text: str) -> str:
        """Format text content as SSE."""
        lines = text.split('\n')
        formatted = []
        for line in lines:
            if line:
                formatted.append(f"data: {json.dumps({'type': 'text', 'content': line})}")
        return '\n'.join(formatted) + '\n\n'
    
    def format_tool_call(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Format tool call as SSE."""
        data = {
            'type': 'tool_call',
            'tool': tool_name,
            'args': args
        }
        return f"data: {json.dumps(data)}\n\n"
    
    def format_tool_result(self, tool_name: str, result: Any) -> str:
        """Format tool result as SSE."""
        data = {
            'type': 'tool_result',
            'tool': tool_name,
            'result': result
        }
        return f"data: {json.dumps(data)}\n\n"
    
    def format_error(self, error: str) -> str:
        """Format error as SSE."""
        data = {
            'type': 'error',
            'error': error
        }
        return f"data: {json.dumps(data)}\n\n"
    
    def format_completion(self) -> str:
        """Format completion event as SSE."""
        data = {'type': 'done'}
        return f"data: {json.dumps(data)}\n\ndata: [DONE]\n\n"


class VercelAIFormatter:
    """
    Format events for Vercel AI SDK.
    
    Vercel AI SDK expects specific event types and structure for streaming.
    """
    
    def format_text(self, text: str) -> str:
        """Format text content for Vercel AI SDK."""
        # Vercel expects each text chunk as a separate data event
        event_id = f"text-{uuid.uuid4().hex[:8]}"
        data = {
            "type": "text",
            "id": event_id,
            "content": text
        }
        return f"data: {json.dumps(data)}\n\n"
    
    def format_tool_call(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Format tool call for Vercel AI SDK."""
        event_id = f"tool-{uuid.uuid4().hex[:8]}"
        data = {
            "type": "tool_call",
            "id": event_id,
            "name": tool_name,
            "arguments": json.dumps(args)
        }
        return f"data: {json.dumps(data)}\n\n"
    
    def format_tool_result(self, tool_name: str, result: Any) -> str:
        """Format tool result for Vercel AI SDK."""
        event_id = f"result-{uuid.uuid4().hex[:8]}"
        data = {
            "type": "tool_result",
            "id": event_id,
            "name": tool_name,
            "result": result if isinstance(result, str) else json.dumps(result)
        }
        return f"data: {json.dumps(data)}\n\n"
    
    def format_error(self, error: str) -> str:
        """Format error for Vercel AI SDK."""
        data = {
            "type": "error",
            "error": {
                "message": error,
                "type": "provider_error"
            }
        }
        return f"data: {json.dumps(data)}\n\n"
    
    def format_completion(self) -> str:
        """Format completion event for Vercel AI SDK."""
        # Vercel expects a finish reason
        data = {
            "type": "finish",
            "finishReason": "stop"
        }
        return f"data: {json.dumps(data)}\n\n"
    
    def format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata for Vercel AI SDK."""
        data = {
            "type": "metadata",
            "metadata": metadata
        }
        return f"data: {json.dumps(data)}\n\n"


@dataclass
class StreamHandler:
    """
    Handle streaming events from ADK agents.
    
    Collects events and formats them according to the specified format.
    """
    
    formatter: Any
    events: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle an event from ADK agents."""
        event_type = event.get('type', '')
        
        if event_type == 'text':
            formatted = self.formatter.format_text(event['content'])
            self.events.append(formatted)
        
        elif event_type == 'tool_call':
            formatted = self.formatter.format_tool_call(
                event['tool'],
                event.get('args', {})
            )
            self.events.append(formatted)
        
        elif event_type == 'tool_result':
            formatted = self.formatter.format_tool_result(
                event['tool'],
                event.get('result')
            )
            self.events.append(formatted)
        
        elif event_type == 'error':
            formatted = self.formatter.format_error(event['error'])
            self.events.append(formatted)
        
        elif event_type == 'metadata':
            self.metadata.update(event.get('metadata', {}))
            if hasattr(self.formatter, 'format_metadata'):
                formatted = self.formatter.format_metadata(event['metadata'])
                self.events.append(formatted)
    
    def complete(self) -> None:
        """Mark stream as complete."""
        completion = self.formatter.format_completion()
        self.events.append(completion)
    
    def get_response(self) -> List[str]:
        """Get all formatted events."""
        return self.events
    
    async def async_handle_event(self, event: Dict[str, Any]) -> Optional[str]:
        """Handle event and return formatted string immediately."""
        event_type = event.get('type', '')
        
        if event_type == 'text':
            return self.formatter.format_text(event['content'])
        elif event_type == 'tool_call':
            return self.formatter.format_tool_call(
                event['tool'],
                event.get('args', {})
            )
        elif event_type == 'tool_result':
            return self.formatter.format_tool_result(
                event['tool'],
                event.get('result')
            )
        elif event_type == 'error':
            return self.formatter.format_error(event['error'])
        elif event_type == 'metadata' and hasattr(self.formatter, 'format_metadata'):
            return self.formatter.format_metadata(event['metadata'])
        
        return None 