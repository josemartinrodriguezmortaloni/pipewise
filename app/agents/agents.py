"""
Modern Agent Architecture with OpenAI AgentSDK
Following the exact implementation pattern from improvements.md

Enhanced with:
- Dual memory system (volatile + persistent)
- Handoff callbacks for agent communication tracking
- Context management for workflow coordination
- Prompts loaded from prompts directory
- Multi-channel communication tools (email, Instagram, Twitter)
"""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict
import logging
import uuid
from pathlib import Path

from agents import Agent, Runner, function_tool, handoff
from agents.mcp import MCPServerSse
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from app.supabase.supabase_client import SupabaseCRMClient
from app.schemas.lead_schema import LeadUpdate
from .memory import MemoryManager, InMemoryStore, SupabaseMemoryStore
from .callbacks import create_handoff_callback, HandoffData
from .tools.twitter import TwitterMCPServer

logger = logging.getLogger(__name__)


# ============================================================================
# PROMPT LOADING FUNCTIONALITY
# ============================================================================


def load_prompt(prompt_name: str) -> str:
    """
    Load prompt content from the prompts directory.

    Args:
        prompt_name: Name of the prompt file (without .md extension)

    Returns:
        Prompt content as string
    """
    try:
        # Get the prompts directory path
        current_dir = Path(__file__).parent
        prompts_dir = current_dir / "prompts"
        prompt_file = prompts_dir / f"{prompt_name}.md"

        if prompt_file.exists():
            with open(prompt_file, "r", encoding="utf-8") as file:
                content = file.read()
                logger.info(f"✅ Loaded prompt: {prompt_name}")
                return content
        else:
            logger.warning(f"⚠️ Prompt file not found: {prompt_file}")
            return f"Prompt file {prompt_name} not found. Using default instructions."

    except Exception as e:
        logger.error(f"❌ Error loading prompt {prompt_name}: {e}")
        return f"Error loading prompt {prompt_name}. Using default instructions."


# ============================================================================
# TYPED CONTEXT AND MODELS - Following improvements.md pattern
# ============================================================================


@dataclass
class TenantContext:
    """Typed context for multi-tenant operations"""

    tenant_id: str
    user_id: str
    is_premium: bool
    api_limits: dict
    features_enabled: List[str]
    memory_manager: Optional[MemoryManager] = None


class LeadAnalysis(BaseModel):
    """Structured output for lead qualification - Following improvements.md pattern"""

    model_config = ConfigDict(extra="forbid")

    lead_id: str
    qualification_score: float
    qualified: bool
    key_factors: List[str]
    recommendations: List[str]
    risk_factors: List[str]
    opportunity_size: str


class MeetingScheduleResult(BaseModel):
    """Structured output for meeting scheduling"""

    model_config = ConfigDict(extra="forbid")

    lead_id: str
    success: bool
    meeting_url: Optional[str]
    event_type: Optional[str]
    scheduled_time: Optional[str]


class IncomingMessage(BaseModel):
    """Structured input for incoming messages from various channels"""

    lead_id: str
    channel: str  # "email", "instagram", "twitter"
    channel_user_id: Optional[str] = None  # Instagram ID, Twitter ID, etc.
    channel_username: Optional[str] = None  # @username for social media
    message_content: str
    context: Optional[Dict[str, Any]] = None


class CoordinatorResponse(BaseModel):
    """Structured output for coordinator responses"""

    model_config = ConfigDict(extra="forbid")  # Explicitly forbid extra fields

    response_sent: bool
    channel_used: str
    response_content: str
    next_step: str
    lead_updated: bool
    handoff_required: bool
    handoff_reason: Optional[str] = None


# ============================================================================
# FUNCTION TOOLS - Following exact @function_tool pattern from improvements.md
# ============================================================================


@function_tool
def get_crm_lead_data(lead_id: str) -> str:
    """Gets complete lead data from CRM.

    Args:
        lead_id: Unique lead identifier
    """
    try:
        db_client = SupabaseCRMClient()
        lead = db_client.get_lead(lead_id)
        if lead:
            return f"Lead data for {lead_id}: Name={lead.name}, Company={lead.company}, Status={lead.status}, Qualified={lead.qualified}"
        return f"No lead found with ID {lead_id}"
    except Exception as e:
        logger.error(f"Error getting lead data: {e}")
        return f"Error retrieving lead data: {str(e)}"


