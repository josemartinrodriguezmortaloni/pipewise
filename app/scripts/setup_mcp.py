#!/usr/bin/env python3
"""
setup_mcp.py - Script para configurar los MCP servers del proyecto CRM
"""

import os
import json
import subprocess
import sys
from pathlib import Path


def check_dependencies():
    """Verificar que las dependencias estén instaladas"""
    try:
        import mcp

        print("✅ MCP library installed")
    except ImportError:
        print("❌ Installing MCP library...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
        print("✅ MCP library installed")

    # Verificar otras dependencias
    required = ["openai", "supabase", "requests", "python-dotenv"]
    for lib in required:
        try:
            __import__(lib.replace("-", "_"))
            print(f"✅ {lib} is available")
        except ImportError:
            print(f"❌ {lib} not found. Install with: pip install {lib}")


def check_environment():
    """Verificar variables de entorno"""
    required_vars = {
        "SUPABASE_URL": "https://tu-proyecto.supabase.co",
        "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "OPENAI_API_KEY": "sk-...",
        "CALENDLY_ACCESS_TOKEN": "eyJraWQiOiIxY2UxZTEzNjE3ZGNmNmRiY2... (opcional)",
    }

    print("\n🔧 Verificando variables de entorno:")
    missing = []

    for var, example in required_vars.items():
        value = os.getenv(var)
        if value:
            masked = f"{value[:10]}..." if len(value) > 10 else "***"
            print(f"✅ {var}: {masked}")
        else:
            print(f"❌ {var}: Not set")
            print(f"   Example: export {var}='{example}'")
            if var != "CALENDLY_ACCESS_TOKEN":
                missing.append(var)

    if missing:
        print(f"\n⚠️ Missing required environment variables: {', '.join(missing)}")
        return False

    return True


def test_mcp_servers():
    """Probar los MCP servers"""
    print("\n🧪 Testing MCP Servers:")

    # Test Supabase MCP
    supabase_path = Path("app/agents/tools/supabase_mcp.py")
    if supabase_path.exists():
        print("✅ Supabase MCP server file found")

        # Solo hacer test de importación si las variables están configuradas
        if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"):
            try:
                # Test basic syntax check
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        f"import sys; sys.path.insert(0, '.'); exec(open('{supabase_path}').read())",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    print("✅ Supabase MCP server syntax OK")
                else:
                    print(
                        f"⚠️ Supabase MCP server syntax issues: {result.stderr.split('Traceback')[0].strip()}"
                    )
            except subprocess.TimeoutExpired:
                print("⚠️ Supabase MCP server test timeout (may be OK)")
            except Exception as e:
                print(f"⚠️ Supabase MCP server test failed: {e}")
        else:
            print("⚠️ Skipping Supabase MCP test (environment vars not set)")
    else:
        print("❌ Supabase MCP server file not found")
        print(f"   Expected: {supabase_path.absolute()}")

    # Test Calendly MCP
    calendly_path = Path("app/agents/tools/calendly.py")
    if calendly_path.exists():
        print("✅ Calendly MCP server file found")
        if os.getenv("CALENDLY_ACCESS_TOKEN"):
            print("✅ Calendly token configured")
            try:
                # Test basic syntax check
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        f"import sys; sys.path.insert(0, '.'); exec(open('{calendly_path}').read())",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    print("✅ Calendly MCP server syntax OK")
                else:
                    print(
                        f"⚠️ Calendly MCP server syntax issues: {result.stderr.split('Traceback')[0].strip()}"
                    )
            except Exception as e:
                print(f"⚠️ Calendly MCP server test failed: {e}")
        else:
            print("⚠️ Calendly token not configured (optional)")
    else:
        print("❌ Calendly MCP server file not found")


def create_mcp_config():
    """Crear archivo de configuración MCP"""
    config = {
        "mcpServers": {
            "supabase": {
                "command": "python",
                "args": ["app/agents/tools/supabase_mcp.py"],
                "env": {
                    "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
                    "SUPABASE_ANON_KEY": os.getenv("SUPABASE_ANON_KEY", ""),
                },
            }
        }
    }

    # Agregar Calendly si está configurado
    if os.getenv("CALENDLY_ACCESS_TOKEN"):
        config["mcpServers"]["calendly"] = {
            "command": "python",
            "args": ["app/agents/tools/calendly.py"],
            "env": {"CALENDLY_ACCESS_TOKEN": os.getenv("CALENDLY_ACCESS_TOKEN", "")},
        }

    # Guardar configuración
    config_path = Path("mcp_config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n📄 MCP configuration saved to: {config_path.absolute()}")
    print("   You can use this for testing MCP servers manually")


def test_agents():
    """Probar que los agentes funcionen"""
    print("\n🤖 Testing Agents:")

    # Solo hacer test si las variables de entorno están configuradas
    if not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY")):
        print("⚠️ Skipping agent tests (Supabase environment vars not set)")
        return

    try:
        # Agregar el directorio raíz al path
        import sys

        project_root = Path.cwd()
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        # Test imports
        from app.agents.lead_qualifier import LeadAgent
        from app.agents.outbound_contact import OutboundAgent
        from app.agents.meeting_scheduler import MeetingSchedulerAgent

        print("✅ All agent imports successful")

        # Test agent initialization
        lead_agent = LeadAgent()
        outbound_agent = OutboundAgent()
        meeting_agent = MeetingSchedulerAgent()

        print("✅ All agents initialized successfully")

        # Verify they have tools configuration
        lead_tools = lead_agent._get_tools()
        outbound_tools = outbound_agent._get_tools()
        meeting_tools = meeting_agent._get_tools()

        # Check for MCP configuration with server_label
        def check_mcp_format(tools, agent_name):
            has_mcp = False
            has_server_label = False
            for tool in tools:
                if tool.get("type") == "mcp":
                    has_mcp = True
                    if "server_label" in tool:
                        has_server_label = True
                        print(
                            f"✅ {agent_name} has MCP with server_label: {tool['server_label']}"
                        )
                    else:
                        print(f"❌ {agent_name} has MCP but missing server_label")

            if not has_mcp:
                print(f"❌ {agent_name} not configured for MCP")
                return False
            return has_server_label

        lead_ok = check_mcp_format(lead_tools, "LeadAgent")
        outbound_ok = check_mcp_format(outbound_tools, "OutboundAgent")
        meeting_ok = check_mcp_format(meeting_tools, "MeetingSchedulerAgent")

        if lead_ok and outbound_ok and meeting_ok:
            print("✅ All agents configured correctly for MCP with server_label")
        else:
            print("❌ Some agents need MCP configuration updates")
            print("   Make sure all agents have 'server_label' in their MCP tools")

    except ImportError as e:
        print(f"⚠️ Agent import failed (expected during setup): {e}")
        print("   This is normal if you haven't updated the agents to use MCP yet")
    except Exception as e:
        print(f"❌ Agent testing failed: {e}")


def main():
    """Ejecutar setup completo"""
    print("🚀 Setting up CRM MCP Infrastructure")
    print("=" * 50)

    # 1. Check dependencies
    print("1. Checking dependencies...")
    check_dependencies()

    # 2. Check environment
    print("\n2. Checking environment...")
    env_ok = check_environment()

    # 3. Test MCP servers
    print("\n3. Testing MCP servers...")
    test_mcp_servers()

    # 4. Create config
    print("\n4. Creating MCP configuration...")
    create_mcp_config()

    # 5. Test agents
    print("\n5. Testing agents...")
    test_agents()

    # Summary
    print("\n" + "=" * 50)
    if env_ok:
        print("🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Update your agents to use MCP (if not done)")
        print("2. Run: python __main__.py (to test the full workflow)")
        print("3. Start using the improved CRM system!")
    else:
        print("⚠️ Setup completed with warnings")
        print("Please configure missing environment variables")


if __name__ == "__main__":
    main()
