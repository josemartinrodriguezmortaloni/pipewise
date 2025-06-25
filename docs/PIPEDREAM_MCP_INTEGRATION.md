# Pipedream MCP Integration with PipeWise Agents

This document describes the complete integration of Pipedream MCP (Model Context Protocol) servers with PipeWise agents, following the official [OpenAI Agents SDK MCP documentation](https://openai.github.io/openai-agents-python/mcp/).

## Overview

The integration provides PipeWise agents with direct access to external business tools through standardized MCP servers hosted by Pipedream. This dramatically expands the agents' capabilities beyond the local CRM functions.

### Integrated Services

| Service | Tools | Agent Access | Use Cases |
|---------|-------|--------------|-----------|
| **Calendly v2** | 7 tools | Meeting Scheduler | Schedule demos, calls, consultations |
| **Pipedrive** | 37 tools | Coordinator | Manage leads, deals, pipeline tracking |
| **Salesforce REST API** | 30 tools | Coordinator | Enterprise CRM operations |
| **Zoho CRM** | 11 tools | Coordinator | Alternative CRM management |
| **SendGrid** | 20 tools | Coordinator | Professional email automation |
| **Google Calendar** | 10 tools | Meeting Scheduler | Calendar management, scheduling |

**Total: 115+ external tools across 6 major business platforms**

## Architecture

### MCP Server Creation

The `create_pipedream_mcp_servers()` function creates SSE (Server-Sent Events) connections to Pipedream MCP servers:

```python
from agents.mcp import MCPServerSse

def create_pipedream_mcp_servers() -> Dict[str, MCPServerSse]:
    """
    Create Pipedream MCP servers following OpenAI Agents SDK documentation
    """
    # Environment variables required
    pipedream_token = os.getenv("PIPEDREAM_TOKEN")
    project_id = os.getenv("PIPEDREAM_PROJECT_ID", "proj_default")
    environment = os.getenv("PIPEDREAM_ENVIRONMENT", "production")
    
    # Create SSE connections for each service
    mcp_servers["calendly"] = MCPServerSse(
        params={
            "url": "https://remote.mcp.pipedream.net",
            "headers": {
                "Authorization": f"Bearer {pipedream_token}",
                "x-pd-project-id": project_id,
                "x-pd-environment": environment,
                "x-pd-external-user-id": "pipewise_scheduler",
                "x-pd-app-slug": "calendly_v2",
            },
        },
        cache_tools_list=True  # Cache for performance
    )
```

### Agent Integration

Each agent type receives specific MCP servers relevant to its function:

#### Coordinator Agent
- **CRM Tools**: Pipedrive, Salesforce, Zoho CRM
- **Email Tools**: SendGrid
- **Use Case**: Manages leads, syncs with multiple CRM systems, sends professional emails

```python
coordinator_mcp_servers = []
if mcp_servers:
    # Coordinator gets CRM and email automation MCP servers
    for server_name in ["pipedrive", "salesforce", "zoho_crm", "sendgrid"]:
        if server_name in mcp_servers:
            coordinator_mcp_servers.append(mcp_servers[server_name])

coordinator_agent = Agent(
    name="PipeWise Coordinator",
    instructions="...",
    tools=[...local_tools...],
    mcp_servers=coordinator_mcp_servers,  # External MCP tools
    output_type=CoordinatorResponse,
)
```

#### Meeting Scheduler Agent
- **Scheduling Tools**: Calendly, Google Calendar
- **Use Case**: Schedules meetings, manages calendar availability

```python
meeting_mcp_servers = []
if mcp_servers:
    # Meeting scheduler gets Calendly and Google Calendar MCP servers
    for server_name in ["calendly", "google_calendar"]:
        if server_name in mcp_servers:
            meeting_mcp_servers.append(mcp_servers[server_name])

meeting_scheduler_agent = Agent(
    name="Meeting Scheduling Specialist", 
    instructions="...",
    tools=[...local_tools...],
    mcp_servers=meeting_mcp_servers,  # External MCP tools
    output_type=MeetingScheduleResult,
)
```

## Environment Setup

### Required Environment Variables

```bash
# Required for MCP integration
PIPEDREAM_TOKEN=your_pipedream_api_token

# Optional configuration
PIPEDREAM_PROJECT_ID=your_project_id        # Default: "proj_default"
PIPEDREAM_ENVIRONMENT=production             # Default: "production"
```

### Obtaining Pipedream Token

1. Create an account at [Pipedream](https://pipedream.com)
2. Navigate to [Account Settings](https://pipedream.com/settings/account)
3. Generate an API token
4. Set `PIPEDREAM_TOKEN` environment variable

## Usage Examples

### 1. Email Processing with CRM Integration

```python
# Incoming email from prospect
email_message = IncomingMessage(
    lead_id="lead_001",
    channel="email",
    message_content="Hi, I'm interested in your service. Can we schedule a demo?",
    context={"sender_email": "prospect@company.com"}
)

# Coordinator processes with MCP tools
result = await agents.handle_incoming_message(email_message)

# Coordinator can now:
# - Update lead in Pipedrive/Salesforce/Zoho using MCP tools
# - Send professional response via SendGrid MCP tools
# - Handoff to meeting scheduler with context
```

### 2. Meeting Scheduling with Calendar Integration

```python
# Meeting scheduler uses MCP tools
# - Check availability via Google Calendar MCP
# - Schedule meeting via Calendly MCP
# - Send calendar invites via MCP tools
```

### 3. Multi-CRM Lead Management

```python
# Coordinator can sync lead across multiple CRMs:
# - Create lead in Pipedrive via MCP
# - Sync to Salesforce via MCP
# - Update Zoho CRM via MCP
# - All using standardized MCP protocol
```

## Technical Details

### MCP Protocol Benefits

1. **Standardization**: All external tools use the same MCP interface
2. **Caching**: Tool lists are cached for performance (`cache_tools_list=True`)
3. **Error Handling**: Graceful fallback when MCP servers are unavailable
4. **Scalability**: Easy to add new MCP servers without code changes

### Performance Optimizations

- **Tool List Caching**: Reduces latency by caching available tools
- **Connection Pooling**: SSE connections are reused across agent runs
- **Graceful Degradation**: System works without MCP servers if needed

### Security

- **Token Authentication**: All MCP requests use secure Pipedream tokens
- **Header-based Auth**: Service-specific authentication via headers
- **Environment Isolation**: Separate project IDs and environments

## Testing

### Demo Script

Run the integration demo:

```bash
python tests/demo_mcp_integration.py
```

### Expected Output

```
🚀 Starting Pipedream MCP Integration Demo
✅ Created 6 MCP servers:
  - calendly: sse: https://remote.mcp.pipedream.net
  - pipedrive: sse: https://remote.mcp.pipedream.net
  - salesforce: sse: https://remote.mcp.pipedream.net
  - zoho_crm: sse: https://remote.mcp.pipedream.net
  - sendgrid: sse: https://remote.mcp.pipedream.net
  - google_calendar: sse: https://remote.mcp.pipedream.net

📊 Integration Summary:
  - Active MCP servers: 6/6
  - Estimated available tools: 115
  - Coordinator MCP access: CRM & Email servers
  - Meeting Scheduler MCP access: Calendly & Google Calendar

🎉 Pipedream MCP integration is working!
```

## Troubleshooting

### Common Issues

1. **No MCP servers created**
   - Check `PIPEDREAM_TOKEN` environment variable
   - Verify Pipedream account and token validity

2. **MCP connection errors**
   - Check network connectivity to `remote.mcp.pipedream.net`
   - Verify Pipedream project ID and environment

3. **Tool discovery failures**
   - Check Pipedream service configurations
   - Verify MCP server app slugs are correct

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration Status

### ✅ Completed Features

- [x] MCP server creation following OpenAI Agents SDK patterns
- [x] SSE connection configuration with Pipedream
- [x] Agent integration with service-specific MCP servers
- [x] Tool list caching for performance
- [x] Graceful fallback when MCP unavailable
- [x] Demo script with comprehensive testing
- [x] Error handling and logging

### 🚀 Benefits Achieved

1. **115+ External Tools**: Access to major business platforms
2. **Standardized Integration**: All external tools use MCP protocol
3. **Performance Optimized**: Caching and connection pooling
4. **Service-Specific Access**: Agents get relevant tools only
5. **Production Ready**: Proper error handling and fallbacks

### 📈 Impact on Agent Capabilities

**Before MCP Integration:**
- Local CRM functions only
- Manual scheduling coordination
- Limited external tool access

**After MCP Integration:**
- Direct access to Calendly, Pipedrive, Salesforce, Zoho, SendGrid, Google Calendar
- Automated meeting scheduling
- Multi-CRM synchronization
- Professional email automation
- 115+ business tools at agent disposal

## References

- [OpenAI Agents SDK MCP Documentation](https://openai.github.io/openai-agents-python/mcp/)
- [Pipedream MCP Documentation](https://pipedream.com/docs/connect/mcp/openai/)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/introduction)
 