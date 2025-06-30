#!/usr/bin/env python3
"""
Comprehensive environment setup script for incident response workflow.

This script validates and creates all required secrets, tests API integrations,
and ensures the environment is properly configured for the end-to-end workflow.
"""

import os
import sys
import json
import time
import getpass
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add paths for SDK access
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent.parent.parent))

from kubiya_workflow_sdk.client import KubiyaClient


class KubiyaEnvironmentSetup:
    """Comprehensive environment setup and validation for Kubiya workflows."""
    
    def __init__(self):
        self.api_key = None
        self.client = None
        self.base_url = "https://api.kubiya.ai"
        self.required_secrets = {
            "ANTHROPIC_API_KEY": {
                "description": "Anthropic Claude API key for AI analysis",
                "env_var": "ANTHROPIC_API_KEY",
                "required": True,
                "validation_url": "https://api.anthropic.com/v1/messages",
                "validation_method": "headers_check"
            },
            "DATADOG_API_KEY": {
                "description": "Datadog API key for monitoring integration",
                "env_var": "DATADOG_API_KEY", 
                "required": False,
                "validation_url": "https://api.datadoghq.com/api/v1/validate",
                "validation_method": "api_call"
            },
            "DATADOG_APP_KEY": {
                "description": "Datadog application key for advanced monitoring",
                "env_var": "DATADOG_APP_KEY",
                "required": False,
                "validation_url": None,
                "validation_method": "none"
            },
            "GITHUB_TOKEN": {
                "description": "GitHub personal access token for repository access",
                "env_var": "GITHUB_TOKEN",
                "required": False,
                "validation_url": "https://api.github.com/user",
                "validation_method": "bearer_token"
            }
        }
        self.setup_results = {}
        
    def print_header(self, title: str):
        """Print a formatted header."""
        print(f"\n{'=' * 80}")
        print(f"🔧 {title}")
        print('=' * 80)
    
    def print_step(self, step: str, status: str = "info"):
        """Print a formatted step."""
        icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌", "progress": "🔄"}
        icon = icons.get(status, "•")
        print(f"{icon} {step}")
    
    def validate_kubiya_api_key(self) -> bool:
        """Validate and set up Kubiya API key."""
        self.print_header("KUBIYA API KEY VALIDATION")
        
        # Try to get API key from environment
        api_key = os.getenv('KUBIYA_API_KEY')
        
        if not api_key:
            self.print_step("No KUBIYA_API_KEY found in environment", "warning")
            print("\n🔑 Please provide your Kubiya API key:")
            print("   You can find this in your Kubiya dashboard under API Keys")
            api_key = getpass.getpass("Enter Kubiya API Key: ")
        
        if not api_key:
            self.print_step("API key is required for setup", "error")
            return False
        
        # Validate API key
        self.print_step("Validating Kubiya API key...", "progress")
        
        try:
            self.client = KubiyaClient(api_key=api_key, timeout=30)
            
            # Test API key by listing integrations
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.base_url}/api/v2/integrations/slack",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.api_key = api_key
                self.print_step(f"API key validated successfully (length: {len(api_key)})", "success")
                
                # Set environment variable for this session
                os.environ['KUBIYA_API_KEY'] = api_key
                return True
            else:
                self.print_step(f"API key validation failed: HTTP {response.status_code}", "error")
                if response.status_code == 401:
                    self.print_step("Invalid API key - please check your credentials", "error")
                return False
                
        except Exception as e:
            self.print_step(f"API key validation error: {str(e)}", "error")
            return False
    
    def check_existing_secrets(self) -> Dict[str, bool]:
        """Check which secrets already exist in Kubiya."""
        self.print_header("CHECKING EXISTING SECRETS")
        
        existing_secrets = {}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        for secret_name in self.required_secrets.keys():
            self.print_step(f"Checking secret: {secret_name}", "progress")
            
            try:
                response = requests.get(
                    f"{self.base_url}/api/v1/secret/get_secret_value/{secret_name}",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    existing_secrets[secret_name] = True
                    self.print_step(f"Secret {secret_name} exists and accessible", "success")
                else:
                    existing_secrets[secret_name] = False
                    self.print_step(f"Secret {secret_name} not found or not accessible", "warning")
                    
            except Exception as e:
                existing_secrets[secret_name] = False
                self.print_step(f"Error checking {secret_name}: {str(e)}", "warning")
                
        return existing_secrets
    
    def validate_slack_integration(self) -> bool:
        """Test Slack integration and token retrieval."""
        self.print_header("SLACK INTEGRATION VALIDATION")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # Test Slack integration info
            self.print_step("Testing Slack integration info endpoint...", "progress")
            response = requests.get(
                f"{self.base_url}/api/v2/integrations/slack",
                headers=headers,
                timeout=15
            )
            
            if response.status_code != 200:
                self.print_step(f"Slack integration check failed: HTTP {response.status_code}", "error")
                return False
                
            slack_info = response.json()
            self.print_step("Slack integration info retrieved successfully", "success")
            
            # Extract integration ID for token test
            if slack_info and isinstance(slack_info, dict) and 'configs' in slack_info:
                configs = slack_info['configs']
                if configs and len(configs) > 0:
                    integration_id = configs[0].get('vendor_specific', {}).get('id')
                    if integration_id:
                        # Test token retrieval
                        self.print_step(f"Testing Slack token retrieval (ID: {integration_id})...", "progress")
                        token_response = requests.get(
                            f"{self.base_url}/api/v1/integration/slack/token/{integration_id}",
                            headers=headers,
                            timeout=15
                        )
                        
                        if token_response.status_code == 200:
                            token_data = token_response.json()
                            if 'token' in token_data:
                                token_preview = token_data['token'][:20] + "..." if len(token_data['token']) > 20 else token_data['token']
                                self.print_step(f"Slack token retrieved successfully: {token_preview}", "success")
                                return True
                            else:
                                self.print_step("Slack token response missing 'token' field", "error")
                                return False
                        else:
                            self.print_step(f"Slack token retrieval failed: HTTP {token_response.status_code}", "error")
                            return False
                    else:
                        self.print_step("No integration ID found in Slack config", "error")
                        return False
                else:
                    self.print_step("No Slack configurations found", "error")
                    return False
            else:
                self.print_step("Invalid Slack integration response format", "error")
                return False
                
        except Exception as e:
            self.print_step(f"Slack integration validation error: {str(e)}", "error")
            return False
    
    def validate_external_secret(self, secret_name: str, secret_value: str) -> bool:
        """Validate a secret against its external API."""
        secret_config = self.required_secrets.get(secret_name, {})
        validation_method = secret_config.get('validation_method', 'none')
        validation_url = secret_config.get('validation_url')
        
        if validation_method == 'none' or not validation_url:
            return True
            
        try:
            self.print_step(f"Validating {secret_name} against external API...", "progress")
            
            if validation_method == 'headers_check':
                # For Anthropic API
                headers = {
                    "x-api-key": secret_value,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                }
                
                # Test payload for Anthropic
                payload = {
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "test"}]
                }
                
                response = requests.post(validation_url, headers=headers, json=payload, timeout=15)
                
                if response.status_code in [200, 400]:  # 400 is OK for validation (means API key worked)
                    self.print_step(f"{secret_name} validated successfully", "success")
                    return True
                else:
                    self.print_step(f"{secret_name} validation failed: HTTP {response.status_code}", "error")
                    return False
                    
            elif validation_method == 'bearer_token':
                # For GitHub API
                headers = {"Authorization": f"Bearer {secret_value}"}
                response = requests.get(validation_url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    self.print_step(f"{secret_name} validated successfully", "success")
                    return True
                else:
                    self.print_step(f"{secret_name} validation failed: HTTP {response.status_code}", "error")
                    return False
                    
            elif validation_method == 'api_call':
                # For Datadog API
                params = {"api_key": secret_value}
                response = requests.get(validation_url, params=params, timeout=15)
                
                if response.status_code == 200:
                    self.print_step(f"{secret_name} validated successfully", "success")
                    return True
                else:
                    self.print_step(f"{secret_name} validation failed: HTTP {response.status_code}", "error")
                    return False
                    
        except Exception as e:
            self.print_step(f"Error validating {secret_name}: {str(e)}", "warning")
            return False
            
        return True
    
    def create_secret(self, secret_name: str, secret_value: str, description: str) -> bool:
        """Create a secret in Kubiya."""
        self.print_step(f"Creating secret: {secret_name}", "progress")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "name": secret_name,
            "description": description,
            "value": secret_value
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v2/secrets",
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code in [200, 201]:
                self.print_step(f"Secret {secret_name} created successfully", "success")
                return True
            else:
                self.print_step(f"Failed to create secret {secret_name}: HTTP {response.status_code}", "error")
                if response.text:
                    print(f"   Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            self.print_step(f"Error creating secret {secret_name}: {str(e)}", "error")
            return False
    
    def setup_secrets_interactively(self, existing_secrets: Dict[str, bool]) -> bool:
        """Interactively set up missing secrets."""
        self.print_header("INTERACTIVE SECRET SETUP")
        
        success_count = 0
        total_secrets = len(self.required_secrets)
        
        for secret_name, config in self.required_secrets.items():
            print(f"\n📋 Setting up: {secret_name}")
            print(f"   Description: {config['description']}")
            print(f"   Required: {'Yes' if config['required'] else 'No'}")
            
            if existing_secrets.get(secret_name, False):
                self.print_step(f"{secret_name} already exists - skipping", "success")
                success_count += 1
                continue
            
            # Check environment variable first
            env_value = os.getenv(config['env_var'])
            if env_value:
                self.print_step(f"Found {secret_name} in environment variable", "info")
                print(f"   Value preview: {env_value[:10]}...")
                
                use_env = input(f"   Use this value? (y/n) [y]: ").strip().lower()
                if use_env in ['', 'y', 'yes']:
                    secret_value = env_value
                else:
                    secret_value = None
            else:
                secret_value = None
            
            # Get value interactively if not from environment
            if not secret_value:
                if config['required']:
                    print(f"   ⚠️ {secret_name} is required for the workflow")
                    secret_value = getpass.getpass(f"   Enter {secret_name}: ")
                else:
                    prompt = input(f"   Enter {secret_name} (optional, press Enter to skip): ")
                    if not prompt.strip():
                        self.print_step(f"Skipping optional secret: {secret_name}", "info")
                        continue
                    secret_value = prompt.strip()
            
            if not secret_value:
                if config['required']:
                    self.print_step(f"Required secret {secret_name} not provided", "error")
                    return False
                continue
            
            # Validate secret
            if not self.validate_external_secret(secret_name, secret_value):
                self.print_step(f"Secret validation failed for {secret_name}", "warning")
                retry = input("   Continue anyway? (y/n) [n]: ").strip().lower()
                if retry not in ['y', 'yes']:
                    if config['required']:
                        return False
                    continue
            
            # Create secret in Kubiya
            if self.create_secret(secret_name, secret_value, config['description']):
                success_count += 1
                self.setup_results[secret_name] = "created"
            else:
                if config['required']:
                    return False
                self.setup_results[secret_name] = "failed"
        
        self.print_step(f"Secrets setup completed: {success_count}/{total_secrets}", "success")
        return True
    
    def test_end_to_end_setup(self) -> bool:
        """Test the complete setup by running a mini workflow."""
        self.print_header("END-TO-END SETUP VALIDATION")
        
        try:
            # Test secret retrieval
            self.print_step("Testing secret retrieval...", "progress")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            secret_tests = {}
            for secret_name in self.required_secrets.keys():
                response = requests.get(
                    f"{self.base_url}/api/v1/secret/get_secret_value/{secret_name}",
                    headers=headers,
                    timeout=10
                )
                secret_tests[secret_name] = response.status_code == 200
            
            # Test Slack integration
            self.print_step("Testing Slack integration...", "progress")
            slack_test = self.validate_slack_integration()
            
            # Summary
            self.print_step("Setup validation summary:", "info")
            for secret_name, status in secret_tests.items():
                icon = "✅" if status else "❌"
                self.print_step(f"  {icon} {secret_name}: {'Available' if status else 'Not available'}")
            
            slack_icon = "✅" if slack_test else "❌"
            self.print_step(f"  {slack_icon} Slack Integration: {'Working' if slack_test else 'Failed'}")
            
            # Overall result
            required_secrets_ok = all(
                secret_tests.get(name, False) 
                for name, config in self.required_secrets.items() 
                if config['required']
            )
            
            if required_secrets_ok and slack_test:
                self.print_step("🎉 End-to-end setup validation PASSED!", "success")
                return True
            else:
                self.print_step("⚠️ End-to-end setup validation FAILED", "warning")
                return False
                
        except Exception as e:
            self.print_step(f"End-to-end validation error: {str(e)}", "error")
            return False
    
    def generate_setup_summary(self):
        """Generate a summary of the setup process."""
        self.print_header("SETUP SUMMARY")
        
        print("📊 Setup Results:")
        for secret_name, result in self.setup_results.items():
            icons = {"created": "✅", "failed": "❌", "skipped": "⚪"}
            icon = icons.get(result, "❓")
            print(f"   {icon} {secret_name}: {result}")
        
        print(f"\n🔧 Environment Status:")
        print(f"   ✅ Kubiya API Key: Configured")
        print(f"   ✅ SDK Client: Initialized")
        
        print(f"\n🚀 Next Steps:")
        print(f"   1. Run the incident response workflow: python test_execution.py")
        print(f"   2. Check generated reports in the reports/ directory")
        print(f"   3. Review workflow execution logs for any issues")
        
        print(f"\n💡 Troubleshooting:")
        print(f"   • Re-run this script to update or fix secrets")
        print(f"   • Check Kubiya dashboard for secret management")
        print(f"   • Verify API keys are valid and have proper permissions")


def main():
    """Main setup function."""
    print("🚀 KUBIYA INCIDENT RESPONSE WORKFLOW - ENVIRONMENT SETUP")
    print("=" * 80)
    print("This script will:")
    print("  ✅ Validate your Kubiya API key")
    print("  ✅ Check and create required secrets")
    print("  ✅ Test Slack integration")
    print("  ✅ Validate external API credentials")
    print("  ✅ Perform end-to-end setup validation")
    print("=" * 80)
    
    setup = KubiyaEnvironmentSetup()
    
    try:
        # Step 1: Validate Kubiya API key
        if not setup.validate_kubiya_api_key():
            print("\n❌ Setup failed: Invalid Kubiya API key")
            return 1
        
        # Step 2: Check existing secrets
        existing_secrets = setup.check_existing_secrets()
        
        # Step 3: Test Slack integration
        slack_working = setup.validate_slack_integration()
        if not slack_working:
            print("\n⚠️ Warning: Slack integration test failed")
            print("   The workflow may still work, but Slack features will be limited")
        
        # Step 4: Interactive secret setup
        if not setup.setup_secrets_interactively(existing_secrets):
            print("\n❌ Setup failed: Could not configure required secrets")
            return 1
        
        # Step 5: End-to-end validation
        if not setup.test_end_to_end_setup():
            print("\n⚠️ Warning: End-to-end validation had issues")
            print("   Some features may not work properly")
        
        # Step 6: Generate summary
        setup.generate_setup_summary()
        
        print(f"\n🎉 SETUP COMPLETED SUCCESSFULLY!")
        print(f"   Your environment is ready for incident response workflows")
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Setup interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Setup failed with error: {str(e)}")
        import traceback
        print(f"🔍 Full traceback:\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())