#!/usr/bin/env python3
"""
Production-grade incident response workflow with configurable Claude Code tools.

This module provides the main entry point for creating and executing incident response workflows
with flexible tool configurations, comprehensive monitoring, and production-ready features.

Usage:
    python main.py --config config.yaml --execute
    python main.py --tools kubectl,datadog-cli,github-cli --test
    python main.py --minimal --demo
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add the workflow_sdk to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from kubiya_workflow_sdk.client import KubiyaClient
from models.config import WorkflowConfig, ClaudeCodeConfig
from models.incident import IncidentEvent
from components.builders import WorkflowBuilder, create_production_workflow, create_test_workflow, create_custom_tool_workflow
from components.parsers import IncidentParser
from tools.registry import get_default_tools, get_minimal_tools, get_full_toolset
from config.examples import create_example_config, create_minimal_config, create_full_config


class IncidentResponseOrchestrator:
    """Main orchestrator for incident response workflows."""
    
    def __init__(self, config: WorkflowConfig, api_key: Optional[str] = None):
        self.config = config
        self.api_key = api_key or os.getenv('KUBIYA_API_KEY')
        self.builder = WorkflowBuilder(config)
        
        if self.api_key:
            self.client = KubiyaClient(
                api_key=self.api_key,
                timeout=config.timeout,
                max_retries=3
            )
        else:
            self.client = None
    
    def create_workflow(self, workflow_type: str = "production", tool_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a workflow based on type and configuration."""
        
        if workflow_type == "production":
            workflow = self.builder.build_complete_workflow()
        elif workflow_type == "minimal":
            workflow = self.builder.build_minimal_workflow()
        elif workflow_type == "test":
            workflow = create_test_workflow(self.config)
        elif workflow_type == "custom" and tool_names:
            workflow = create_custom_tool_workflow(tool_names, self.config)
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
        
        return workflow.to_dict()
    
    def execute_workflow(self, 
                        incident_event: IncidentEvent,
                        workflow_type: str = "production",
                        tool_names: Optional[List[str]] = None,
                        stream: bool = True) -> Any:
        """Execute an incident response workflow."""
        
        if not self.client:
            raise ValueError("API key required for workflow execution")
        
        # Create workflow
        workflow_dict = self.create_workflow(workflow_type, tool_names)
        
        # Prepare parameters
        params = {
            "event": incident_event.json()
        }
        
        print(f"🚀 Executing {workflow_type} incident response workflow")
        print(f"📋 Incident: {incident_event.id} - {incident_event.title}")
        print(f"🚨 Severity: {incident_event.severity}")
        
        if tool_names:
            print(f"🛠️ Custom tools: {', '.join(tool_names)}")
        
        # Execute workflow
        if stream:
            return self.client.execute_workflow(
                workflow_definition=workflow_dict,
                parameters=params,
                stream=True
            )
        else:
            return self.client.execute_workflow(
                workflow_definition=workflow_dict,
                parameters=params,
                stream=False
            )
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate the current configuration."""
        
        validation_results = {
            "config_valid": True,
            "errors": [],
            "warnings": [],
            "tool_validation": {}
        }
        
        # Validate basic config
        if not self.config.name:
            validation_results["errors"].append("Workflow name is required")
            validation_results["config_valid"] = False
        
        if not self.config.runner:
            validation_results["errors"].append("Workflow runner is required")
            validation_results["config_valid"] = False
        
        # Validate Claude Code configuration
        if not self.config.claude_code.tools:
            validation_results["warnings"].append("No tools configured for Claude Code investigation")
        
        # Validate each tool
        for tool in self.config.claude_code.tools:
            tool_result = {
                "valid": True,
                "issues": []
            }
            
            if not tool.name:
                tool_result["issues"].append("Tool name is required")
                tool_result["valid"] = False
            
            if not tool.install_commands:
                tool_result["issues"].append("No installation commands provided")
                tool_result["valid"] = False
            
            validation_results["tool_validation"][tool.name or "unnamed"] = tool_result
        
        return validation_results
    
    def generate_config_template(self, config_type: str = "default") -> WorkflowConfig:
        """Generate a configuration template."""
        
        if config_type == "minimal":
            return create_minimal_config()
        elif config_type == "full":
            return create_full_config()
        else:
            return create_example_config()


def parse_arguments():
    """Parse command line arguments."""
    
    parser = argparse.ArgumentParser(
        description="Production-grade incident response workflow with configurable Claude Code tools"
    )
    
    # Configuration options
    parser.add_argument("--config", "-c", type=str, help="Path to configuration file")
    parser.add_argument("--config-type", choices=["default", "minimal", "full"], 
                       default="default", help="Type of configuration to use")
    
    # Workflow options
    parser.add_argument("--workflow-type", "-w", choices=["production", "minimal", "test", "custom"],
                       default="production", help="Type of workflow to create")
    parser.add_argument("--tools", "-t", type=str, help="Comma-separated list of tools to include")
    
    # Execution options
    parser.add_argument("--execute", "-e", action="store_true", help="Execute the workflow")
    parser.add_argument("--test-event", action="store_true", help="Use test incident event")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming output")
    
    # Output options
    parser.add_argument("--output", "-o", type=str, help="Output file for workflow definition")
    parser.add_argument("--validate", action="store_true", help="Validate configuration only")
    parser.add_argument("--generate-config", type=str, help="Generate configuration template")
    
    return parser.parse_args()


def load_configuration(args) -> WorkflowConfig:
    """Load configuration from file or create default."""
    
    if args.config and os.path.exists(args.config):
        # Load from file
        with open(args.config, 'r') as f:
            if args.config.endswith('.json'):
                config_data = json.load(f)
            else:
                import yaml
                config_data = yaml.safe_load(f)
        
        return WorkflowConfig(**config_data)
    else:
        # Create default configuration
        if args.config_type == "minimal":
            config = create_minimal_config()
        elif args.config_type == "full":
            config = create_full_config()
        else:
            config = create_example_config()
        
        # Apply demo mode if requested
        if args.demo:
            config.demo_mode = True
        
        return config


def main():
    """Main entry point."""
    
    args = parse_arguments()
    
    # Generate configuration template if requested
    if args.generate_config:
        orchestrator = IncidentResponseOrchestrator(WorkflowConfig())
        template_config = orchestrator.generate_config_template(args.generate_config)
        
        output_file = f"config_template_{args.generate_config}.json"
        with open(output_file, 'w') as f:
            f.write(template_config.json(indent=2))
        
        print(f"✅ Configuration template saved to {output_file}")
        return 0
    
    # Load configuration
    try:
        config = load_configuration(args)
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return 1
    
    # Create orchestrator
    orchestrator = IncidentResponseOrchestrator(config)
    
    # Validate configuration if requested
    if args.validate:
        validation = orchestrator.validate_configuration()
        
        if validation["config_valid"]:
            print("✅ Configuration validation passed")
        else:
            print("❌ Configuration validation failed")
            for error in validation["errors"]:
                print(f"  ❌ {error}")
        
        for warning in validation["warnings"]:
            print(f"  ⚠️ {warning}")
        
        return 0 if validation["config_valid"] else 1
    
    # Parse tool names if provided
    tool_names = None
    if args.tools:
        tool_names = [tool.strip() for tool in args.tools.split(',')]
    
    # Create workflow
    try:
        workflow_dict = orchestrator.create_workflow(args.workflow_type, tool_names)
        
        print(f"✅ Created {args.workflow_type} workflow: {workflow_dict['name']}")
        print(f"📋 Steps: {len(workflow_dict['steps'])}")
        print(f"🏃 Runner: {workflow_dict.get('runner', 'default')}")
        
        if tool_names:
            print(f"🛠️ Custom tools: {', '.join(tool_names)}")
        
    except Exception as e:
        print(f"❌ Failed to create workflow: {e}")
        return 1
    
    # Save workflow to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(workflow_dict, f, indent=2)
        print(f"💾 Workflow saved to {args.output}")
    
    # Execute workflow if requested
    if args.execute:
        if not orchestrator.api_key:
            print("❌ KUBIYA_API_KEY required for execution")
            return 1
        
        # Create test incident if requested
        if args.test_event:
            incident_event = IncidentParser.create_test_event()
        else:
            print("❌ Real incident event required (use --test-event for testing)")
            return 1
        
        try:
            print("\n🚀 Starting workflow execution...")
            
            events = orchestrator.execute_workflow(
                incident_event=incident_event,
                workflow_type=args.workflow_type,
                tool_names=tool_names,
                stream=not args.no_stream
            )
            
            # Process events
            event_count = 0
            for event in events:
                event_count += 1
                
                if isinstance(event, str) and event.strip():
                    try:
                        parsed_event = json.loads(event)
                        event_type = parsed_event.get('type', 'unknown')
                        step_name = parsed_event.get('step_name', 'unknown')
                        
                        if event_type == 'heartbeat':
                            print(f"💓 Heartbeat #{event_count}")
                        elif 'step.completed' in event_type:
                            print(f"✅ Step completed: {step_name}")
                        elif 'step.failed' in event_type:
                            print(f"❌ Step failed: {step_name}")
                        else:
                            print(f"📡 Event #{event_count}: {event_type}")
                            
                    except json.JSONDecodeError:
                        print(f"📝 Raw event #{event_count}: {event[:100]}...")
                
                # Safety limit
                if event_count >= 200:
                    print("⚠️ Event limit reached - stopping")
                    break
            
            print(f"\n✅ Workflow execution completed ({event_count} events)")
            
        except Exception as e:
            print(f"❌ Workflow execution failed: {e}")
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())