@function_tool
def analyze_lead_opportunity(lead_id: str) -> str:
    """Analyzes a specific lead opportunity for qualification.

    Args:
        lead_id: Unique lead identifier
    """
    try:
        db_client = SupabaseCRMClient()
        lead = db_client.get_lead(lead_id)
        if not lead:
            return f"Lead {lead_id} not found"

        # Analyze lead data for qualification
        analysis = f"Lead analysis for {lead_id}: "
        analysis += f"Company size indicator: {lead.metadata.get('company_size', 'Unknown') if lead.metadata else 'Unknown'}, "
        analysis += f"Industry: {lead.metadata.get('industry', 'Unknown') if lead.metadata else 'Unknown'}, "
        analysis += (
            f"Message indicates budget: {'budget' in (lead.message or '').lower()}"
        )

        return analysis
    except Exception as e:
        logger.error(f"Error analyzing lead opportunity: {e}")
        return f"Error analyzing opportunity: {str(e)}"


@function_tool
def update_lead_qualification(
    lead_id: str, qualified: bool, reason: str, score: float = 0.0
) -> str:
    """
    Updates lead qualification status in CRM.

    Args:
        lead_id: Lead identifier to update
        qualified: Whether the lead is qualified
        reason: Reason for qualification decision
        score: Qualification score (0-100)
    """
    try:
        db_client = SupabaseCRMClient()

        metadata = {
            "qualification_reason": reason,
            "qualification_score": score,
            "qualified_by": "lead_agent_sdk",
            "qualification_timestamp": "now()",
        }

        status = "qualified" if qualified else "unqualified"
        updates = LeadUpdate(qualified=qualified, status=status, metadata=metadata)

        result = db_client.update_lead(lead_id, updates)
        if result:
            return f"Lead {lead_id} updated successfully: qualified={qualified}, score={score}"
        return f"Failed to update lead {lead_id}"

    except Exception as e:
        logger.error(f"Error updating lead qualification: {e}")
        return f"Error updating lead: {str(e)}"


@function_tool
def schedule_meeting_for_lead(lead_id: str, meeting_url: str, event_type: str) -> str:
    """
    Schedules a meeting for a qualified lead.

    Args:
        lead_id: Lead identifier
        meeting_url: Calendly or meeting booking URL
        event_type: Type of meeting scheduled
    """
    try:
        db_client = SupabaseCRMClient()

        metadata = {
            "meeting_url": meeting_url,
            "meeting_type": event_type,
            "scheduled_by": "meeting_agent_sdk",
            "scheduling_timestamp": "now()",
        }

        updates = LeadUpdate(meeting_scheduled=True, metadata=metadata)
        result = db_client.update_lead(lead_id, updates)

        if result:
            return f"Meeting scheduled for lead {lead_id}: {meeting_url}"
        return f"Failed to schedule meeting for lead {lead_id}"

    except Exception as e:
        logger.error(f"Error scheduling meeting: {e}")
        return f"Error scheduling meeting: {str(e)}"


@function_tool
def send_twitter_dm(username: str, message: str) -> str:
    """Send a direct message on Twitter to a prospect.

    Args:
        username: Twitter username (without @)
        message: Message content to send
    """
    try:
        twitter_server = TwitterMCPServer()
        result = twitter_server.send_dm("", message)

        if result.get("success"):
            return f"Twitter DM sent successfully to @{username}"
        else:
            return f"Failed to send Twitter DM: {result.get('error', 'Unknown error')}"
    except Exception as e:
        logger.error(f"Error sending Twitter DM: {e}")
        return f"Error sending Twitter DM: {str(e)}"


@function_tool
def get_twitter_user_info(username: str) -> str:
    """Get Twitter user information by username.

    Args:
        username: Twitter username (without @)
    """
    try:
        twitter_server = TwitterMCPServer()
        result = twitter_server.get_user_by_username(username)

        if result.get("success"):
            return f"Twitter user @{username} found: ID={result.get('user_id')}"
        else:
            return f"Twitter user @{username} not found: {result.get('error', 'Unknown error')}"
    except Exception as e:
        logger.error(f"Error getting Twitter user info: {e}")
        return f"Error getting Twitter user info: {str(e)}"


