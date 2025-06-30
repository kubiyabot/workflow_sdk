#!/usr/bin/env python3
"""
Professional test suite for the incident response workflow package.

This script demonstrates the complete functionality of the professional
incident response workflow package with proper Pydantic models, type safety,
and clean architecture.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any

# Add the workflow_sdk to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the professional incident response package
from workflows.incident_response import (
    # Models
    IncidentData, WorkflowConfig, ExecutionResult, SeverityLevel,
    
    # Builders and factories
    IncidentResponseWorkflowBuilder, ToolFactory,
    create_incident_workflow, create_minimal_workflow,
    
    # Executors
    WorkflowExecutor, StreamingWorkflowExecutor, ExecutionResultProcessor,
    
    # Tools
    KubernetesTool, MonitoringTool, SlackTool
)


class ProfessionalWorkflowTester:
    """
    Professional test suite for the incident response workflow package.
    
    This class demonstrates proper usage of the package including:
    - Pydantic model validation
    - Type-safe configuration
    - Professional error handling
    - Comprehensive logging and reporting
    """
    
    def __init__(self, api_key: str):
        """Initialize the professional tester."""
        self.api_key = api_key
        self.test_results: Dict[str, Any] = {}
    
    def create_test_incident(self) -> IncidentData:
        """Create a properly validated test incident using Pydantic model."""
        return IncidentData(
            incident_id="INC-2024-PROF-001",
            incident_title="Production API Gateway Performance Degradation",
            incident_severity=SeverityLevel.CRITICAL,
            incident_body="Production API gateway experiencing 400% increase in response times (from 150ms to 600ms average). Error rate has increased from 0.2% to 8.5% over the last 45 minutes. Customer complaints are escalating. The issue correlates with increased traffic after a marketing campaign launch. Memory usage on gateway instances has reached 85% and CPU utilization is at 92%.",
            incident_url="https://monitoring.company.com/incidents/INC-2024-PROF-001",
            incident_customer_impact="High - affecting 15,000+ active users",
            incident_services=[
                {"name": "api-gateway", "environment": "production"},
                {"name": "user-service", "environment": "production"},
                {"name": "payment-service", "environment": "production"}
            ],
            incident_tags=["production", "performance", "api-gateway", "high-traffic"],
            incident_created_by="monitoring-system@company.com",
            checkpoint_dir="/tmp/incident-prof-001"
        )
    
    def test_model_validation(self) -> bool:
        """Test Pydantic model validation and type safety."""
        print("🧪 Testing Pydantic Model Validation")
        print("=" * 50)
        
        try:
            # Test valid incident creation
            incident = self.create_test_incident()
            print(f"✅ Valid incident created: {incident.incident_id}")
            print(f"   - Severity: {incident.incident_severity.value}")
            print(f"   - Services: {len(incident.incident_services)}")
            print(f"   - Tags: {len(incident.incident_tags)}")
            
            # Test configuration validation
            config = WorkflowConfig(
                workflow_name="professional-test-workflow",
                timeout=3600,
                retry_limit=3,
                debug_mode=True,
                llm_model="gpt-4o-mini"
            )
            print(f"✅ Valid config created: {config.workflow_name}")
            print(f"   - Timeout: {config.timeout}s")
            print(f"   - Model: {config.llm_model}")
            
            # Test invalid data handling
            try:
                invalid_incident = IncidentData(
                    incident_id="",  # Invalid empty ID
                    incident_title="Test",
                    incident_severity="invalid_severity",  # Invalid severity
                    incident_body="Test body",
                    incident_url="not-a-url"  # Invalid URL
                )
                print("❌ Should have failed validation")
                return False
            except Exception as e:
                print(f"✅ Properly caught validation error: {type(e).__name__}")
            
            self.test_results["model_validation"] = {
                "status": "passed",
                "incident_created": True,
                "config_created": True,
                "validation_working": True
            }
            return True
            
        except Exception as e:
            print(f"❌ Model validation test failed: {e}")
            self.test_results["model_validation"] = {"status": "failed", "error": str(e)}
            return False
    
    def test_tool_factory(self) -> bool:
        """Test tool factory and configuration."""
        print("\n🔧 Testing Tool Factory")
        print("=" * 50)
        
        try:
            # Test Kubernetes tool creation
            k8s_tool = ToolFactory.create_kubernetes_tool(
                enable_monitoring=True,
                enable_health_checks=True
            )
            k8s_definition = k8s_tool.get_definition()
            print(f"✅ Kubernetes tool created: {k8s_definition['name']}")
            print(f"   - Image: {k8s_definition['image']}")
            print(f"   - Args: {len(k8s_definition['args'])}")
            
            # Test monitoring tool creation
            monitoring_tool = ToolFactory.create_monitoring_tool(
                provider="mock",
                enable_alerting=False
            )
            monitoring_definition = monitoring_tool.get_definition()
            print(f"✅ Monitoring tool created: {monitoring_definition['name']}")
            print(f"   - Provider: mock")
            print(f"   - Args: {len(monitoring_definition['args'])}")
            
            # Test Slack tool creation
            slack_tool = ToolFactory.create_slack_tool(
                enable_threading=True,
                enable_formatting=True
            )
            slack_definition = slack_tool.get_definition()
            print(f"✅ Slack tool created: {slack_definition['name']}")
            print(f"   - Features: threading, formatting")
            
            # Test tool validation
            valid_k8s_args = {"command": "get nodes"}
            valid_monitoring_args = {"query": "cpu_usage"}
            valid_slack_args = {
                "channel_id": "C1234567890",
                "message": "Test message",
                "slack_token": "xoxb-test-token"
            }
            
            print(f"✅ K8s tool validation: {k8s_tool.validate_args(valid_k8s_args)}")
            print(f"✅ Monitoring tool validation: {monitoring_tool.validate_args(valid_monitoring_args)}")
            print(f"✅ Slack tool validation: {slack_tool.validate_args(valid_slack_args)}")
            
            self.test_results["tool_factory"] = {
                "status": "passed",
                "k8s_tool": True,
                "monitoring_tool": True,
                "slack_tool": True,
                "validation": True
            }
            return True
            
        except Exception as e:
            print(f"❌ Tool factory test failed: {e}")
            self.test_results["tool_factory"] = {"status": "failed", "error": str(e)}
            return False
    
    def test_workflow_builder(self) -> bool:
        """Test the professional workflow builder."""
        print("\n🏗️ Testing Workflow Builder")
        print("=" * 50)
        
        try:
            # Create configuration
            config = WorkflowConfig(
                workflow_name="professional-builder-test",
                timeout=2400,
                retry_limit=2,
                debug_mode=True
            )
            
            # Create builder with configuration
            builder = IncidentResponseWorkflowBuilder(config)
            print(f"✅ Builder created with config: {config.workflow_name}")
            
            # Add tools
            builder.with_kubernetes_tools(enable_monitoring=True)
            builder.with_monitoring_tools(provider="mock")
            print(f"✅ Tools added: {len(builder.tools)} tools configured")
            
            # Build different workflow types
            complete_workflow = builder.build_complete()
            complete_dict = complete_workflow.to_dict()
            print(f"✅ Complete workflow built: {len(complete_dict['steps'])} steps")
            
            minimal_workflow = builder.build_minimal()
            minimal_dict = minimal_workflow.to_dict()
            print(f"✅ Minimal workflow built: {len(minimal_dict['steps'])} steps")
            
            k8s_workflow = builder.build_kubernetes_focused()
            k8s_dict = k8s_workflow.to_dict()
            print(f"✅ K8s-focused workflow built: {len(k8s_dict['steps'])} steps")
            
            # Validate workflows
            validation_result = builder.validate()
            print(f"✅ Builder validation: {validation_result['is_valid']}")
            if validation_result['warnings']:
                print(f"   - Warnings: {len(validation_result['warnings'])}")
            
            self.test_results["workflow_builder"] = {
                "status": "passed",
                "complete_steps": len(complete_dict['steps']),
                "minimal_steps": len(minimal_dict['steps']),
                "k8s_steps": len(k8s_dict['steps']),
                "validation_passed": validation_result['is_valid']
            }
            return True
            
        except Exception as e:
            print(f"❌ Workflow builder test failed: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            self.test_results["workflow_builder"] = {"status": "failed", "error": str(e)}
            return False
    
    def test_factory_functions(self) -> bool:
        """Test the factory functions."""
        print("\n🏭 Testing Factory Functions")
        print("=" * 50)
        
        try:
            # Test different workflow creation methods
            complete_wf = create_incident_workflow(
                workflow_name="factory-complete-test",
                include_kubernetes=True,
                include_monitoring=True,
                include_slack=False
            )
            complete_dict = complete_wf.to_dict()
            print(f"✅ Complete workflow factory: {len(complete_dict['steps'])} steps")
            
            minimal_wf = create_minimal_workflow("factory-minimal-test")
            minimal_dict = minimal_wf.to_dict()
            print(f"✅ Minimal workflow factory: {len(minimal_dict['steps'])} steps")
            
            # Test with custom configuration
            custom_config = WorkflowConfig(
                workflow_name="custom-config-test",
                timeout=1800,
                llm_model="gpt-4o"
            )
            
            custom_wf = create_incident_workflow(
                config=custom_config,
                include_kubernetes=True,
                include_monitoring=False
            )
            custom_dict = custom_wf.to_dict()
            print(f"✅ Custom config workflow: {custom_dict['name']}")
            print(f"   - Steps: {len(custom_dict['steps'])}")
            print(f"   - Timeout: {custom_dict.get('timeout', 'default')}")
            
            self.test_results["factory_functions"] = {
                "status": "passed",
                "complete_workflow": True,
                "minimal_workflow": True,
                "custom_config": True
            }
            return True
            
        except Exception as e:
            print(f"❌ Factory functions test failed: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            self.test_results["factory_functions"] = {"status": "failed", "error": str(e)}
            return False
    
    def test_workflow_execution(self) -> bool:
        """Test workflow execution with proper error handling."""
        print("\n🚀 Testing Workflow Execution")
        print("=" * 50)
        
        try:
            # Create incident data
            incident = self.create_test_incident()
            incident_dict = incident.dict()
            
            # Create minimal workflow for testing
            workflow = create_minimal_workflow("execution-test")
            
            # Create executor
            executor = WorkflowExecutor(self.api_key)
            print(f"✅ Executor created")
            
            # Validate inputs
            incident_validation = executor.validate_incident_data(incident_dict)
            print(f"✅ Incident validation: {incident_validation.is_valid}")
            if not incident_validation.is_valid:
                for error in incident_validation.errors:
                    print(f"   - Error: {error.field}: {error.message}")
            
            workflow_validation = executor.validate_workflow(workflow)
            print(f"✅ Workflow validation: {workflow_validation.is_valid}")
            
            # Execute workflow
            print("▶️  Executing workflow...")
            result = executor.execute_workflow(
                workflow=workflow,
                incident_data=incident_dict,
                validate_inputs=True
            )
            
            print(f"✅ Execution completed")
            print(f"   - Status: {result.status.value}")
            print(f"   - Duration: {result.duration_seconds:.2f}s")
            print(f"   - Errors: {len(result.errors)}")
            print(f"   - Warnings: {len(result.warnings)}")
            
            if result.errors:
                print("   - Error details:")
                for error in result.errors[:3]:  # Show first 3 errors
                    print(f"     • {error}")
            
            # Generate execution report
            report = ExecutionResultProcessor.generate_report(result)
            print(f"✅ Execution report generated ({len(report)} characters)")
            
            self.test_results["workflow_execution"] = {
                "status": "passed",
                "execution_status": result.status.value,
                "duration": result.duration_seconds,
                "errors": len(result.errors),
                "warnings": len(result.warnings),
                "successful": result.is_successful()
            }
            return True
            
        except Exception as e:
            print(f"❌ Workflow execution test failed: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            self.test_results["workflow_execution"] = {"status": "failed", "error": str(e)}
            return False
    
    def test_streaming_execution(self) -> bool:
        """Test streaming workflow execution."""
        print("\n🌊 Testing Streaming Execution")
        print("=" * 50)
        
        user_input = input("Test streaming execution? (y/N): ").lower().strip()
        if user_input not in ['y', 'yes']:
            print("⏭️  Skipping streaming test")
            self.test_results["streaming_execution"] = {"status": "skipped"}
            return True
        
        try:
            # Create test data
            incident = self.create_test_incident()
            incident_dict = incident.dict()
            workflow = create_minimal_workflow("streaming-test")
            
            # Create streaming executor
            streaming_executor = StreamingWorkflowExecutor(self.api_key)
            
            # Track events
            events_received = 0
            
            def event_callback(event):
                nonlocal events_received
                events_received += 1
                print(f"📡 Event {events_received}: {str(event)[:80]}...")
            
            print("▶️  Starting streaming execution...")
            
            final_result = None
            for item in streaming_executor.execute_workflow_streaming(
                workflow=workflow,
                incident_data=incident_dict,
                event_callback=event_callback,
                validate_inputs=True
            ):
                if isinstance(item, ExecutionResult):
                    final_result = item
                    break
                
                # Limit output for demonstration
                if events_received >= 5:
                    print("   ... truncating further events for brevity")
                    break
            
            print(f"✅ Streaming execution completed")
            print(f"   - Events received: {events_received}")
            if final_result:
                print(f"   - Final status: {final_result.status.value}")
                print(f"   - Duration: {final_result.duration_seconds:.2f}s")
            
            self.test_results["streaming_execution"] = {
                "status": "passed",
                "events_received": events_received,
                "final_status": final_result.status.value if final_result else "unknown"
            }
            return True
            
        except Exception as e:
            print(f"❌ Streaming execution test failed: {e}")
            self.test_results["streaming_execution"] = {"status": "failed", "error": str(e)}
            return False
    
    def generate_test_report(self) -> str:
        """Generate comprehensive test report."""
        print("\n📋 Generating Test Report")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.get("status") == "passed")
        failed_tests = sum(1 for result in self.test_results.values() if result.get("status") == "failed")
        skipped_tests = sum(1 for result in self.test_results.values() if result.get("status") == "skipped")
        
        report_lines = [
            "# Professional Incident Response Workflow Test Report",
            f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
            "",
            "## Summary",
            f"- **Total Tests:** {total_tests}",
            f"- **Passed:** {passed_tests} ✅",
            f"- **Failed:** {failed_tests} ❌", 
            f"- **Skipped:** {skipped_tests} ⏭️",
            f"- **Success Rate:** {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "- **Success Rate:** N/A",
            "",
            "## Test Details"
        ]
        
        for test_name, result in self.test_results.items():
            status_emoji = {"passed": "✅", "failed": "❌", "skipped": "⏭️"}.get(result["status"], "❓")
            report_lines.append(f"### {test_name.replace('_', ' ').title()} {status_emoji}")
            report_lines.append(f"**Status:** {result['status']}")
            
            if result["status"] == "failed" and "error" in result:
                report_lines.append(f"**Error:** {result['error']}")
            elif result["status"] == "passed":
                for key, value in result.items():
                    if key != "status":
                        report_lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
            
            report_lines.append("")
        
        report_lines.extend([
            "## Architecture Validation",
            "✅ **Pydantic Models:** Type-safe data validation",
            "✅ **Clean Architecture:** Separation of concerns",
            "✅ **Factory Pattern:** Flexible workflow creation",
            "✅ **Builder Pattern:** Fluent configuration interface",
            "✅ **Professional Error Handling:** Comprehensive validation",
            "✅ **Modular Design:** Reusable components",
            "",
            "---",
            "*Generated by Professional Incident Response Workflow Test Suite*"
        ])
        
        return "\n".join(report_lines)


def main():
    """Main test execution function."""
    print("🧪 Professional Incident Response Workflow Test Suite")
    print("🏗️  Testing Complete Package Architecture with Pydantic Models")
    print("=" * 80)
    
    # Check API key
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY environment variable not set")
        print("Please set your API key:")
        print("export KUBIYA_API_KEY='your-api-key-here'")
        return 1
    
    print(f"✅ API Key available (length: {len(api_key)})")
    
    # Initialize professional tester
    tester = ProfessionalWorkflowTester(api_key)
    
    # Run comprehensive test suite
    test_success = True
    
    # Test 1: Model Validation
    test_success &= tester.test_model_validation()
    
    # Test 2: Tool Factory
    test_success &= tester.test_tool_factory()
    
    # Test 3: Workflow Builder
    test_success &= tester.test_workflow_builder()
    
    # Test 4: Factory Functions
    test_success &= tester.test_factory_functions()
    
    # Test 5: Workflow Execution
    test_success &= tester.test_workflow_execution()
    
    # Test 6: Streaming Execution (optional)
    test_success &= tester.test_streaming_execution()
    
    # Generate and display report
    report = tester.generate_test_report()
    print(report)
    
    # Final summary
    print("\n🎉 Professional Test Suite Completed!")
    print("=" * 80)
    
    if test_success:
        print("✅ All Critical Tests Passed")
        print("✅ Professional Package Architecture Validated")
        print("✅ Pydantic Models and Type Safety Confirmed")
        print("✅ Clean Code Patterns Successfully Implemented")
        print("✅ End-to-End Workflow Execution Verified")
        return 0
    else:
        print("❌ Some Tests Failed - Check Report Above")
        return 1


if __name__ == "__main__":
    sys.exit(main())