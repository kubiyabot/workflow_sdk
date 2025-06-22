"""
Execution Manager for Workflow Server

Manages workflow executions, tracks state, and provides execution history.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import logging

from ..core.types import WorkflowStatus, ExecutionResult

logger = logging.getLogger(__name__)


class ExecutionManager:
    """Manages workflow executions and their lifecycle."""
    
    def __init__(self, max_concurrent: int = 100, default_timeout: int = 3600):
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.executions: Dict[str, ExecutionResult] = {}
        self.events: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
    async def start(self) -> None:
        """Start the execution manager."""
        logger.info(f"Execution manager started (max concurrent: {self.max_concurrent})")
        
    async def stop(self) -> None:
        """Stop the execution manager."""
        logger.info("Execution manager stopping...")
        # Cancel any running executions
        for exec_id, result in self.executions.items():
            if result.status in [WorkflowStatus.PENDING, WorkflowStatus.RUNNING]:
                logger.warning(f"Cancelling execution {exec_id}")
                result.status = WorkflowStatus.CANCELLED
                
    @property
    def active_count(self) -> int:
        """Get count of active executions."""
        return sum(1 for r in self.executions.values() 
                  if r.status in [WorkflowStatus.PENDING, WorkflowStatus.RUNNING])
        
    async def create_execution(self, workflow_name: str) -> str:
        """Create a new execution."""
        async with self._lock:
            exec_id = str(uuid.uuid4())
            self.executions[exec_id] = ExecutionResult(
                execution_id=exec_id,
                workflow_name=workflow_name,
                status=WorkflowStatus.PENDING,
                start_time=datetime.utcnow(),
                outputs={},
                errors=[],
                step_results={}
            )
            self.events[exec_id] = []
            return exec_id
            
    async def get_execution(self, execution_id: str) -> Optional[ExecutionResult]:
        """Get execution by ID."""
        return self.executions.get(execution_id)
        
    async def add_event(self, execution_id: str, event: Dict[str, Any]) -> None:
        """Add event to execution history."""
        if execution_id in self.events:
            self.events[execution_id].append(event)
            
    async def store_result(self, execution_id: str, result: ExecutionResult) -> None:
        """Store execution result."""
        async with self._lock:
            self.executions[execution_id] = result
            
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an execution."""
        async with self._lock:
            if execution_id in self.executions:
                result = self.executions[execution_id]
                if result.status in [WorkflowStatus.PENDING, WorkflowStatus.RUNNING]:
                    result.status = WorkflowStatus.CANCELLED
                    result.end_time = datetime.utcnow()
                    return True
            return False
            
    async def list_executions(
        self, 
        status: Optional[WorkflowStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ExecutionResult]:
        """List executions with optional filtering."""
        results = list(self.executions.values())
        
        # Filter by status if provided
        if status:
            results = [r for r in results if r.status == status]
            
        # Sort by start time (most recent first)
        results.sort(key=lambda r: r.start_time, reverse=True)
        
        # Apply pagination
        return results[offset:offset + limit]
        
    async def get_events(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get events for an execution."""
        return self.events.get(execution_id, []) 