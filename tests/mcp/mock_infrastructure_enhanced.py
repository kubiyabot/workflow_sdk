"""Enhanced mock infrastructure for comprehensive MCP testing.

This module provides advanced mock scenarios including stateful mocks,
network simulation, resource constraints, and performance testing support.
"""

import asyncio
import random
import time
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from unittest.mock import AsyncMock, Mock
from dataclasses import dataclass, field
import json


@dataclass
class NetworkCondition:
    """Represents network conditions for simulation."""
    latency_ms: float = 50.0
    bandwidth_mbps: float = 100.0
    packet_loss_rate: float = 0.0
    jitter_ms: float = 0.0
    is_connected: bool = True


@dataclass
class ResourceState:
    """Tracks system resource state."""
    cpu_usage_percent: float = 10.0
    memory_usage_mb: float = 100.0
    disk_usage_percent: float = 30.0
    open_file_descriptors: int = 50
    network_connections: int = 10


@dataclass
class WorkflowExecutionState:
    """Tracks workflow execution state across interactions."""
    execution_id: str
    status: str = "pending"
    progress_percent: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    resource_allocation: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)


class StatefulMockClient:
    """Mock client that maintains state across multiple interactions."""
    
    def __init__(self):
        self.executions: Dict[str, WorkflowExecutionState] = {}
        self.resource_state = ResourceState()
        self.network_condition = NetworkCondition()
        self.authentication_sessions: Dict[str, datetime] = {}
        self.allocated_resources: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    async def compile_workflow(self, dsl_code: str, **kwargs) -> Dict[str, Any]:
        """Compile workflow with stateful behavior."""
        await self._simulate_network_delay()
        
        # Simulate resource usage for compilation
        compilation_cost = len(dsl_code) * 0.001  # CPU cost based on DSL size
        self.resource_state.cpu_usage_percent += compilation_cost
        
        workflow_id = f"wf_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Check for compilation errors based on DSL content
        if "invalid" in dsl_code.lower() or "error" in dsl_code.lower():
            return {
                "workflow_id": None,
                "status": "failed",
                "validation_errors": ["Invalid DSL syntax detected"],
                "compilation_time": random.uniform(0.5, 2.0)
            }
        
        # Successful compilation
        return {
            "workflow_id": workflow_id,
            "status": "compiled",
            "validation_errors": [],
            "manifest": self._generate_manifest(dsl_code),
            "compilation_time": random.uniform(0.1, 1.0),
            "docker_required": "docker:" in dsl_code
        }
    
    async def execute_workflow(self, workflow_input: Union[str, Dict], **kwargs) -> Dict[str, Any]:
        """Execute workflow with stateful tracking."""
        await self._simulate_network_delay()
        
        execution_id = f"exec_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Create execution state
        execution_state = WorkflowExecutionState(
            execution_id=execution_id,
            status="running",
            start_time=datetime.now()
        )
        
        # Check resource availability
        if not self._check_resource_availability():
            execution_state.status = "failed"
            execution_state.errors.append("Insufficient resources available")
            execution_state.end_time = datetime.now()
            self.executions[execution_id] = execution_state
            
            return {
                "execution_id": execution_id,
                "status": "failed",
                "error": "Resource exhaustion",
                "logs": ["Resource allocation failed"]
            }
        
        # Allocate resources
        self._allocate_resources(execution_id)
        execution_state.resource_allocation = self.allocated_resources.get(execution_id, {})
        
        # Simulate execution progress
        await self._simulate_execution_progress(execution_state)
        
        # Store execution state
        self.executions[execution_id] = execution_state
        
        return {
            "execution_id": execution_id,
            "status": execution_state.status,
            "exit_code": 0 if execution_state.status == "completed" else 1,
            "output": "Execution completed successfully" if execution_state.status == "completed" else None,
            "error": execution_state.errors[0] if execution_state.errors else None,
            "logs": execution_state.logs,
            "duration": self._calculate_duration(execution_state),
            "resource_usage": execution_state.resource_allocation
        }
    
    async def get_runners(self, **kwargs) -> Dict[str, Any]:
        """Get runners with dynamic state."""
        await self._simulate_network_delay()
        
        runners = []
        for i in range(3):
            # Simulate runner health based on resource state
            runner_healthy = (
                self.resource_state.cpu_usage_percent < 80 and
                self.resource_state.memory_usage_mb < 8000 and
                random.random() > 0.1  # 10% chance of random failure
            )
            
            runner = {
                "id": f"runner-{i+1}",
                "name": f"Enhanced Runner {i+1}",
                "status": "healthy" if runner_healthy else "unhealthy",
                "version": "2.1.0",
                "capabilities": ["python", "docker", "kubernetes"],
                "last_heartbeat": datetime.now().isoformat(),
                "health_info": {
                    "cpu_usage": self.resource_state.cpu_usage_percent + random.uniform(-5, 5),
                    "memory_usage": self.resource_state.memory_usage_mb + random.uniform(-50, 50),
                    "disk_usage": self.resource_state.disk_usage_percent + random.uniform(-2, 2)
                }
            }
            runners.append(runner)
        
        return {
            "runners": runners,
            "total_count": len(runners),
            "healthy_count": sum(1 for r in runners if r["status"] == "healthy"),
            "last_refresh": datetime.now().isoformat()
        }
    
    async def get_integrations(self, **kwargs) -> Dict[str, Any]:
        """Get integrations with category filtering."""
        await self._simulate_network_delay()
        
        all_integrations = [
            {
                "name": "enhanced_slack",
                "description": "Enhanced Slack integration with advanced features",
                "category": "communication",
                "docker_image": "enhanced/slack:2.0",
                "required_secrets": ["SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET"],
                "version": "2.0.0",
                "enabled": True
            },
            {
                "name": "advanced_github",
                "description": "Advanced GitHub integration with CI/CD support",
                "category": "development",
                "docker_image": "enhanced/github:1.5",
                "required_secrets": ["GITHUB_TOKEN", "GITHUB_WEBHOOK_SECRET"],
                "version": "1.5.0",
                "enabled": True
            },
            {
                "name": "enterprise_aws",
                "description": "Enterprise AWS integration with full service support",
                "category": "cloud",
                "docker_image": "enhanced/aws:3.2",
                "required_secrets": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
                "version": "3.2.0",
                "enabled": True
            }
        ]
        
        # Filter by category if specified
        category_filter = kwargs.get("category")
        if category_filter:
            filtered_integrations = [
                i for i in all_integrations 
                if i["category"] == category_filter
            ]
        else:
            filtered_integrations = all_integrations
        
        return {
            "integrations": filtered_integrations,
            "categories": ["communication", "development", "cloud"],
            "total_count": len(all_integrations),
            "filtered_count": len(filtered_integrations),
            "category_filter": category_filter
        }
    
    async def get_secrets(self, **kwargs) -> Dict[str, Any]:
        """Get secrets with pattern filtering."""
        await self._simulate_network_delay()
        
        all_secrets = [
            {
                "name": "ENHANCED_API_KEY",
                "description": "Enhanced API key for external services",
                "task_type": "authentication",
                "required": True,
                "pattern": "ENHANCED_*",
                "last_updated": datetime.now().isoformat()
            },
            {
                "name": "DATABASE_PASSWORD",
                "description": "Database connection password",
                "task_type": "database",
                "required": True,
                "pattern": "DATABASE_*",
                "last_updated": (datetime.now() - timedelta(days=30)).isoformat()
            },
            {
                "name": "ENCRYPTION_KEY",
                "description": "Data encryption key",
                "task_type": "security",
                "required": True,
                "pattern": "ENCRYPTION_*",
                "last_updated": (datetime.now() - timedelta(days=7)).isoformat()
            }
        ]
        
        # Filter by pattern if specified
        pattern_filter = kwargs.get("pattern")
        if pattern_filter:
            # Simple pattern matching (could be enhanced)
            pattern_prefix = pattern_filter.replace("*", "")
            filtered_secrets = [
                s for s in all_secrets 
                if s["name"].startswith(pattern_prefix)
            ]
        else:
            filtered_secrets = all_secrets
        
        return {
            "secrets": filtered_secrets,
            "total_count": len(all_secrets),
            "required_count": sum(1 for s in all_secrets if s["required"]),
            "optional_count": sum(1 for s in all_secrets if not s["required"]),
            "pattern_filter": pattern_filter
        }
    
    async def _simulate_network_delay(self):
        """Simulate network latency and conditions."""
        if not self.network_condition.is_connected:
            raise ConnectionError("Network connection lost")
        
        # Base latency with jitter
        delay = (self.network_condition.latency_ms + 
                random.uniform(-self.network_condition.jitter_ms, self.network_condition.jitter_ms)) / 1000.0
        
        # Packet loss simulation
        if random.random() < self.network_condition.packet_loss_rate:
            # Simulate packet retransmission delay
            delay *= 3
        
        await asyncio.sleep(max(0, delay))
    
    def _check_resource_availability(self) -> bool:
        """Check if sufficient resources are available."""
        return (
            self.resource_state.cpu_usage_percent < 90 and
            self.resource_state.memory_usage_mb < 15000 and
            self.resource_state.open_file_descriptors < 900
        )
    
    def _allocate_resources(self, execution_id: str):
        """Allocate resources for execution."""
        with self._lock:
            allocation = {
                "cpu_cores": 2,
                "memory_mb": 1024,
                "disk_mb": 500,
                "allocated_at": datetime.now().isoformat()
            }
            self.allocated_resources[execution_id] = allocation
            
            # Update global resource state
            self.resource_state.memory_usage_mb += allocation["memory_mb"]
            self.resource_state.cpu_usage_percent += 20
            self.resource_state.open_file_descriptors += 10
    
    def _deallocate_resources(self, execution_id: str):
        """Deallocate resources after execution."""
        with self._lock:
            if execution_id in self.allocated_resources:
                allocation = self.allocated_resources[execution_id]
                
                # Update global resource state
                self.resource_state.memory_usage_mb -= allocation["memory_mb"]
                self.resource_state.cpu_usage_percent -= 20
                self.resource_state.open_file_descriptors -= 10
                
                del self.allocated_resources[execution_id]
    
    async def _simulate_execution_progress(self, execution_state: WorkflowExecutionState):
        """Simulate realistic execution progress."""
        execution_state.logs.append("Execution started")
        
        # Simulate multi-step execution
        steps = ["initialization", "processing", "validation", "completion"]
        
        for i, step in enumerate(steps):
            execution_state.logs.append(f"Starting {step}")
            
            # Simulate step duration with some variability
            step_duration = random.uniform(0.1, 0.5)
            await asyncio.sleep(step_duration)
            
            execution_state.progress_percent = int((i + 1) / len(steps) * 100)
            execution_state.logs.append(f"Completed {step}")
            
            # Simulate occasional errors
            if random.random() < 0.05:  # 5% chance of error
                execution_state.status = "failed"
                execution_state.errors.append(f"Error during {step}")
                execution_state.end_time = datetime.now()
                self._deallocate_resources(execution_state.execution_id)
                return
        
        execution_state.status = "completed"
        execution_state.end_time = datetime.now()
        execution_state.logs.append("Execution completed successfully")
        self._deallocate_resources(execution_state.execution_id)
    
    def _calculate_duration(self, execution_state: WorkflowExecutionState) -> float:
        """Calculate execution duration."""
        if execution_state.start_time and execution_state.end_time:
            return (execution_state.end_time - execution_state.start_time).total_seconds()
        return 0.0
    
    def _generate_manifest(self, dsl_code: str) -> Dict[str, Any]:
        """Generate workflow manifest from DSL."""
        lines = dsl_code.strip().split('\n')
        name = "generated_workflow"
        
        # Extract name from DSL
        for line in lines:
            if line.strip().startswith("name:"):
                name = line.split(":", 1)[1].strip()
                break
        
        return {
            "name": name,
            "description": f"Generated workflow from DSL",
            "steps": [
                {
                    "name": f"step_{i+1}",
                    "run": "echo 'Generated step'",
                    "docker": "docker:" in dsl_code
                }
                for i in range(random.randint(1, 3))
            ]
        }


