# PyPI Publishing Setup Guide

This guide will help you set up automated PyPI publishing for the `kubiya-workflow-sdk` package.

## 🚀 Quick Start

### Option 1: Automated Release (Recommended)

1. **Set up PyPI Trusted Publishing** (see below)
2. **Create a release:**
   ```bash
   make release-patch  # 0.1.0 -> 0.1.1
   make release-minor  # 0.1.0 -> 0.2.0  
   make release-major  # 0.1.0 -> 1.0.0
   ```
3. **GitHub Actions will automatically:**
   - Run tests
   - Build the package
   - Publish to PyPI

### Option 2: Manual Build & Upload

```bash
# Install build tools
pip install build twine

# Build the package
make build

# Test upload (optional)
make publish-test

# Upload to PyPI
make publish
```

## 🔐 Setting Up PyPI Trusted Publishing (Required)

This is the **secure, recommended way** to publish packages without storing API tokens.

### 1. Create PyPI Account & Project

1. Go to [PyPI](https://pypi.org) and create an account
2. **Reserve your package name** by uploading an initial version:
   ```bash
   # Build and upload manually first time
   pip install build twine
   python -m build
   python -m twine upload dist/* --repository pypi
   ```

### 2. Configure Trusted Publishing on PyPI

1. Go to your project page: `https://pypi.org/manage/project/kubiya-workflow-sdk/`
2. Go to **"Publishing"** tab
3. Click **"Add a new pending publisher"**
4. Fill in:
   - **PyPI Project Name**: `kubiya-workflow-sdk`
   - **Owner**: Your GitHub username/org (e.g., `kubiya-ai`)
   - **Repository name**: `workflow-sdk`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi`

### 3. Create GitHub Environment

1. In your GitHub repo, go to **Settings** → **Environments**
2. Create environment called `pypi`
3. Add protection rules (optional but recommended):
   - ✅ Required reviewers
   - ✅ Restrict to protected branches

## 📋 What's Already Set Up

✅ **Package Configuration** (`pyproject.toml`)
- Dynamic versioning from `__version__.py`
- Proper metadata and classifiers
- Multiple optional dependencies (`dev`, `server`, `adk`)

✅ **GitHub Actions Workflows**
- `.github/workflows/test.yml` - Runs tests on every PR
- `.github/workflows/publish.yml` - Publishes on tags/releases

✅ **Release Management**
- `scripts/release.py` - Automated version bumping
- `Makefile` commands for easy releases
- `MANIFEST.in` - Controls what files are included

✅ **Build System**
- Modern `pyproject.toml` configuration
- Setuptools backend with proper package discovery

## 🔄 Release Process

### Automated (Recommended)
```bash
# Patch release (0.1.0 -> 0.1.1)
make release-patch

# Minor release (0.1.0 -> 0.2.0)  
make release-minor

# Major release (0.1.0 -> 1.0.0)
make release-major
```

This will:
1. Run tests
2. Bump version in `__version__.py`
3. Commit changes
4. Create and push git tag
5. Trigger GitHub Actions to publish

### Manual Git Tags
```bash
# Create tag manually
git tag v0.1.1
git push origin v0.1.1
```

### GitHub Releases
1. Go to GitHub → Releases → Create Release  
2. Choose tag or create new one
3. GitHub Actions will trigger automatically

## 🧪 Testing Your Setup

### Test Package Build Locally
```bash
make build
ls dist/  # Should see .whl and .tar.gz files
```

### Test Upload to Test PyPI
```bash
# Upload to test PyPI first
make publish-test

# Install from test PyPI
pip install -i https://test.pypi.org/simple/ kubiya-workflow-sdk
```

### Verify Installation
```python
import kubiya_workflow_sdk
print(kubiya_workflow_sdk.__version__)
```

## 🔧 Troubleshooting

### "Package already exists" Error
If you get this error, it means someone else has already registered the package name. You'll need to:
1. Choose a different name in `pyproject.toml`
2. Update the package name throughout the codebase

### Trusted Publishing Not Working
1. Verify environment name matches exactly (`pypi`)
2. Check repository settings match your GitHub repo
3. Ensure you've uploaded at least one version manually first

### Version Conflicts
The package uses dynamic versioning from `kubiya_workflow_sdk/__version__.py`. Make sure:
1. This file exists and has `__version__ = "x.y.z"`
2. The version follows semantic versioning (major.minor.patch)

### GitHub Actions Failing  
1. Check the Actions tab for detailed error logs
2. Ensure all required secrets/environments are configured
3. Verify tests pass locally first

## 📚 Additional Resources

- [PyPI Trusted Publishing Guide](https://docs.pypi.org/trusted-publishers/)
- [Python Packaging User Guide](https://packaging.python.org/)
- [Semantic Versioning](https://semver.org/)

## 🆘 Getting Help

If you encounter issues:
1. Check GitHub Actions logs for detailed errors
2. Verify PyPI trusted publishing configuration
3. Test the build process locally first
4. Ensure all tests pass before releasing 