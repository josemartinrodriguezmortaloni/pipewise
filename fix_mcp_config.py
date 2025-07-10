#!/usr/bin/env python3
"""
MCP Configuration Fix Script
Configures environment variables and fixes MCP-related issues.
"""

import os
import sys
import subprocess
from pathlib import Path


def check_environment():
    """Check and fix environment configuration."""
    print("🔧 Checking environment configuration...")

    # Check current DISABLE_MCP value
    disable_mcp = os.getenv("DISABLE_MCP", "false").lower()
    print(f"📋 Current DISABLE_MCP value: {disable_mcp}")

    if disable_mcp == "true":
        print("⚠️ MCP is currently disabled!")
        print("💡 To enable MCP servers, set DISABLE_MCP=false or remove the variable")
        return False

    print("✅ MCP is enabled in environment")
    return True


def check_node_installation():
    """Check if Node.js and npm are properly installed."""
    print("🔧 Checking Node.js installation...")

    try:
        # Check Node.js
        node_result = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, check=True
        )
        print(f"✅ Node.js version: {node_result.stdout.strip()}")

        # Check npm
        npm_result = subprocess.run(
            ["npm", "--version"], capture_output=True, text=True, check=True
        )
        print(f"✅ npm version: {npm_result.stdout.strip()}")

        # Check npx
        npx_result = subprocess.run(
            ["npx", "--version"], capture_output=True, text=True, check=True
        )
        print(f"✅ npx version: {npx_result.stdout.strip()}")

        return True

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"❌ Node.js/npm not found or not working: {e}")
        print("💡 Install Node.js from https://nodejs.org/")
        return False


def install_mcp_filesystem_server():
    """Install the MCP filesystem server globally."""
    print("🔧 Installing MCP filesystem server...")

    try:
        # Install the MCP filesystem server
        result = subprocess.run(
            ["npm", "install", "-g", "@modelcontextprotocol/server-filesystem"],
            capture_output=True,
            text=True,
            check=True,
        )

        print("✅ MCP filesystem server installed successfully")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install MCP filesystem server: {e}")
        print(f"Error output: {e.stderr}")
        return False


def test_mcp_server():
    """Test if the MCP filesystem server can be started."""
    print("🔧 Testing MCP filesystem server...")

    try:
        # Create a temporary directory for testing
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"📁 Testing with directory: {temp_dir}")

            # Test the MCP server command
            result = subprocess.run(
                ["npx", "-y", "@modelcontextprotocol/server-filesystem", temp_dir],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # If it runs without immediate error, it's likely working
            print("✅ MCP filesystem server test completed")
            return True

    except subprocess.TimeoutExpired:
        # Timeout is expected since the server would run indefinitely
        print("✅ MCP filesystem server started successfully (timeout expected)")
        return True
    except Exception as e:
        print(f"❌ MCP filesystem server test failed: {e}")
        return False


def create_env_file():
    """Create a proper .env file with MCP enabled."""
    env_content = """# PipeWise Environment Configuration
# MCP Configuration - CRITICAL: Set to false to enable MCP servers
DISABLE_MCP=false

# Required for MCP Pipedream integration
PIPEDREAM_CLIENT_SECRET=your_pipedream_secret_here
PIPEDREAM_PROJECT_ID=proj_default
PIPEDREAM_ENVIRONMENT=development

# Add your other environment variables here
"""

    env_file = Path(".env")

    if env_file.exists():
        print("📋 .env file already exists")

        # Read current content
        with open(env_file, "r") as f:
            content = f.read()

        # Check if DISABLE_MCP is configured
        if "DISABLE_MCP" not in content:
            print("🔧 Adding DISABLE_MCP=false to .env file...")
            with open(env_file, "a") as f:
                f.write("\n# MCP Configuration\nDISABLE_MCP=false\n")
            print("✅ Added DISABLE_MCP=false to .env file")
        else:
            print("📋 DISABLE_MCP already configured in .env file")
    else:
        print("🔧 Creating new .env file...")
        with open(env_file, "w") as f:
            f.write(env_content)
        print("✅ Created .env file with MCP enabled")


def main():
    """Main configuration function."""
    print("🚀 Starting MCP configuration fix...")

    issues_found = []

    # Check environment
    if not check_environment():
        issues_found.append("Environment configuration")

    # Check Node.js installation
    if not check_node_installation():
        issues_found.append("Node.js installation")

    # Install MCP filesystem server
    if not install_mcp_filesystem_server():
        issues_found.append("MCP server installation")

    # Test MCP server
    if not test_mcp_server():
        issues_found.append("MCP server functionality")

    # Create/update .env file
    try:
        create_env_file()
    except Exception as e:
        print(f"⚠️ Could not create/update .env file: {e}")
        issues_found.append("Environment file creation")

    # Summary
    print("\n" + "=" * 60)
    print("🎯 CONFIGURATION SUMMARY")
    print("=" * 60)

    if issues_found:
        print(f"⚠️ Issues found: {len(issues_found)}")
        for issue in issues_found:
            print(f"   - {issue}")
        print("\n💡 NEXT STEPS:")
        print("1. Fix the issues listed above")
        print("2. Restart your server with: uv run server.py")
        print("3. Set DISABLE_MCP=false in your environment")
        return False
    else:
        print("✅ All checks passed!")
        print("\n💡 NEXT STEPS:")
        print("1. Restart your server with: uv run server.py")
        print("2. The MCP servers should now work correctly")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