class NetworkSimulator:
    """Simulates various network conditions for testing."""
    
    def __init__(self):
        self.current_condition = NetworkCondition()
        self.condition_history: List[NetworkCondition] = []
    
    def set_condition(self, condition: NetworkCondition):
        """Set current network condition."""
        self.condition_history.append(self.current_condition)
        self.current_condition = condition
    
    def simulate_connection_loss(self, duration_seconds: float):
        """Simulate temporary connection loss."""
        async def _simulate():
            original_condition = self.current_condition
            self.current_condition.is_connected = False
            await asyncio.sleep(duration_seconds)
            self.current_condition = original_condition
        
        return _simulate()
    
    def simulate_high_latency(self, latency_ms: float, duration_seconds: float):
        """Simulate high latency condition."""
        async def _simulate():
            original_latency = self.current_condition.latency_ms
            self.current_condition.latency_ms = latency_ms
            await asyncio.sleep(duration_seconds)
            self.current_condition.latency_ms = original_latency
        
        return _simulate()
    
    def simulate_packet_loss(self, loss_rate: float, duration_seconds: float):
        """Simulate packet loss."""
        async def _simulate():
            original_loss_rate = self.current_condition.packet_loss_rate
            self.current_condition.packet_loss_rate = loss_rate
            await asyncio.sleep(duration_seconds)
            self.current_condition.packet_loss_rate = original_loss_rate
        
        return _simulate()


