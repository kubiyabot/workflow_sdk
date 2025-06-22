"""
SSE Handler for Workflow Server

Handles Server-Sent Events streaming for real-time workflow updates.
"""

import asyncio
import json
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SSEHandler:
    """Handles SSE streaming for workflow execution events."""
    
    def __init__(self, keep_alive_interval: int = 30):
        self.keep_alive_interval = keep_alive_interval
        self._active_streams: Dict[str, bool] = {}
        
    async def stream_events(
        self,
        execution_id: str,
        event_source: AsyncGenerator[Dict[str, Any], None]
    ) -> AsyncGenerator[str, None]:
        """Stream events in SSE format."""
        self._active_streams[execution_id] = True
        
        try:
            # Send initial connection event
            yield self._format_sse_event({
                "event": "connected",
                "data": {
                    "execution_id": execution_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            
            # Create keep-alive task
            keep_alive_task = asyncio.create_task(
                self._send_keep_alive(execution_id)
            )
            
            try:
                # Stream events from source
                async for event in event_source:
                    if not self._active_streams.get(execution_id, False):
                        break
                        
                    yield self._format_sse_event(event)
                    
            finally:
                # Cancel keep-alive task
                keep_alive_task.cancel()
                try:
                    await keep_alive_task
                except asyncio.CancelledError:
                    pass
                    
        finally:
            # Cleanup
            self._active_streams.pop(execution_id, None)
            
    async def _send_keep_alive(self, execution_id: str) -> None:
        """Send periodic keep-alive messages."""
        while self._active_streams.get(execution_id, False):
            await asyncio.sleep(self.keep_alive_interval)
            
            # Send keep-alive ping
            yield self._format_sse_event({
                "event": "keep-alive",
                "data": {
                    "execution_id": execution_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            
    def _format_sse_event(self, event: Dict[str, Any]) -> str:
        """Format event for SSE protocol."""
        event_type = event.get("event", "message")
        data = event.get("data", {})
        
        # Format according to SSE spec
        lines = []
        
        if event_type != "message":
            lines.append(f"event: {event_type}")
            
        # Split data into multiple lines if needed
        data_str = json.dumps(data, default=str)
        for line in data_str.split('\n'):
            lines.append(f"data: {line}")
            
        # Add double newline to terminate event
        return '\n'.join(lines) + '\n\n'
        
    def stop_stream(self, execution_id: str) -> None:
        """Stop streaming for an execution."""
        self._active_streams[execution_id] = False 