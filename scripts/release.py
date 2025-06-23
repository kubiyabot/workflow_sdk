#!/usr/bin/env python3
"""
Release script for kubiya-workflow-sdk

This script helps manage version bumps and releases.
Usage:
    python scripts/release.py patch  # 1.0.0 -> 1.0.1
    python scripts/release.py minor  # 1.0.0 -> 1.1.0  
    python scripts/release.py major  # 1.0.0 -> 2.0.0
    python scripts/release.py 1.2.3  # Set specific version
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def get_current_version():
    """Get current version from __version__.py"""
    version_file = Path("kubiya_workflow_sdk/__version__.py")
    content = version_file.read_text()
    match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
    if not match:
        raise ValueError("Could not find version in __version__.py")
    return match.group(1)


def parse_version(version_str):
    """Parse version string into tuple of ints"""
    parts = version_str.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version_str}")
    return tuple(int(p) for p in parts)


def bump_version(current_version, bump_type):
    """Bump version based on type"""
    major, minor, patch = parse_version(current_version)
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        # Assume it's a specific version
        parse_version(bump_type)  # Validate format
        return bump_type


def update_version_file(new_version):
    """Update version in __version__.py"""
    version_file = Path("kubiya_workflow_sdk/__version__.py")
    content = version_file.read_text()
    
    new_content = re.sub(
        r'__version__ = ["\'][^"\']+["\']',
        f'__version__ = "{new_version}"',
        content
    )
    
    version_file.write_text(new_content)
    print(f"Updated __version__.py to {new_version}")


def run_command(cmd, check=True):
    """Run shell command"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if check and result.returncode != 0:
        print(f"Command failed: {cmd}")
        print(f"Error: {result.stderr}")
        sys.exit(1)
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Release kubiya-workflow-sdk")
    parser.add_argument(
        "version_type",
        choices=["major", "minor", "patch"],
        nargs="?",
        help="Version bump type or specific version (e.g., 1.2.3)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true", 
        help="Skip running tests before release"
    )
    
    args = parser.parse_args()
    
    if not args.version_type:
        current = get_current_version()
        print(f"Current version: {current}")
        print("Usage: python scripts/release.py [major|minor|patch|X.Y.Z]")
        return
    
    # Get current version
    current_version = get_current_version()
    print(f"Current version: {current_version}")
    
    # Calculate new version
    try:
        new_version = bump_version(current_version, args.version_type)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    print(f"New version: {new_version}")
    
    if args.dry_run:
        print("Dry run - no changes made")
        return
    
    # Confirm
    response = input(f"Release version {new_version}? [y/N]: ")
    if response.lower() != 'y':
        print("Aborted")
        return
    
    # Check git status
    result = run_command("git status --porcelain")
    if result.stdout.strip():
        print("Error: Working directory not clean. Commit changes first.")
        sys.exit(1)
    
    # Run tests
    if not args.skip_tests:
        print("Running tests...")
        run_command("python -m pytest tests/ -v")
        print("✓ Tests passed")
    
    # Update version
    update_version_file(new_version)
    
    # Commit changes
    run_command(f'git add kubiya_workflow_sdk/__version__.py')
    run_command(f'git commit -m "Bump version to {new_version}"')
    
    # Create tag
    run_command(f'git tag -a v{new_version} -m "Release v{new_version}"')
    
    # Push
    run_command('git push origin main')
    run_command(f'git push origin v{new_version}')
    
    print(f"✓ Released version {new_version}")
    print("GitHub Actions will now build and publish to PyPI")


if __name__ == "__main__":
    main() 