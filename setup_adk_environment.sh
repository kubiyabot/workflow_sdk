#!/bin/bash
# Setup script for Kubiya Workflow SDK with ADK Provider

echo "=========================================="
echo "Kubiya Workflow SDK - ADK Provider Setup"
echo "=========================================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "❌ Error: Python 3.10+ is required (found $python_version)"
    echo "Please install Python 3.10 or higher"
    exit 1
fi

echo "✅ Python version: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d "venv_adk" ]; then
    echo "  Removing existing venv_adk..."
    rm -rf venv_adk
fi

python3 -m venv venv_adk
source venv_adk/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install the SDK with ADK support
echo ""
echo "Installing Kubiya Workflow SDK with ADK provider..."
pip install -e ".[adk]"

# Check if Together AI key is set
echo ""
echo "Checking environment variables..."
if [ -z "$TOGETHER_API_KEY" ]; then
    echo "⚠️  Warning: TOGETHER_API_KEY is not set"
    echo "  You'll need to set it to use the ADK provider:"
    echo "  export TOGETHER_API_KEY=your-api-key"
else
    echo "✅ TOGETHER_API_KEY is set"
fi

if [ -z "$KUBIYA_API_KEY" ]; then
    echo "ℹ️  Note: KUBIYA_API_KEY is not set"
    echo "  Examples will use a mock client for demonstration"
else
    echo "✅ KUBIYA_API_KEY is set"
fi

# Create .env.example
echo ""
echo "Creating .env.example file..."
cat > .env.example << EOF
# Required for ADK provider
TOGETHER_API_KEY=your-together-api-key

# Optional - for real Kubiya platform integration
KUBIYA_API_KEY=your-kubiya-api-key

# Optional - alternative model providers
# GOOGLE_API_KEY=your-google-api-key
# VERTEX_PROJECT_ID=your-project-id
# VERTEX_LOCATION=us-central1

# Optional - model overrides
# ADK_ORCHESTRATOR_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo
# ADK_WORKFLOW_GENERATOR_MODEL=deepseek-ai/DeepSeek-V3
# ADK_REFINEMENT_MODEL=deepseek-ai/DeepSeek-R1
EOF

echo "✅ Created .env.example"

# Test imports
echo ""
echo "Testing imports..."
python3 -c "
try:
    from kubiya_workflow_sdk import KubiyaClient
    print('✅ Kubiya SDK imported successfully')
except ImportError as e:
    print(f'❌ Failed to import Kubiya SDK: {e}')
    exit(1)

try:
    from kubiya_workflow_sdk.providers import get_provider
    print('✅ Provider system imported successfully')
except ImportError as e:
    print(f'❌ Failed to import providers: {e}')
    exit(1)

try:
    from kubiya_workflow_sdk.providers.adk import ADKConfig
    print('✅ ADK provider imported successfully')
except ImportError as e:
    print(f'❌ Failed to import ADK provider: {e}')
    exit(1)

try:
    import litellm
    print('✅ LiteLLM imported successfully')
except ImportError as e:
    print(f'❌ Failed to import LiteLLM: {e}')
    exit(1)

try:
    from google.adk.agents import LlmAgent
    print('✅ Google ADK imported successfully')
except ImportError as e:
    print(f'⚠️  Warning: Google ADK not available: {e}')
    print('  The provider will use mock components in tests')
"

# Create a simple test script
echo ""
echo "Creating test_adk_basic.py..."
cat > test_adk_basic.py << 'EOF'
#!/usr/bin/env python3
"""Basic test for ADK provider setup."""

import os
import sys

def test_basic_import():
    """Test basic imports work."""
    try:
        from kubiya_workflow_sdk import KubiyaClient
        from kubiya_workflow_sdk.providers import get_provider
        from kubiya_workflow_sdk.providers.adk import ADKConfig, ModelProvider
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_provider_creation():
    """Test provider can be created."""
    try:
        from kubiya_workflow_sdk import KubiyaClient
        from kubiya_workflow_sdk.providers import get_provider
        
        # Use mock client
        from unittest.mock import Mock
        client = Mock(spec=KubiyaClient)
        
        # Try to create provider
        provider = get_provider("adk", client=client)
        print("✅ ADK provider created successfully")
        return True
    except Exception as e:
        print(f"❌ Provider creation failed: {e}")
        return False

def test_config():
    """Test ADK configuration."""
    try:
        from kubiya_workflow_sdk.providers.adk import ADKConfig, ModelProvider
        
        # Test default config
        config = ADKConfig()
        assert config.model_provider == ModelProvider.TOGETHER
        print(f"✅ Default model provider: {config.model_provider.value}")
        
        # Test model lookup
        model = config.get_model("orchestrator")
        print(f"✅ Orchestrator model: {model}")
        
        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("\nRunning ADK Provider Tests")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_basic_import),
        ("Provider Creation", test_provider_creation),
        ("Configuration", test_config)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
    
    print(f"\n{'=' * 40}")
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n✅ All tests passed! ADK provider is ready to use.")
        print("\nNext steps:")
        print("1. Set your TOGETHER_API_KEY environment variable")
        print("2. Run the examples: python kubiya_workflow_sdk/providers/adk/example.py")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

echo "✅ Created test_adk_basic.py"

# Run the test
echo ""
echo "Running basic tests..."
python3 test_adk_basic.py

# Print final instructions
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To use the ADK provider:"
echo ""
echo "1. Activate the virtual environment:"
echo "   source venv_adk/bin/activate"
echo ""
echo "2. Set your API keys:"
echo "   export TOGETHER_API_KEY=your-together-api-key"
echo "   export KUBIYA_API_KEY=your-kubiya-api-key  # Optional"
echo ""
echo "3. Run the examples:"
echo "   python kubiya_workflow_sdk/providers/adk/example.py"
echo ""
echo "4. Or start coding:"
echo "   python"
echo "   >>> from kubiya_workflow_sdk.providers import get_provider"
echo "   >>> # ... see README for usage"
echo ""
echo "Documentation: kubiya_workflow_sdk/providers/adk/README.md"
echo "==========================================" 