"""
Workflow executors for incident response automation.

This module provides execution classes that handle workflow deployment,
execution, monitoring, and result processing with proper error handling
and logging.
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, Iterator, Callable, Union, List
from pydantic import ValidationError

from kubiya_workflow_sdk.client import KubiyaClient
from kubiya_workflow_sdk.dsl import Workflow

from .models import (
    IncidentData, WorkflowConfig, ExecutionResult, WorkflowStatus,
    IncidentAnalysis, KubernetesFindings, MonitoringFindings,
    AggregatedAnalysis, ValidationResult, ValidationError as ModelValidationError
)


class WorkflowExecutor:
    """
    Synchronous workflow executor with comprehensive error handling and validation.
    
    This class handles the complete lifecycle of workflow execution including
    validation, deployment, execution, monitoring, and result processing.
    """
    
    def __init__(self, api_key: str, config: Optional[WorkflowConfig] = None):
        """Initialize the workflow executor."""
        self.api_key = api_key
        self.config = config or WorkflowConfig()
        self.client = KubiyaClient(api_key=api_key)
        self._execution_history: List[ExecutionResult] = []
    
    def validate_incident_data(self, incident_data: Dict[str, Any]) -> ValidationResult:
        """Validate incident data against Pydantic model."""
        try:
            # Attempt to create IncidentData model
            validated_data = IncidentData(**incident_data)
            return ValidationResult(is_valid=True, errors=[], warnings=[])
        
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                errors.append(ModelValidationError(
                    field=field,
                    message=error["msg"],
                    value=error.get("input")
                ))
            
            return ValidationResult(is_valid=False, errors=errors, warnings=[])
        
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[ModelValidationError(field="general", message=str(e))],
                warnings=[]
            )
    
    def validate_workflow(self, workflow: Workflow) -> ValidationResult:
        """Validate workflow structure and configuration."""
        try:
            # Convert workflow to dict to check structure
            workflow_dict = workflow.to_dict()
            
            errors = []
            warnings = []
            
            # Basic structure validation
            if not workflow_dict.get("name"):
                errors.append(ModelValidationError(
                    field="name", 
                    message="Workflow name is required"
                ))
            
            if not workflow_dict.get("steps"):
                errors.append(ModelValidationError(
                    field="steps",
                    message="Workflow must have at least one step"
                ))
            
            # Step validation
            steps = workflow_dict.get("steps", [])
            if len(steps) == 0:
                errors.append(ModelValidationError(
                    field="steps",
                    message="No steps defined in workflow"
                ))
            
            # Check for required step types
            step_names = [step.get("name", "") for step in steps]
            if "validate-inputs" not in step_names:
                warnings.append("No input validation step found")
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings
            )
        
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[ModelValidationError(field="workflow", message=str(e))],
                warnings=[]
            )
    
    def execute_workflow(
        self,
        workflow: Workflow,
        incident_data: Dict[str, Any],
        validate_inputs: bool = True
    ) -> ExecutionResult:
        """
        Execute a workflow with comprehensive error handling and result processing.
        
        Args:
            workflow: The workflow to execute
            incident_data: Incident data dictionary
            validate_inputs: Whether to validate inputs before execution
            
        Returns:
            ExecutionResult with comprehensive execution data
        """
        result = ExecutionResult(
            start_time=datetime.now(),
            status=WorkflowStatus.PENDING
        )
        
        try:
            # Validate inputs if requested
            if validate_inputs:
                incident_validation = self.validate_incident_data(incident_data)
                if not incident_validation.is_valid:
                    result.status = WorkflowStatus.FAILED
                    result.errors = [f"Incident validation failed: {error.message}" for error in incident_validation.errors]
                    return result
                
                workflow_validation = self.validate_workflow(workflow)
                if not workflow_validation.is_valid:
                    result.status = WorkflowStatus.FAILED
                    result.errors = [f"Workflow validation failed: {error.message}" for error in workflow_validation.errors]
                    return result
                
                # Add warnings
                result.warnings.extend(incident_validation.warnings)
                result.warnings.extend(workflow_validation.warnings)
            
            # Parse and store incident data
            try:
                result.incident_data = IncidentData(**incident_data)
            except ValidationError:
                # If strict validation fails, store as-is and add warning
                result.add_warning("Incident data validation failed, proceeding with raw data")
            
            # Convert workflow to execution format
            workflow_dict = workflow.to_dict()
            
            # Execute workflow
            result.status = WorkflowStatus.RUNNING
            execution_response = self.client.execute_workflow(
                workflow_definition=workflow_dict,
                parameters=incident_data,
                stream=False
            )
            
            # Process execution response
            result = self._process_execution_response(result, execution_response)
            
        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.add_error(f"Workflow execution failed: {str(e)}")
        
        finally:
            result.end_time = datetime.now()
            if result.start_time and result.end_time:
                result.duration_seconds = (result.end_time - result.start_time).total_seconds()
            
            # Store in execution history
            self._execution_history.append(result)
        
        return result
    
    def _process_execution_response(
        self, 
        result: ExecutionResult, 
        response: Dict[str, Any]
    ) -> ExecutionResult:
        """Process the raw execution response and extract structured data."""
        try:
            # Store raw response
            if isinstance(response, dict):
                # Extract execution metadata
                result.execution_id = response.get("execution_id") or response.get("id")
                result.workflow_id = response.get("workflow_id") or response.get("workflowId")
                
                # Determine status
                status = response.get("status", "unknown").lower()
                if status in ["completed", "success"]:
                    result.status = WorkflowStatus.COMPLETED
                elif status in ["failed", "error"]:
                    result.status = WorkflowStatus.FAILED
                elif status in ["running", "executing"]:
                    result.status = WorkflowStatus.RUNNING
                else:
                    result.status = WorkflowStatus.COMPLETED  # Default for unknown
                
                # Extract step results
                if "steps" in response:
                    result.step_results = response["steps"]
                
                # Extract errors
                if "errors" in response and response["errors"]:
                    result.errors.extend(response["errors"])
                    if result.status == WorkflowStatus.COMPLETED:
                        result.status = WorkflowStatus.FAILED
                
                # Extract workflow outputs and parse them
                self._extract_workflow_outputs(result, response)
            
            else:
                result.add_warning(f"Unexpected response type: {type(response)}")
                result.status = WorkflowStatus.COMPLETED
        
        except Exception as e:
            result.add_error(f"Failed to process execution response: {str(e)}")
            result.status = WorkflowStatus.FAILED
        
        return result
    
    def _extract_workflow_outputs(self, result: ExecutionResult, response: Dict[str, Any]) -> None:
        """Extract and parse structured outputs from workflow execution."""
        try:
            # Look for outputs in various response formats
            outputs = response.get("outputs", {})
            
            # Also check step results for outputs
            if "steps" in response:
                for step_name, step_data in response["steps"].items():
                    if "output" in step_data:
                        outputs[step_name] = step_data["output"]
            
            # Parse specific outputs
            for output_name, output_value in outputs.items():
                try:
                    # Try to parse JSON outputs
                    if isinstance(output_value, str) and output_value.strip().startswith("{"):
                        parsed_output = json.loads(output_value)
                    else:
                        parsed_output = output_value
                    
                    # Map to specific model types
                    if "analysis" in output_name.lower():
                        try:
                            result.incident_analysis = IncidentAnalysis(**parsed_output)
                        except (ValidationError, TypeError):
                            result.add_warning(f"Failed to parse incident analysis: {output_name}")
                    
                    elif "k8s" in output_name.lower() or "kubernetes" in output_name.lower():
                        try:
                            result.kubernetes_findings = KubernetesFindings(**parsed_output)
                        except (ValidationError, TypeError):
                            result.add_warning(f"Failed to parse Kubernetes findings: {output_name}")
                    
                    elif "monitoring" in output_name.lower() or "metrics" in output_name.lower():
                        try:
                            result.monitoring_findings = MonitoringFindings(**parsed_output)
                        except (ValidationError, TypeError):
                            result.add_warning(f"Failed to parse monitoring findings: {output_name}")
                    
                    elif "aggregated" in output_name.lower() or "final" in output_name.lower():
                        try:
                            result.aggregated_analysis = AggregatedAnalysis(**parsed_output)
                        except (ValidationError, TypeError):
                            result.add_warning(f"Failed to parse aggregated analysis: {output_name}")
                
                except json.JSONDecodeError:
                    # Store as raw value if not JSON
                    continue
                except Exception as e:
                    result.add_warning(f"Error processing output {output_name}: {str(e)}")
        
        except Exception as e:
            result.add_warning(f"Error extracting workflow outputs: {str(e)}")
    
    def get_execution_history(self) -> List[ExecutionResult]:
        """Get the execution history."""
        return self._execution_history.copy()
    
    def get_last_execution(self) -> Optional[ExecutionResult]:
        """Get the last execution result."""
        return self._execution_history[-1] if self._execution_history else None


class StreamingWorkflowExecutor(WorkflowExecutor):
    """
    Streaming workflow executor that provides real-time execution monitoring.
    
    This class extends the base executor to provide streaming capabilities
    for real-time monitoring of workflow execution progress.
    """
    
    def execute_workflow_streaming(
        self,
        workflow: Workflow,
        incident_data: Dict[str, Any],
        event_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        validate_inputs: bool = True
    ) -> Iterator[Union[Dict[str, Any], ExecutionResult]]:
        """
        Execute workflow with streaming events and yield progress updates.
        
        Args:
            workflow: The workflow to execute
            incident_data: Incident data dictionary
            event_callback: Optional callback for processing events
            validate_inputs: Whether to validate inputs before execution
            
        Yields:
            Stream of events or final ExecutionResult
        """
        result = ExecutionResult(
            start_time=datetime.now(),
            status=WorkflowStatus.PENDING
        )
        
        try:
            # Validate inputs if requested
            if validate_inputs:
                incident_validation = self.validate_incident_data(incident_data)
                if not incident_validation.is_valid:
                    result.status = WorkflowStatus.FAILED
                    result.errors = [f"Incident validation failed: {error.message}" for error in incident_validation.errors]
                    yield result
                    return
                
                workflow_validation = self.validate_workflow(workflow)
                if not workflow_validation.is_valid:
                    result.status = WorkflowStatus.FAILED
                    result.errors = [f"Workflow validation failed: {error.message}" for error in workflow_validation.errors]
                    yield result
                    return
            
            # Parse incident data
            try:
                result.incident_data = IncidentData(**incident_data)
            except ValidationError:
                result.add_warning("Incident data validation failed, proceeding with raw data")
            
            # Convert workflow
            workflow_dict = workflow.to_dict()
            
            # Start streaming execution
            result.status = WorkflowStatus.RUNNING
            event_count = 0
            
            for event in self.client.execute_workflow(
                workflow_definition=workflow_dict,
                parameters=incident_data,
                stream=True
            ):
                event_count += 1
                
                # Process event through callback if provided
                if event_callback:
                    try:
                        event_callback(event)
                    except Exception as e:
                        result.add_warning(f"Event callback error: {str(e)}")
                
                # Yield the event
                yield event
                
                # Check for completion indicators in events
                if isinstance(event, dict):
                    if event.get("type") == "workflow.completed":
                        break
                    elif event.get("type") == "workflow.failed":
                        result.status = WorkflowStatus.FAILED
                        break
            
            # After streaming completes, get final result
            time.sleep(2)  # Brief delay to allow final processing
            
            # Try to get final execution status
            # Note: This would require additional API calls in a real implementation
            result.status = WorkflowStatus.COMPLETED
            result.add_warning(f"Streaming completed with {event_count} events")
            
        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.add_error(f"Streaming execution failed: {str(e)}")
        
        finally:
            result.end_time = datetime.now()
            if result.start_time and result.end_time:
                result.duration_seconds = (result.end_time - result.start_time).total_seconds()
            
            self._execution_history.append(result)
            yield result
    
    def execute_with_progress_tracking(
        self,
        workflow: Workflow,
        incident_data: Dict[str, Any],
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> ExecutionResult:
        """
        Execute workflow with progress tracking and callbacks.
        
        Args:
            workflow: The workflow to execute
            incident_data: Incident data dictionary
            progress_callback: Callback for progress updates (step_name, progress_percentage)
            
        Returns:
            ExecutionResult with execution data
        """
        total_steps = len(workflow.to_dict().get("steps", []))
        completed_steps = 0
        
        def event_processor(event: Dict[str, Any]) -> None:
            nonlocal completed_steps
            
            # Extract step completion info from events
            if isinstance(event, dict):
                if event.get("type") == "step.completed":
                    completed_steps += 1
                    progress = (completed_steps / total_steps) * 100 if total_steps > 0 else 0
                    
                    if progress_callback:
                        step_name = event.get("step_name", f"Step {completed_steps}")
                        progress_callback(step_name, progress)
        
        # Execute with streaming and collect final result
        final_result = None
        for item in self.execute_workflow_streaming(
            workflow=workflow,
            incident_data=incident_data,
            event_callback=event_processor,
            validate_inputs=True
        ):
            if isinstance(item, ExecutionResult):
                final_result = item
                break
        
        return final_result or ExecutionResult(status=WorkflowStatus.FAILED)


class ExecutionResultProcessor:
    """Utility class for processing and analyzing execution results."""
    
    @staticmethod
    def extract_summary(result: ExecutionResult) -> Dict[str, Any]:
        """Extract a summary of the execution result."""
        summary = {
            "execution_id": result.execution_id,
            "status": result.status.value if result.status else "unknown",
            "duration_seconds": result.duration_seconds,
            "success": result.is_successful(),
            "error_count": len(result.errors),
            "warning_count": len(result.warnings)
        }
        
        # Add incident info if available
        if result.incident_data:
            summary["incident"] = {
                "id": result.incident_data.incident_id,
                "title": result.incident_data.incident_title,
                "severity": result.incident_data.incident_severity.value
            }
        
        # Add analysis summary if available
        if result.incident_analysis:
            summary["analysis"] = {
                "category": result.incident_analysis.incident_category.value,
                "urgency": result.incident_analysis.urgency_level.value,
                "confidence": result.incident_analysis.confidence_score
            }
        
        # Add findings summary
        findings_summary = {}
        if result.kubernetes_findings:
            findings_summary["kubernetes"] = {
                "status": result.kubernetes_findings.status,
                "confidence": result.kubernetes_findings.confidence
            }
        
        if result.monitoring_findings:
            findings_summary["monitoring"] = {
                "status": result.monitoring_findings.status,
                "confidence": result.monitoring_findings.confidence
            }
        
        if findings_summary:
            summary["findings"] = findings_summary
        
        return summary
    
    @staticmethod
    def generate_report(result: ExecutionResult) -> str:
        """Generate a human-readable report from execution result."""
        report_lines = [
            "# Incident Response Execution Report",
            f"**Execution ID:** {result.execution_id or 'N/A'}",
            f"**Status:** {result.status.value if result.status else 'Unknown'}",
            f"**Duration:** {result.duration_seconds:.2f}s" if result.duration_seconds else "**Duration:** N/A",
            ""
        ]
        
        # Incident information
        if result.incident_data:
            report_lines.extend([
                "## Incident Details",
                f"- **ID:** {result.incident_data.incident_id}",
                f"- **Title:** {result.incident_data.incident_title}",
                f"- **Severity:** {result.incident_data.incident_severity.value}",
                ""
            ])
        
        # Analysis results
        if result.incident_analysis:
            report_lines.extend([
                "## AI Analysis",
                f"- **Category:** {result.incident_analysis.incident_category.value}",
                f"- **Urgency:** {result.incident_analysis.urgency_level.value}",
                f"- **Estimated Impact:** {result.incident_analysis.estimated_impact.value}",
                f"- **Confidence:** {result.incident_analysis.confidence_score:.2f}",
                ""
            ])
        
        # Findings
        if result.kubernetes_findings or result.monitoring_findings:
            report_lines.append("## Investigation Findings")
            
            if result.kubernetes_findings:
                report_lines.extend([
                    f"### Kubernetes ({result.kubernetes_findings.status})",
                    f"- **Key Findings:** {', '.join(result.kubernetes_findings.key_findings[:3])}",
                    f"- **Confidence:** {result.kubernetes_findings.confidence:.2f}",
                    ""
                ])
            
            if result.monitoring_findings:
                report_lines.extend([
                    f"### Monitoring ({result.monitoring_findings.status})",
                    f"- **Key Findings:** {', '.join(result.monitoring_findings.key_findings[:3])}",
                    f"- **Confidence:** {result.monitoring_findings.confidence:.2f}",
                    ""
                ])
        
        # Errors and warnings
        if result.errors:
            report_lines.extend([
                "## Errors",
                *[f"- {error}" for error in result.errors],
                ""
            ])
        
        if result.warnings:
            report_lines.extend([
                "## Warnings", 
                *[f"- {warning}" for warning in result.warnings],
                ""
            ])
        
        return "\n".join(report_lines)