@function_tool
def reply_to_twitter_thread(tweet_id: str, message: str) -> str:
    """Reply to a Twitter thread with a message.

    Args:
        tweet_id: ID of the tweet to reply to
        message: Reply content
    """
    try:
        twitter_server = TwitterMCPServer()
        result = twitter_server.reply_to_tweet(tweet_id, message)

        if result.get("success"):
            return f"Twitter reply sent successfully to tweet {tweet_id}"
        else:
            return f"Failed to reply to Twitter thread: {result.get('error', 'Unknown error')}"
    except Exception as e:
        logger.error(f"Error replying to Twitter thread: {e}")
        return f"Error replying to Twitter thread: {str(e)}"


# ============================================================================
# MCP SERVERS SETUP - Following OpenAI Agents SDK documentation
# ============================================================================


def get_user_integration(
    user_id: str, integration_type: str
) -> Optional[Dict[str, Any]]:
    """
    Get user integration configuration for a specific integration type.

    Args:
        user_id: User identifier
        integration_type: Type of integration (google_calendar, slack, twitter, etc.)

    Returns:
        Integration configuration if enabled, None otherwise
    """
    # Mock implementation for testing with Twitter support
    logger.info(f"Getting {integration_type} integration for user {user_id}")

    # Specific configurations for different integrations
    mock_integrations = {
        "calendly_v2": {"enabled": True, "config": {}},
        "google_calendar": {"enabled": True, "config": {}},
        "twitter": {"enabled": True, "config": {"account_id": f"twitter_{user_id}"}},
        "pipedrive": {"enabled": False, "config": {}},
        "salesforce_rest_api": {"enabled": False, "config": {}},
        "sendgrid": {"enabled": True, "config": {}},
        "zoho_crm": {"enabled": False, "config": {}},
    }

    return mock_integrations.get(integration_type, {"enabled": False, "config": {}})


def create_pipedream_mcp_servers(
    user_id: Optional[str] = None,
) -> Dict[str, MCPServerSse]:
    """
    Create Pipedream MCP servers for agent integration.
    Only creates servers for integrations enabled by the user.

    Following documentation: https://openai.github.io/openai-agents-python/mcp/

    Args:
        user_id: User identifier to check enabled integrations

    Returns:
        Dictionary of configured MCP servers for user-enabled services only
    """
    # Get Pipedream environment variables
    pipedream_token = os.getenv("PIPEDREAM_TOKEN")
    project_id = os.getenv("PIPEDREAM_PROJECT_ID", "proj_default")
    environment = os.getenv("PIPEDREAM_ENVIRONMENT", "production")

    if not pipedream_token:
        logger.warning(
            "⚠️ PIPEDREAM_TOKEN not found. MCP servers will not be available."
        )
        return {}

    if not user_id:
        logger.warning(
            "⚠️ No user_id provided. Creating MCP servers without user filtering."
        )

    # Base headers for all Pipedream MCP connections
    base_headers = {
        "Authorization": f"Bearer {pipedream_token}",
        "x-pd-project-id": project_id,
        "x-pd-environment": environment,
    }

    # Define all available MCP integrations
    available_mcp_integrations = {
        "calendly_v2": "calendly",
        "google_calendar": "google_calendar",
        "pipedrive": "pipedrive",
        "salesforce_rest_api": "salesforce",
        "zoho_crm": "zoho_crm",
        "sendgrid": "sendgrid",
    }

    # Filter integrations based on user settings
    enabled_integrations = {}
    if user_id:
        # Use local function for user integration checking
        for integration_id, server_key in available_mcp_integrations.items():
            user_config = get_user_integration(user_id, integration_id)
            if user_config and user_config.get("enabled", False):
                enabled_integrations[integration_id] = server_key
                logger.info(
                    f"✅ MCP integration {integration_id} enabled for user {user_id}"
                )
            else:
                logger.debug(
                    f"⚪ MCP integration {integration_id} not enabled for user {user_id}"
                )
    else:
        # Fallback: use all available integrations if no user_id
        enabled_integrations = available_mcp_integrations
        logger.warning("⚠️ No user filtering - creating all MCP servers")

    if not enabled_integrations:
        logger.info(f"ℹ️ No MCP integrations enabled for user {user_id}")
        return {}

    # Create MCP servers for enabled integrations only
    mcp_servers = {}

    try:
        # Create MCP servers only for enabled integrations
        for integration_id, server_key in enabled_integrations.items():
            # Determine external user ID based on integration type
            if integration_id in ["calendly_v2", "google_calendar"]:
                external_user_id = "pipewise_scheduler"
            else:
                external_user_id = "pipewise_coordinator"

            # Create MCP server for this integration
            mcp_servers[server_key] = MCPServerSse(
                params={
                    "url": "https://remote.mcp.pipedream.net",
                    "headers": {
                        **base_headers,
                        "x-pd-external-user-id": external_user_id,
                        "x-pd-app-slug": integration_id,
                    },
                },
                cache_tools_list=True,  # Cache for performance
            )

            logger.info(
                f"✅ Created MCP server for {integration_id} (key: {server_key})"
            )

        logger.info(
            f"✅ Created {len(mcp_servers)} user-specific Pipedream MCP servers"
        )
        return mcp_servers

    except Exception as e:
        logger.error(f"❌ Error creating Pipedream MCP servers: {e}")
        return {}


