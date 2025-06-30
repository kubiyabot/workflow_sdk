#!/usr/bin/env python3
"""
Quick script to create a demo ANTHROPIC_API_KEY secret for testing.
"""

import os
import sys
import requests
import json

def create_demo_secret():
    """Create a demo secret for testing purposes."""
    
    print("🔧 Creating demo ANTHROPIC_API_KEY secret for testing...")
    
    # Get API key from environment 
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY not found in environment")
        return False
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Create demo secret
    payload = {
        "name": "ANTHROPIC_API_KEY",
        "description": "Demo Anthropic API key for incident response workflow testing",
        "value": "sk-demo-anthropic-key-for-testing-12345"
    }
    
    try:
        print("📡 Sending request to create secret...")
        response = requests.post(
            "https://api.kubiya.ai/api/v2/secrets",
            headers=headers,
            json=payload,
            timeout=15
        )
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📄 Response body: {response.text}")
        
        if response.status_code in [200, 201]:
            print("✅ Demo secret created successfully!")
            return True
        elif response.status_code == 409:
            print("ℹ️ Secret already exists - that's fine!")
            return True
        else:
            print(f"❌ Failed to create secret: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating secret: {str(e)}")
        return False

def test_secret_retrieval():
    """Test retrieving the created secret."""
    
    print("\n🔍 Testing secret retrieval...")
    
    api_key = os.getenv('KUBIYA_API_KEY')
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            "https://api.kubiya.ai/api/v1/secret/get_secret_value/ANTHROPIC_API_KEY",
            headers=headers,
            timeout=15
        )
        
        print(f"📊 Retrieval status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Secret retrieval successful!")
            data = response.json()
            if 'value' in data:
                value_preview = data['value'][:20] + "..." if len(data['value']) > 20 else data['value']
                print(f"📋 Secret value preview: {value_preview}")
            return True
        else:
            print(f"❌ Secret retrieval failed: HTTP {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error retrieving secret: {str(e)}")
        return False

def main():
    """Main function."""
    print("🚀 Demo Secret Creation for Incident Response Workflow")
    print("=" * 60)
    
    # Create the secret
    if create_demo_secret():
        # Test retrieval
        if test_secret_retrieval():
            print("\n🎉 SUCCESS: Demo secret is ready for workflow testing!")
            print("💡 You can now run: python test_execution.py")
            return 0
        else:
            print("\n⚠️ Secret created but retrieval test failed")
            return 1
    else:
        print("\n❌ Failed to create demo secret")
        return 1

if __name__ == "__main__":
    sys.exit(main())