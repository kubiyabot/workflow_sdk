#!/bin/bash
set -e

echo "🛠️ INCIDENT RESPONSE ENVIRONMENT SETUP"
echo "======================================"

# Set up environment variables
export HOME=/root
export PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH
export KUBECONFIG=/tmp/kubeconfig
export KUBERNETES_SERVICE_HOST=kubernetes.default.svc
export KUBERNETES_SERVICE_PORT=443

# Function to log with timestamps
log_info() {
    echo "$(date -u +%H:%M:%S) ℹ️ $1"
}

log_success() {
    echo "$(date -u +%H:%M:%S) ✅ $1"
}

log_warning() {
    echo "$(date -u +%H:%M:%S) ⚠️ $1"
}

log_error() {
    echo "$(date -u +%H:%M:%S) ❌ $1"
}

# Install system packages
log_info "Installing system packages..."
APT_UPDATE_OUTPUT=$(apt-get update -qq 2>&1)
if [ $? -eq 0 ]; then
    log_success "Package lists updated"
else
    log_warning "Package update warnings: $APT_UPDATE_OUTPUT"
fi

APT_INSTALL_OUTPUT=$(apt-get install -y curl wget jq procps python3 python3-pip 2>&1)
if [ $? -eq 0 ]; then
    log_success "System packages installed: curl, wget, jq, procps, python3, python3-pip"
else
    log_error "Package installation failed: $APT_INSTALL_OUTPUT"
    exit 1
fi

# Install Python packages
log_info "Installing Python monitoring utilities..."
PIP_INSTALL_OUTPUT=$(pip3 install --quiet psutil requests pyyaml 2>&1)
if [ $? -eq 0 ]; then
    log_success "Python packages installed: psutil, requests, pyyaml"
else
    log_warning "Python package installation issues: $PIP_INSTALL_OUTPUT"
fi

# Install kubectl
log_info "Installing kubectl..."
KUBECTL_VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt 2>&1)
log_info "Latest kubectl version: $KUBECTL_VERSION"

KUBECTL_DOWNLOAD=$(curl -LO "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/amd64/kubectl" 2>&1)
if [ $? -eq 0 ]; then
    chmod +x kubectl
    mv kubectl /usr/local/bin/
    log_success "kubectl installed successfully ($KUBECTL_VERSION)"
else
    log_warning "kubectl installation failed: $KUBECTL_DOWNLOAD"
fi

# Install Helm
log_info "Installing Helm..."
HELM_INSTALL_OUTPUT=$(curl -s https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash 2>&1)
if [ $? -eq 0 ] && command -v helm >/dev/null 2>&1; then
    HELM_VERSION=$(helm version --short 2>&1 || echo "version unknown")
    log_success "Helm installed successfully ($HELM_VERSION)"
else
    log_warning "Helm installation failed: $HELM_INSTALL_OUTPUT"
fi

# Install Claude Code CLI
log_info "Installing Claude Code CLI..."
NPM_INSTALL_OUTPUT=$(npm install -g @anthropic-ai/claude-code 2>&1)
NPM_EXIT_CODE=$?

if [ $NPM_EXIT_CODE -eq 0 ] && command -v claude >/dev/null 2>&1; then
    CLAUDE_VERSION=$(claude --version 2>&1 || echo "version unknown")
    log_success "Claude Code CLI installed successfully ($CLAUDE_VERSION)"
    echo "CLAUDE_AVAILABLE=true"
else
    log_warning "Claude Code CLI installation failed: $NPM_INSTALL_OUTPUT"
    echo "CLAUDE_AVAILABLE=false"
fi

# Verify installations
echo ""
log_info "INSTALLATION VERIFICATION"
echo "========================="

# Check each tool
for tool in curl wget jq python3 pip3; do
    if command -v $tool >/dev/null 2>&1; then
        log_success "$tool: Available"
    else
        log_warning "$tool: Not available"
    fi
done

# Check optional tools
for tool in kubectl helm claude; do
    if command -v $tool >/dev/null 2>&1; then
        log_success "$tool: Available"
    else
        log_warning "$tool: Not available"
    fi
done

log_success "Environment setup completed"