class PerformanceMonitor:
    """Monitor and simulate performance metrics."""
    
    def __init__(self):
        self.metrics_history: List[Dict[str, Any]] = []
        self.current_metrics = {
            "cpu_usage": 10.0,
            "memory_usage_mb": 100.0,
            "disk_io_mbps": 50.0,
            "network_io_mbps": 10.0
        }
    
    def record_metrics(self, operation: str, duration: float, **extra_metrics):
        """Record performance metrics for an operation."""
        timestamp = datetime.now()
        metrics = {
            "timestamp": timestamp.isoformat(),
            "operation": operation,
            "duration_seconds": duration,
            **self.current_metrics,
            **extra_metrics
        }
        self.metrics_history.append(metrics)
        return metrics
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report."""
        if not self.metrics_history:
            return {"message": "No performance data available"}
        
        # Calculate basic statistics
        durations = [m["duration_seconds"] for m in self.metrics_history]
        cpu_usage = [m["cpu_usage"] for m in self.metrics_history]
        memory_usage = [m["memory_usage_mb"] for m in self.metrics_history]
        
        return {
            "total_operations": len(self.metrics_history),
            "average_duration": sum(durations) / len(durations),
            "max_duration": max(durations),
            "min_duration": min(durations),
            "average_cpu_usage": sum(cpu_usage) / len(cpu_usage),
            "peak_memory_usage": max(memory_usage),
            "performance_trends": self._analyze_trends()
        }
    
    def _analyze_trends(self) -> Dict[str, str]:
        """Analyze performance trends."""
        if len(self.metrics_history) < 2:
            return {"trend": "insufficient_data"}
        
        recent_avg = sum(m["duration_seconds"] for m in self.metrics_history[-5:]) / min(5, len(self.metrics_history))
        overall_avg = sum(m["duration_seconds"] for m in self.metrics_history) / len(self.metrics_history)
        
        if recent_avg > overall_avg * 1.2:
            trend = "degrading"
        elif recent_avg < overall_avg * 0.8:
            trend = "improving"
        else:
            trend = "stable"
        
        return {
            "performance_trend": trend,
            "recent_average": recent_avg,
            "overall_average": overall_avg
        }


class EnhancedMockScenarios:
    """Collection of enhanced mock scenarios for comprehensive testing."""
    
    @staticmethod
    def create_network_failure_scenario() -> StatefulMockClient:
        """Create a mock client with network failure simulation."""
        client = StatefulMockClient()
        client.network_condition = NetworkCondition(
            latency_ms=200.0,
            packet_loss_rate=0.1,
            is_connected=False
        )
        return client
    
    @staticmethod
    def create_resource_exhaustion_scenario() -> StatefulMockClient:
        """Create a mock client with resource exhaustion."""
        client = StatefulMockClient()
        client.resource_state = ResourceState(
            cpu_usage_percent=95.0,
            memory_usage_mb=14000.0,
            disk_usage_percent=98.0,
            open_file_descriptors=950
        )
        return client
    
    @staticmethod
    def create_performance_testing_scenario() -> StatefulMockClient:
        """Create a mock client optimized for performance testing."""
        client = StatefulMockClient()
        client.network_condition = NetworkCondition(
            latency_ms=10.0,
            bandwidth_mbps=1000.0,
            packet_loss_rate=0.0
        )
        return client
    
    @staticmethod
    def create_intermittent_failure_scenario() -> StatefulMockClient:
        """Create a mock client with intermittent failures."""
        client = StatefulMockClient()
        
        # Override methods to inject random failures
        original_compile = client.compile_workflow
        async def intermittent_compile(*args, **kwargs):
            if random.random() < 0.3:  # 30% failure rate
                raise Exception("Intermittent service failure")
            return await original_compile(*args, **kwargs)
        
        client.compile_workflow = intermittent_compile
        return client


# Export enhanced mock infrastructure
ENHANCED_MOCK_INFRASTRUCTURE = {
    "StatefulMockClient": StatefulMockClient,
    "NetworkSimulator": NetworkSimulator,
    "PerformanceMonitor": PerformanceMonitor,
    "EnhancedMockScenarios": EnhancedMockScenarios
}