def create_twitter_mcp_server(
    user_id: Optional[str] = None,
) -> Optional[TwitterMCPServer]:
    """
    Create Twitter MCP server for direct Twitter integration.

    Args:
        user_id: User identifier to check Twitter integration settings

    Returns:
        TwitterMCPServer instance if user has Twitter enabled, None otherwise
    """
    if user_id:
        user_config = get_user_integration(user_id, "twitter")
        if not user_config or not user_config.get("enabled", False):
            logger.info(f"Twitter integration not enabled for user {user_id}")
            return None

    try:
        twitter_server = TwitterMCPServer()
        logger.info("✅ Created local Twitter MCP server")
        return twitter_server
    except Exception as e:
        logger.error(f"❌ Error creating Twitter MCP server: {e}")
        return None


def create_all_mcp_servers(user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create all available MCP servers (Pipedream + local integrations).

    Args:
        user_id: User identifier for filtering enabled integrations

    Returns:
        Dictionary containing all available MCP servers
    """
    all_servers = {}

    # Get Pipedream MCP servers
    pipedream_servers = create_pipedream_mcp_servers(user_id)
    all_servers.update(pipedream_servers)

    # Get Twitter MCP server
    twitter_server = create_twitter_mcp_server(user_id)
    if twitter_server:
        all_servers["twitter_local"] = twitter_server

    logger.info(f"✅ Created {len(all_servers)} total MCP servers")
    return all_servers


# ============================================================================
# SPECIALIZED AGENTS - Following exact Agent pattern from improvements.md
# ============================================================================


def create_agents_with_memory(
    memory_manager: MemoryManager,
    workflow_id: str,
    mcp_servers: Optional[Dict[str, MCPServerSse]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Agent]:
    """
    Create agents with memory-enabled handoff callbacks.

    Args:
        memory_manager: Configured memory manager
        workflow_id: Current workflow session ID
        mcp_servers: Optional pre-created MCP servers
        user_id: User identifier for creating user-specific MCP servers

    Returns:
        Dictionary of configured agents with handoff callbacks
    """

    # Load prompts from files
    coordinator_prompt = load_prompt("coordinatorPrompt")
    meeting_prompt = load_prompt("meetingSchedulerPrompt")
    lead_qualifier_prompt = load_prompt("leadQualifierPrompt")

    # Create user-specific MCP servers if not provided (includes Twitter + Pipedream)
    if not mcp_servers and user_id:
        logger.info(f"Creating all MCP servers for user {user_id}")
        mcp_servers = create_all_mcp_servers(user_id)
    elif not mcp_servers:
        logger.warning(
            "No MCP servers provided and no user_id - agents will have no MCP tools"
        )
        mcp_servers = {}

    # Prepare MCP servers for specific agents
    meeting_mcp_servers = []
    if mcp_servers:
        # Meeting scheduler gets Calendly and Google Calendar MCP servers
        for server_name in ["calendly", "google_calendar"]:
            if server_name in mcp_servers:
                meeting_mcp_servers.append(mcp_servers[server_name])

    # Agent specialized in meeting scheduling
    meeting_scheduler_agent = Agent(
        name="Meeting Scheduling Specialist",
        instructions=f"""
            {RECOMMENDED_PROMPT_PREFIX}
            
            {meeting_prompt}
            
            When you receive a handoff, access previous context from your memory
            to personalize the meeting scheduling approach.
            
            You now have access to Calendly and Google Calendar tools via MCP servers.
            Use these to schedule meetings directly with prospects.
        """,
        tools=[get_crm_lead_data],
        mcp_servers=meeting_mcp_servers,
        output_type=MeetingScheduleResult,
    )

    # Agent specialized in creating leads from orchestrator conversations
    lead_qualifier_agent = Agent(
        name="Lead Creation Specialist",
        instructions=f"""
            {RECOMMENDED_PROMPT_PREFIX}
            
            {lead_qualifier_prompt}
            
            When you receive conversation context from the Coordinator,
            analyze it thoroughly and create structured leads in the database.
            Only hand off to Meeting Scheduling when a lead is highly qualified
            and ready for immediate meeting scheduling.
        """,
        tools=[
            get_crm_lead_data,
            analyze_lead_opportunity,
            update_lead_qualification,
        ],
        output_type=LeadAnalysis,
        handoffs=[
            handoff(
                agent=meeting_scheduler_agent,
                on_handoff=create_handoff_callback(
                    memory_manager=memory_manager,
                    from_agent_id="lead_qualifier_agent",
                    to_agent_id="meeting_scheduler_agent",
                    workflow_id=workflow_id,
                ),
                input_type=HandoffData,
                tool_description_override="Transfer highly qualified lead ready for meeting scheduling",
            )
        ],
    )

    # Prepare MCP servers for coordinator
    coordinator_mcp_servers = []
    if mcp_servers:
        # Coordinator gets CRM and email automation MCP servers
        for server_name in ["pipedrive", "salesforce", "zoho_crm", "sendgrid"]:
            if server_name in mcp_servers:
                coordinator_mcp_servers.append(mcp_servers[server_name])

    # Main coordinator agent - Enhanced with proactive communication capabilities
    coordinator_agent = Agent(
        name="PipeWise Coordinator",
        instructions=f"""
            {RECOMMENDED_PROMPT_PREFIX}
            
            {coordinator_prompt}
            
            You are the PRIMARY COMMUNICATION AGENT who INITIATES conversations with configured 
            targets and maintains ongoing relationships. Your role is to:
            
            1. PROACTIVELY reach out to configured communication targets
            2. BUILD RELATIONSHIPS through valuable interactions
            3. GENERATE INTEREST in services/products
            4. CREATE meaningful conversations that can become leads
            5. HANDOFF conversation context to Lead Creation Specialist when appropriate
            
            TWITTER CAPABILITIES:
            - Send direct messages to prospects using send_twitter_dm()
            - Get user information with get_twitter_user_info()
            - Reply to Twitter threads using reply_to_twitter_thread()
            
            When you create a meaningful conversation with a prospect, provide the full context 
            to the Lead Creation Specialist who will analyze it and create structured leads.
            
            You also have access to Pipedrive, Salesforce, Zoho CRM, and SendGrid tools via MCP servers.
            Use these to manage ongoing communications and track prospect interactions.
        """,
        tools=[
            # CRM and lead management tools
            get_crm_lead_data,
            analyze_lead_opportunity,
            update_lead_qualification,
            # Twitter communication tools
            send_twitter_dm,
            get_twitter_user_info,
            reply_to_twitter_thread,
        ],
        mcp_servers=coordinator_mcp_servers,
        output_type=CoordinatorResponse,
        handoffs=[
            handoff(
                agent=lead_qualifier_agent,
                on_handoff=create_handoff_callback(
                    memory_manager=memory_manager,
                    from_agent_id="coordinator_agent",
                    to_agent_id="lead_qualifier_agent",
                    workflow_id=workflow_id,
                ),
                input_type=HandoffData,
                tool_description_override="Transfer conversation context to Lead Creation Specialist",
            ),
            handoff(
                agent=meeting_scheduler_agent,
                on_handoff=create_handoff_callback(
                    memory_manager=memory_manager,
                    from_agent_id="coordinator_agent",
                    to_agent_id="meeting_scheduler_agent",
                    workflow_id=workflow_id,
                ),
                input_type=HandoffData,
                tool_description_override="Transfer to Meeting Scheduling Specialist for immediate scheduling",
            ),
        ],
    )

    return {
        "coordinator": coordinator_agent,
        "lead_qualifier": lead_qualifier_agent,
        "meeting_scheduler": meeting_scheduler_agent,
    }


# ============================================================================
# MODERN LEAD PROCESSOR - Replacing Legacy Architecture
# ============================================================================


class ModernLeadProcessor:
    """
    Modern lead processor using OpenAI AgentSDK with dual memory system
    """

    def __init__(self, tenant_context: Optional[TenantContext] = None):
        self.tenant_context = tenant_context
        self.db_client = SupabaseCRMClient()

        # Initialize memory manager if provided in context
        if tenant_context and tenant_context.memory_manager:
            self.memory_manager = tenant_context.memory_manager
        else:
            # Create default memory manager
            volatile_store = InMemoryStore(default_ttl=3600)  # 1 hour TTL
            persistent_store = SupabaseMemoryStore(self.db_client.client)
            self.memory_manager = MemoryManager(volatile_store, persistent_store)

        logger.info(
            "ModernLeadProcessor initialized with AgentSDK and dual memory system"
        )

    async def process_incoming_message(
        self, message_data: IncomingMessage
    ) -> Dict[str, Any]:
        """
        Process incoming message from email, Instagram, or Twitter with direct coordinator response
        """
        workflow_id = str(uuid.uuid4())

        try:
            logger.info(
                f"🚀 Processing incoming {message_data.channel} message from lead: {message_data.lead_id}"
            )

            # Store incoming message context in memory
            await self.memory_manager.save_both(
                agent_id="coordinator_agent",
                workflow_id=workflow_id,
                content={
                    "message_type": "incoming",
                    "channel": message_data.channel,
                    "message_content": message_data.message_content,
                    "lead_id": message_data.lead_id,
                    "channel_user_id": message_data.channel_user_id,
                    "channel_username": message_data.channel_username,
                    "context": message_data.context,
                },
                tags=["incoming_message", message_data.channel, "coordinator"],
                metadata={"type": "incoming_communication"},
            )

            # Create Pipedream MCP servers
            mcp_servers = create_pipedream_mcp_servers()

            # Create memory-enabled agents for this workflow
            agents = create_agents_with_memory(
                self.memory_manager, workflow_id, mcp_servers
            )
            coordinator = agents["coordinator"]

            # Build coordinated prompt with channel-specific context
            prompt = f"""
            INCOMING MESSAGE PROCESSING:
            
            Channel: {message_data.channel}
            Lead ID: {message_data.lead_id}
            Message: "{message_data.message_content}"
            """

            if message_data.channel_username:
                prompt += f"\nChannel Username: @{message_data.channel_username}"

            if message_data.context:
                prompt += f"\nAdditional Context: {message_data.context}"

            prompt += """
            
            INSTRUCTIONS:
            1. First, get the lead's information using get_crm_lead_data()
            2. Analyze the message content and lead profile
            3. Provide a direct, personalized response via the same channel
            4. Update lead qualification if new information is available
            5. Only handoff to specialists if you need specific technical support
            
            Respond directly to the prospect - you are their main point of contact!
            """

            # Store the processing request in memory
            await self.memory_manager.save_volatile(
                agent_id="coordinator_agent",
                workflow_id=workflow_id,
                content={
                    "step": "message_processing",
                    "prompt": prompt,
                    "lead_id": message_data.lead_id,
                    "channel": message_data.channel,
                },
                tags=["coordinator", "message_processing"],
            )

            # Run the coordinator workflow
            coordinator_result = await Runner.run(coordinator, prompt)

            logger.info(f"✅ Message processed: {coordinator_result}")

            # Store final result in memory
            final_result = {
                "status": "completed",
                "workflow_id": workflow_id,
                "lead_id": message_data.lead_id,
                "channel": message_data.channel,
                "result": coordinator_result.final_output
                if hasattr(coordinator_result, "final_output")
                else str(coordinator_result),
                "message_processed": True,
            }

            await self.memory_manager.save_both(
                agent_id="coordinator_agent",
                workflow_id=workflow_id,
                content=final_result,
                tags=["message_complete", "coordinator_response"],
                metadata={"type": "message_processing_completion"},
            )

            return final_result

        except Exception as e:
            logger.error(
                f"❌ Error processing {message_data.channel} message {workflow_id}: {str(e)}"
            )

            # Store error in memory for debugging
            try:
                await self.memory_manager.save_persistent(
                    agent_id="coordinator_agent",
                    workflow_id=workflow_id,
                    content={
                        "error": str(e),
                        "message_data": message_data.dict(),
                        "step": "message_processing_error",
                    },
                    tags=["message_error", "error"],
                    metadata={"type": "message_processing_error"},
                )
            except Exception as memory_error:
                logger.error(
                    f"Failed to store message processing error in memory: {memory_error}"
                )

            return {
                "status": "error",
                "error": str(e),
                "workflow_id": workflow_id,
                "message_processed": False,
            }

    async def process_lead_workflow(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete lead processing workflow using AgentSDK with memory system
        """
        workflow_id = str(uuid.uuid4())

        try:
            logger.info(
                f"🚀 Starting AgentSDK workflow {workflow_id} for lead: {lead_data.get('email')}"
            )

            # Create or get lead ID
            lead_id = lead_data.get("id") or str(uuid.uuid4())

            # Store initial workflow context in memory
            await self.memory_manager.save_both(
                agent_id="workflow_coordinator",
                workflow_id=workflow_id,
                content={
                    "workflow_started": True,
                    "lead_data": lead_data,
                    "lead_id": lead_id,
                    "tenant_context": self.tenant_context.__dict__
                    if self.tenant_context
                    else None,
                },
                tags=["workflow_start", "lead_processing"],
                metadata={"type": "workflow_initialization"},
            )

            # Create Pipedream MCP servers
            mcp_servers = create_pipedream_mcp_servers()

            # Create memory-enabled agents for this workflow
            agents = create_agents_with_memory(
                self.memory_manager, workflow_id, mcp_servers
            )
            coordinator = agents["coordinator"]

            # Step 1: Lead Qualification with memory context
            initial_prompt = f"""
            Process lead qualification for the following lead:
            Lead ID: {lead_id}
            Lead Data: {lead_data}
            
            Please use the handoff system to route this to the appropriate specialist.
            Provide clear reasoning for your handoff decisions.
            """

            # Store the initial request in memory
            await self.memory_manager.save_volatile(
                agent_id="coordinator_agent",
                workflow_id=workflow_id,
                content={
                    "step": "initial_request",
                    "prompt": initial_prompt,
                    "lead_id": lead_id,
                },
                tags=["coordinator", "initial_request"],
            )

            # Run the coordination workflow
            workflow_result = await Runner.run(coordinator, initial_prompt)

            logger.info(f"✅ Workflow completed: {workflow_result}")

            # Store final result in memory
            final_result = {
                "status": "completed",
                "workflow_id": workflow_id,
                "lead_id": lead_id,
                "result": workflow_result.final_output
                if hasattr(workflow_result, "final_output")
                else str(workflow_result),
                "workflow_completed": True,
            }

            await self.memory_manager.save_both(
                agent_id="workflow_coordinator",
                workflow_id=workflow_id,
                content=final_result,
                tags=["workflow_complete", "final_result"],
                metadata={"type": "workflow_completion"},
            )

            # Get workflow memory summary
            workflow_context = await self.memory_manager.get_workflow_context(
                workflow_id
            )
            final_result["memory_summary"] = {
                "volatile_memories": len(workflow_context["volatile"]),
                "persistent_memories": len(workflow_context["persistent"]),
                "handoffs_recorded": len(
                    [m for m in workflow_context["volatile"] if "handoff" in m.tags]
                ),
            }

            return final_result

        except Exception as e:
            logger.error(f"❌ Error in AgentSDK workflow {workflow_id}: {str(e)}")

            # Store error in memory for debugging
            try:
                await self.memory_manager.save_persistent(
                    agent_id="workflow_coordinator",
                    workflow_id=workflow_id,
                    content={
                        "error": str(e),
                        "lead_data": lead_data,
                        "step": "workflow_error",
                    },
                    tags=["workflow_error", "error"],
                    metadata={"type": "workflow_error"},
                )
            except Exception as memory_error:
                logger.error(
                    f"Failed to self.memory_manage workflow error in memory: {memory_error}"
                )

            return {
                "status": "error",
                "error": str(e),
                "workflow_id": workflow_id,
                "workflow_completed": False,
            }


# ============================================================================
# MODERN AGENTS COORDINATOR - Main Interface
# ============================================================================


class ModernAgents:
    """
    Main interface for the modern agent system with dual memory
    """

    def __init__(self, tenant_context: Optional[TenantContext] = None):
        # Initialize memory manager if not provided
        if not tenant_context or not tenant_context.memory_manager:
            db_client = SupabaseCRMClient()
            volatile_store = InMemoryStore(default_ttl=3600)  # 1 hour TTL
            persistent_store = SupabaseMemoryStore(db_client.client)
            memory_manager = MemoryManager(volatile_store, persistent_store)
        else:
            memory_manager = tenant_context.memory_manager

        self.tenant_context = tenant_context or TenantContext(
            tenant_id="default",
            user_id="system",
            is_premium=False,
            api_limits={"calls_per_hour": 100},
            features_enabled=[
                "basic_qualification",
                "meeting_scheduling",
            ],
            memory_manager=memory_manager,
        )

        # Ensure memory manager is set in context
        if not self.tenant_context.memory_manager:
            self.tenant_context.memory_manager = memory_manager

        self.processor = ModernLeadProcessor(self.tenant_context)
        logger.info(
            "ModernAgents system initialized with AgentSDK and dual memory system"
        )

    async def run_workflow(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete workflow using AgentSDK agents"""
        return await self.processor.process_lead_workflow(lead_data)

    def run_workflow_sync(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous version of run_workflow for compatibility.
        """
        import asyncio

        return asyncio.run(self.run_workflow(lead_data))

    async def qualify_lead_only(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run only lead qualification part of the workflow.
        """
        # Mock implementation for testing
        return {
            "status": "qualified",
            "lead_id": lead_data.get("id", "unknown"),
            "qualification_score": 85.0,
            "qualified": True,
        }

    async def contact_lead_only(
        self, lead_id: str, lead_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run only lead contact part of the workflow.
        """
        # Mock implementation for testing
        return {
            "status": "contacted",
            "lead_id": lead_id,
            "contact_method": "email",
            "contact_success": True,
        }

    async def schedule_meeting_only(
        self, lead_id: str, lead_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run only meeting scheduling part of the workflow.
        """
        # Mock implementation for testing
        return {
            "status": "meeting_scheduled",
            "lead_id": lead_id,
            "meeting_url": "https://calendly.com/test-meeting",
            "scheduled": True,
        }

    async def handle_incoming_message(self, message: IncomingMessage) -> Dict[str, Any]:
        """
        Handle incoming messages from various channels.
        """
        return await self.processor.process_incoming_message(message)

    async def handle_email_message(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming email messages.
        """
        message = IncomingMessage(
            lead_id=email_data.get("lead_id", "unknown"),
            channel="email",
            message_content=email_data.get("content", ""),
            context=email_data.get("context", {}),
        )
        return await self.handle_incoming_message(message)

    async def handle_instagram_message(
        self, instagram_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle incoming Instagram messages.
        """
        message = IncomingMessage(
            lead_id=instagram_data.get("lead_id", "unknown"),
            channel="instagram",
            channel_user_id=instagram_data.get("user_id"),
            channel_username=instagram_data.get("username"),
            message_content=instagram_data.get("content", ""),
            context=instagram_data.get("context", {}),
        )
        return await self.handle_incoming_message(message)

    async def handle_twitter_message(
        self, twitter_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle incoming Twitter messages.
        """
        message = IncomingMessage(
            lead_id=twitter_data.get("lead_id", "unknown"),
            channel="twitter",
            channel_user_id=twitter_data.get("user_id"),
            channel_username=twitter_data.get("username"),
            message_content=twitter_data.get("content", ""),
            context=twitter_data.get("context", {}),
        )
        return await self.handle_incoming_message(message)
