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

import logging
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from pydantic import BaseModel

from agents import Agent, Runner, function_tool, ModelSettings
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from app.supabase.supabase_client import SupabaseCRMClient
from .memory import MemoryManager, InMemoryStore, SupabaseMemoryStore

# Import MCP server management module
from .mcp.mcp_server_manager import (
    connect_mcp_servers,
    connect_mcp_servers_properly,
    get_all_mcp_servers_for_user,
)

# Import schemas
from app.schemas.lead_schema import LeadCreate
from app.api.oauth_integration_manager import OAuthIntegrationManager

# Configure logging to suppress MCP-related errors
logger = logging.getLogger(__name__)

# Suppress specific MCP-related loggers that may show Content-Type errors
mcp_loggers = [
    "mcp.client.sse",
    "mcp.client",
    "mcp",
    "agents.mcp",
    "httpx",  # May show HTTP errors from MCP calls
]

for logger_name in mcp_loggers:
    mcp_logger = logging.getLogger(logger_name)
    mcp_logger.setLevel(logging.CRITICAL)  # Only show critical errors
    mcp_logger.addFilter(
        lambda record: not any(
            phrase in record.getMessage().lower()
            for phrase in [
                "text/event-stream",
                "text/html",
                "content-type",
                "sse_reader",
                "expected response header",
            ]
        )
    )


# ============================================================================
# PROMPT LOADING FUNCTIONALITY
# ============================================================================


def load_agent_prompt(prompt_name: str) -> str:
    """
    Load agent prompt from file with fallback to default prompt.

    Args:
        prompt_name: Name of the prompt file (without .md extension)

    Returns:
        str: The prompt content or default prompt if file not found
    """
    # Use ai_agents directory instead of agents
    prompt_path = Path(__file__).parent / "prompts" / f"{prompt_name}.md"

    try:
        with open(prompt_path, "r", encoding="utf-8") as file:
            content = file.read()
            logger.info(f"✅ Loaded prompt from: {prompt_path}")
            return content
    except FileNotFoundError:
        logger.warning(f"⚠️ Prompt file not found: {prompt_path}")

        # Fallback prompts for each agent type
        fallback_prompts = {
            "coordinatorPrompt": """
You are a PipeWise Coordinator, specialized in lead management and coordination.

Your role is to:
1. Gather essential client information (name, email, company, needs, budget, timeline)
2. Assess if the client is interested in scheduling meetings
3. Coordinate with specialist agents when needed
4. Provide clear, professional communication

When processing leads:
- Ask for missing essential information
- Determine meeting interest before calling meetingScheduler
- Use leadGenerator for creating structured lead records
- Maintain professional and helpful communication

Always be thorough but efficient in your coordination.
            """,
            "leadAdministratorPrompt": """
You are a PipeWise Lead Administrator, specialized in managing leads and database operations.

Your role is to:
1. Create structured lead records from coordinator conversations
2. Manage lead qualification and database updates
3. Handle contact record creation and outreach tracking
4. Ensure data quality and completeness

When managing leads:
- Create leads using create_lead_in_database()
- Update qualifications using update_lead_qualification()
- Mark contacts using mark_lead_as_contacted()
- Extract all available contact information
- Assess lead quality and potential
- Create detailed lead profiles
- Ensure proper database formatting

Database Operations:
- Create conversation records in conversations table
- Create outreach message records in outreach_messages table  
- Create contact records in contacts table
- Handle UUID conversion for JSON operations
- Use admin client fallback for RLS policy issues

You work with the coordinator to maintain high-quality lead data and database operations.
            """,
            "meetingSchedulerPrompt": """
You are a PipeWise Meeting Scheduler, specialized in calendar integration and meeting coordination.

Your role is to:
1. Provide appropriate Calendly links based on client profiles
2. Generate personalized meeting presentation scripts
3. Coordinate with the coordinator for meeting setup
4. Ensure proper meeting scheduling workflow

When scheduling meetings:
- Analyze client profile and needs
- Provide relevant Calendly links
- Create personalized presentation scripts
- Support the coordinator with meeting logistics

Always provide professional and helpful meeting coordination.
            """,
        }

        return fallback_prompts.get(prompt_name, "You are a helpful AI assistant.")
    except Exception as e:
        logger.error(f"Error loading prompt {prompt_name}: {e}")
        return "You are a helpful AI assistant."


# ============================================================================
# TYPED CONTEXT AND MODELS - Following improvements.md pattern
# ============================================================================


class TenantContext:
    """Typed context for multi-tenant operations"""

    def __init__(
        self,
        tenant_id: str,
        user_id: str,
        is_premium: bool,
        api_limits: dict,
        features_enabled: list,
        memory_manager=None,
    ):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.is_premium = is_premium
        self.api_limits = api_limits
        self.features_enabled = features_enabled
        self.memory_manager = memory_manager


class LeadAnalysis(BaseModel):
    """Structured output for lead qualification - Following improvements.md pattern"""

    lead_id: str
    qualification_score: float
    qualified: bool
    key_factors: List[str]
    recommendations: List[str]
    risk_factors: List[str]
    opportunity_size: str


class MeetingScheduleResult(BaseModel):
    """Structured output for meeting scheduling"""

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
def create_lead_in_database(
    name: str,
    email: str,
    company: str = "",
    phone: str = "",
    source: str = "agent_processing",
) -> str:
    """
    Creates a new lead in the database.

    Args:
        name: Contact's full name
        email: Contact's email address
        company: Contact's company name
        phone: Contact's phone number (optional)
        source: Lead source identifier

    Returns:
        String with lead creation status and ID
    """
    try:
        db_client = SupabaseCRMClient()

        # Create lead directly without requiring test user
        lead_data = LeadCreate(
            name=name,
            email=email,
            company=company,
            phone=phone,
            source=source,
            metadata={"created_by": "ai_agent", "source": source},
        )

        logger.info(f"🔧 Creating lead: {name} ({email}) from {company}")

        # Create the lead
        created_lead = db_client.create_lead(lead_data)

        if created_lead:
            result = f"✅ Lead created successfully: {created_lead.name} (ID: {created_lead.id})"
            result += f"\n📧 Email: {created_lead.email}"
            result += f"\n🏢 Company: {created_lead.company}"
            result += f"\n📞 Phone: {created_lead.phone or 'Not provided'}"
            result += f"\n🔗 Source: {created_lead.source}"

            logger.info(f"✅ Lead created: {created_lead.id}")
            return result
        else:
            error_msg = "Failed to create lead - no response from database"
            logger.error(f"❌ {error_msg}")
            return f"❌ {error_msg}"

    except Exception as e:
        error_msg = f"Error creating lead: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"❌ {error_msg}"


@function_tool
def update_lead_qualification(
    lead_id: str, qualified: bool, reason: str, score: float = 0.0
) -> str:
    """
    Updates lead qualification status in CRM database.

    Args:
        lead_id: Lead identifier to update
        qualified: Whether the lead is qualified
        reason: Reason for qualification decision
        score: Qualification score (0-100)
    """
    try:
        from app.schemas.lead_schema import LeadUpdate

        db_client = SupabaseCRMClient()

        # First, try to get the lead by email if lead_id looks like an email
        lead = None
        if "@" in lead_id:
            lead = db_client.get_lead_by_email(lead_id)
        else:
            lead = db_client.get_lead(lead_id)

        if not lead or not lead.id:
            return f"Lead with identifier '{lead_id}' not found in database"

        # Prepare metadata with qualification details
        metadata = lead.metadata or {}
        metadata.update(
            {
                "qualification_reason": reason,
                "qualification_score": score,
                "qualified_at": db_client._get_current_timestamp(),
                "qualified_by": "ai_agent",
            }
        )

        # Update the lead
        updated_lead = db_client.update_lead(
            lead.id,
            LeadUpdate(
                qualified=qualified,
                status="qualified"
                if qualified
                else "new",  # Fixed: use "new" instead of "unqualified"
                metadata=metadata,
            ),
        )
        logger.info(
            f"Lead qualification updated: {updated_lead.id} - qualified={qualified}"
        )

        return f"Lead '{updated_lead.name}' qualification updated: qualified={qualified}, score={score}, reason='{reason}'"

    except Exception as e:
        logger.error(f"Error updating lead qualification: {e}")
        return f"Error updating lead qualification: {str(e)}"


@function_tool
def mark_lead_as_contacted(
    lead_id: str, contact_method: str, contact_details: str = ""
) -> str:
    """
    Marks a lead as contacted in the database and creates/updates contact record.

    Args:
        lead_id: Lead identifier
        contact_method: Method used to contact (email, twitter, instagram, phone)
        contact_details: Additional details about the contact attempt
    """
    try:
        logger.info("🔧 FUNCTION TOOL CALLED: mark_lead_as_contacted")
        logger.info(f"🔧 Parameters: lead_id={lead_id}, method={contact_method}")

        db_client = SupabaseCRMClient()

        # Get the lead
        lead = None
        if "@" in lead_id:
            lead = db_client.get_lead_by_email(lead_id)
        else:
            lead = db_client.get_lead(lead_id)

        if not lead or not lead.id:
            logger.warning(f"⚠️ Lead not found: {lead_id}")
            return f"Lead with identifier '{lead_id}' not found in database"

        # Mark as contacted using the dedicated method
        updated_lead = db_client.mark_lead_as_contacted(lead.id, contact_method)
        logger.info(
            f"✅ Lead marked as contacted: {updated_lead.id} via {contact_method}"
        )

        # Add contact details to metadata
        if contact_details:
            metadata = updated_lead.metadata or {}
            metadata["last_contact_details"] = contact_details

            from app.schemas.lead_schema import LeadUpdate

            db_client.update_lead(lead.id, LeadUpdate(metadata=metadata))
            logger.info("✅ Contact details added to metadata")

        # NOTE: Contact record creation is now handled by leadAdministrator via prompts
        logger.info(
            "ℹ️ Lead marked as contacted - contact record creation handled by leadAdministrator"
        )

        return f"✅ Lead '{updated_lead.name}' marked as contacted via {contact_method}"

    except Exception as e:
        logger.error(f"❌ Error marking lead as contacted: {e}", exc_info=True)
        return f"❌ Error marking lead as contacted: {str(e)}"


@function_tool
def get_leads_to_contact(status: str = "qualified", limit: int = 10) -> str:
    """
    Gets a list of leads that need to be contacted.

    Args:
        status: Lead status to filter by (qualified, new, etc.)
        limit: Maximum number of leads to return
    """
    try:
        db_client = SupabaseCRMClient()

        if status == "qualified":
            leads = db_client.get_qualified_leads()
        else:
            leads = db_client.list_leads(status=status, limit=limit)

        if not leads:
            return f"No leads found with status: {status}"

        result = f"Found {len(leads)} leads with status '{status}':\n\n"

        for lead in leads[:limit]:
            result += f"- {lead.name} ({lead.email})"
            if lead.company:
                result += f" from {lead.company}"
            result += f" | Status: {lead.status}"
            result += f" | Qualified: {lead.qualified}"
            result += f" | Contacted: {lead.contacted}\n"

        return result

    except Exception as e:
        logger.error(f"Error getting leads to contact: {e}")
        return f"Error getting leads: {str(e)}"


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

        # Get the lead
        lead = None
        if "@" in lead_id:
            lead = db_client.get_lead_by_email(lead_id)
        else:
            lead = db_client.get_lead(lead_id)

        if not lead or not lead.id:
            return f"Lead with identifier '{lead_id}' not found in database"

        # Schedule meeting using the dedicated method
        updated_lead = db_client.schedule_meeting_for_lead(
            lead.id, meeting_url, event_type
        )

        logger.info(f"Meeting scheduled for lead {updated_lead.id}: {meeting_url}")

        return f"Meeting scheduled for lead '{updated_lead.name}': {meeting_url}, type: {event_type}"

    except Exception as e:
        logger.error(f"Error scheduling meeting: {e}")
        return f"Error scheduling meeting: {str(e)}"


# ============================================================================
# MCP SERVERS SETUP - Following OpenAI Agents SDK Official Documentation
# ============================================================================

# NOTE: MCP server creation and management functions have been extracted to
# app.ai_agents.mcp.mcp_server_manager module for better organization.
#
# Available functions:
# - create_mcp_servers_for_user()
# - create_local_mcp_server()
# - connect_mcp_servers()
# - connect_mcp_servers_properly()
# - get_user_integration()
# - get_all_mcp_servers_for_user()
#
# These are imported at the top of this file for use by agent creation functions.


# ============================================================================
# UPDATED AGENT CREATION WITH PROPER MCP INTEGRATION
# ============================================================================


def create_agents_with_proper_mcp_integration(
    memory_manager: MemoryManager,
    workflow_id: str,
    user_id: Optional[str] = None,
) -> Dict[str, Agent]:
    """
    Create agents with proper MCP integration following OpenAI documentation.

    Args:
        memory_manager: Configured memory manager
        workflow_id: Current workflow session ID
        user_id: User identifier for MCP server filtering

    Returns:
        Dictionary of configured agents with MCP servers
    """
    # Load prompts from files
    coordinator_prompt = load_agent_prompt("coordinatorPrompt")
    meeting_prompt = load_agent_prompt("meetingSchedulerPrompt")

    # Create MCP servers for user (following OpenAI documentation)
    # Using the new MCP server manager module
    mcp_servers = get_all_mcp_servers_for_user(user_id)

    # Get OAuth integration info with proper error handling
    oauth_manager = OAuthIntegrationManager()
    enabled_integrations = {}
    try:
        enabled_integrations = (
            oauth_manager.get_enabled_integrations(user_id) if user_id else {}
        )
    except Exception as e:
        logger.warning(
            f"⚠️ Could not get enabled integrations: {e}. Continuing with empty list."
        )
        enabled_integrations = {}

    enabled_list = ", ".join(enabled_integrations.keys()) or "None"

    # CRITICAL FIX: Create empty MCP lists if no servers available
    # This prevents the "Server not initialized" error
    coordinator_mcp_servers = []
    meeting_mcp_servers = []

    # Only assign MCP servers if they exist and are valid
    if mcp_servers:
        logger.info(f"✅ Using {len(mcp_servers)} MCP servers for agents")
        # For now, assign all servers to all agents (can be refined later)
        coordinator_mcp_servers = mcp_servers
        meeting_mcp_servers = mcp_servers
    else:
        logger.info("ℹ️ No MCP servers available - agents will use local tools only")

    # Meeting Scheduler Agent with Calendar MCPs
    meeting_scheduler_agent = Agent(
        model="gpt-4.1",
        model_settings=ModelSettings(
            tool_choice="auto",
            parallel_tool_calls=True,
        ),
        name="Meeting Scheduling Specialist",
        instructions=f"""
            {RECOMMENDED_PROMPT_PREFIX}
            
            {meeting_prompt}
            
            You are a SPECIALIZED MEETING SCHEDULER with calendar integration capabilities.
            
            Your tools allow you to:
            - Review qualified leads using get_leads_to_contact()
            - Schedule meetings using schedule_meeting_for_lead()
            
            Core Functions:
            1. Review leads ready for meetings
            2. Provide appropriate Calendly links based on client profiles
            3. Schedule meetings in the system
            4. Coordinate meeting logistics
            
            Always update the database when completing actions!
            \n\nUser Enabled Integrations: {enabled_list}\nOnly use tools and MCP servers from enabled integrations. If an integration is not enabled, inform the user and do not attempt to use related tools.
        """,
        tools=[
            get_leads_to_contact,  # Changed from get_crm_lead_data
            schedule_meeting_for_lead,
        ],
        mcp_servers=meeting_mcp_servers,  # Use safe list
    )

    # Lead Administrator - Manages leads and database operations
    lead_administrator_agent = Agent(
        name="PipeWise Lead Administrator",
        model="gpt-4.1",
        model_settings=ModelSettings(
            tool_choice="auto",
            parallel_tool_calls=True,
        ),
        instructions=load_agent_prompt("leadAdministratorPrompt"),
        tools=[
            # Database operations only
            create_lead_in_database,
            update_lead_qualification,
            mark_lead_as_contacted,
        ],
        mcp_servers=[],  # Lead Administrator works with local database only
    )

    # Coordinator Agent (Communication focused)
    coordinator_agent = Agent(
        model="gpt-4.1",  # Changed from "o3" to avoid model errors
        model_settings=ModelSettings(
            tool_choice="auto",
            parallel_tool_calls=True,
        ),
        name="PipeWise Coordinator",
        instructions=f"""
            {RECOMMENDED_PROMPT_PREFIX}
            
            {coordinator_prompt}
            
            You are the PRIMARY COORDINATOR with multi-channel communication capabilities.
            
            Your MCP servers provide direct access to:
            - SendGrid for email automation (if available)
            - Other communication platforms as configured
            
            Core Functions:
            1. Process incoming messages from prospects
            2. Initiate outreach campaigns
            3. Coordinate with specialists through handoffs
            4. Manage complete workflows
            
            Database Integration:
            - Use mark_lead_as_contacted() for contact tracking
            - DO NOT create or qualify leads - that's the leadAdministrator's job
            
            Communication Tools:
            - Twitter: Use MCP servers for social media outreach (if available)
            - Email: Use SendGrid MCP tools for professional outreach (if available)
            
            MCP Integration:
            - Check if MCP tools are available before using them
            - If no MCP servers are available, inform the user about the limitation
            - Focus on database operations and coordination when MCP is unavailable
            
            IMPORTANT: Contact prospects first, then use handoffs to specialists!
            \n\nUser Enabled Integrations: {enabled_list}\nOnly use tools and MCP servers from enabled integrations. If an integration is not enabled, inform the user and do not attempt to use related tools.
        """,
        tools=[
            # Essential database operations only
            mark_lead_as_contacted,
            # Communication through MCP servers (if available)
        ],
        mcp_servers=coordinator_mcp_servers,  # Use safe list
    )

    agents_dict = {
        "coordinator": coordinator_agent,
        "lead_administrator": lead_administrator_agent,  # Changed from lead_generator_agent
        "meeting_scheduler": meeting_scheduler_agent,
    }

    logger.info(
        f"✅ Created {len(agents_dict)} agents with {len(mcp_servers)} MCP servers"
    )
    return agents_dict


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

            # Create MCP servers using new function
            mcp_servers = get_all_mcp_servers_for_user()

            # Connect MCP servers automatically (but don't fail if they don't connect)
            connected_mcps = []
            if mcp_servers:
                try:
                    connected_mcps = await connect_mcp_servers_properly(mcp_servers)
                    if connected_mcps:
                        logger.info(
                            f"✅ Connected {len(connected_mcps)} MCP servers for incoming message"
                        )
                    else:
                        logger.info(
                            "⚪ No MCP servers connected for incoming message, using local tools only"
                        )
                except Exception as e:
                    logger.warning(f"⚠️ MCP connection failed for incoming message: {e}")
                    connected_mcps = []

            # Create memory-enabled agents for this workflow (use connected MCPs only)
            agents = create_agents_with_proper_mcp_integration(
                self.memory_manager, workflow_id
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

    async def create_workflow_tools_integration(
        self, workflow_id: str, user_id: str
    ) -> Dict[str, Any]:
        """
        Crea herramientas de integración para comunicarse con el frontend via AI SDK tools.
        """
        return {
            "start_workflow": {
                "workflowId": workflow_id,
                "agentName": "PipeWise Lead Processor",
                "leadId": user_id,
                "initialTasks": [
                    {
                        "id": "qualification",
                        "title": "Lead Qualification",
                        "description": "Analyzing lead quality and potential",
                        "status": "pending",
                        "priority": "high",
                        "tools": [
                            "analyze_lead_opportunity",
                            "update_lead_qualification",
                        ],
                    },
                    {
                        "id": "communication",
                        "title": "Lead Communication",
                        "description": "Reaching out to qualified leads",
                        "status": "pending",
                        "priority": "medium",
                        "tools": ["send_twitter_dm", "send_email"],
                    },
                    {
                        "id": "scheduling",
                        "title": "Meeting Scheduling",
                        "description": "Scheduling meetings with interested leads",
                        "status": "pending",
                        "priority": "medium",
                        "tools": ["schedule_meeting_for_lead"],
                    },
                ],
            },
            "update_workflow": {
                "workflowId": workflow_id,
                "currentAgent": "Lead Generator",
                "currentStep": "Generating leads...",
                "progress": 25,
                "status": "in-progress",
                "tasks": [],  # Se actualizará dinámicamente
            },
        }

    async def process_lead_workflow(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete lead processing workflow using AgentSDK with database integration.

        Handles two main scenarios:
        1. Processing a list of prospects provided by user for outreach
        2. Processing incoming messages from prospects
        """
        workflow_id = str(uuid.uuid4())
        user_id = self.tenant_context.user_id if self.tenant_context else "system"

        try:
            # Determine workflow type based on input data
            workflow_type = lead_data.get("workflow_type", "single_lead")

            # ADD EXTENSIVE DEBUG LOGGING
            logger.info(
                f"🔧 DEBUG: process_lead_workflow called with workflow_type: {workflow_type}"
            )
            logger.info(f"🔧 DEBUG: Lead data keys: {list(lead_data.keys())}")
            logger.info(f"🔧 DEBUG: Workflow ID: {workflow_id}")
            logger.info(f"🔧 DEBUG: User ID: {user_id}")
            logger.info(
                f"🔧 DEBUG: Debug mode flag: {lead_data.get('debug_mode', False)}"
            )
            logger.info(
                f"🔧 DEBUG: Force real workflow flag: {lead_data.get('force_real_workflow', False)}"
            )

            logger.info(
                f"🚀 Starting REAL {workflow_type} workflow {workflow_id} for: {lead_data.get('email', lead_data.get('prospect_list', 'unknown'))}"
            )

            # Verify we're NOT in simplified mode
            logger.info("🔧 DEBUG: This is the REAL AGENT WORKFLOW - NOT SIMPLIFIED")

            # Store initial workflow context in memory
            await self.memory_manager.save_both(
                agent_id="workflow_manager",
                workflow_id=workflow_id,
                content={
                    "workflow_type": workflow_type,
                    "lead_data": lead_data,
                    "user_id": user_id,
                    "status": "started",
                    "debug_mode": lead_data.get("debug_mode", False),
                    "real_workflow": True,
                },
                tags=["workflow_start", workflow_type, "real_workflow"],
                metadata={"type": "workflow_initialization"},
            )

            logger.info("🔧 DEBUG: Memory saved, about to create MCP servers")

            # Create MCP servers for user integrations
            mcp_servers = get_all_mcp_servers_for_user(user_id)
            logger.info(f"🔧 DEBUG: Created {len(mcp_servers)} MCP servers")

            # Connect MCP servers automatically (but don't fail if they don't connect)
            connected_mcps = []
            if mcp_servers:
                try:
                    logger.info("🔧 DEBUG: Attempting to connect MCP servers...")
                    connected_result = await connect_mcp_servers(mcp_servers)
                    connected_mcps = connected_result.get("servers", [])
                    if connected_mcps:
                        logger.info(
                            f"✅ Connected {len(connected_mcps)} MCP servers successfully"
                        )
                    else:
                        logger.info(
                            "⚪ No MCP servers connected, continuing with local tools only"
                        )
                except Exception as e:
                    logger.warning(
                        f"⚠️ MCP connection failed, continuing without external integrations: {e}"
                    )
                    connected_mcps = []

            logger.info("🔧 DEBUG: About to create agents with memory")

            # CRITICAL FIX: Pass only connected MCP servers to agents
            # This prevents the "Server not initialized" error
            def create_agents_with_connected_mcps():
                """Create agents with only properly connected MCP servers"""
                # Load prompts from files
                coordinator_prompt = load_agent_prompt("coordinatorPrompt")
                meeting_prompt = load_agent_prompt("meetingSchedulerPrompt")

                # Get OAuth integration info with proper error handling
                oauth_manager = OAuthIntegrationManager()
                enabled_integrations = {}
                try:
                    enabled_integrations = (
                        oauth_manager.get_enabled_integrations(user_id)
                        if user_id
                        else {}
                    )
                except Exception as e:
                    logger.warning(
                        f"⚠️ Could not get enabled integrations: {e}. Continuing with empty list."
                    )
                    enabled_integrations = {}

                enabled_list = ", ".join(enabled_integrations.keys()) or "None"

                # Use only connected MCP servers
                safe_mcp_servers = connected_mcps if connected_mcps else []
                logger.info(
                    f"🔧 Using {len(safe_mcp_servers)} connected MCP servers for agents"
                )

                # Meeting Scheduler Agent
                meeting_scheduler_agent = Agent(
                    model="gpt-4.1",
                    model_settings=ModelSettings(
                        tool_choice="auto",
                        parallel_tool_calls=True,
                    ),
                    name="Meeting Scheduling Specialist",
                    instructions=f"""
                        {RECOMMENDED_PROMPT_PREFIX}
                        
                        {meeting_prompt}
                        
                        You are a SPECIALIZED MEETING SCHEDULER with calendar integration capabilities.
                        
                        Your tools allow you to:
                        - Review qualified leads using get_leads_to_contact()
                        - Schedule meetings using schedule_meeting_for_lead()
                        
                        Core Functions:
                        1. Review leads ready for meetings
                        2. Provide appropriate Calendly links based on client profiles
                        3. Schedule meetings in the system
                        4. Coordinate meeting logistics
                        
                        Always update the database when completing actions!
                        \n\nUser Enabled Integrations: {enabled_list}\nOnly use tools and MCP servers from enabled integrations. If an integration is not enabled, inform the user and do not attempt to use related tools.
                    """,
                    tools=[
                        get_leads_to_contact,
                        schedule_meeting_for_lead,
                    ],
                    mcp_servers=safe_mcp_servers,  # Use only connected servers
                )

                # Lead Administrator - Manages leads and database operations
                lead_administrator_agent = Agent(
                    name="PipeWise Lead Administrator",
                    model="gpt-4.1",
                    model_settings=ModelSettings(
                        tool_choice="auto",
                        parallel_tool_calls=True,
                    ),
                    instructions=load_agent_prompt("leadAdministratorPrompt"),
                    tools=[
                        # Database operations only
                        create_lead_in_database,
                        update_lead_qualification,
                        mark_lead_as_contacted,
                    ],
                    mcp_servers=[],  # Lead Administrator works with local database only
                )

                # Coordinator Agent (Communication focused)
                coordinator_agent = Agent(
                    model="gpt-4.1",
                    model_settings=ModelSettings(
                        tool_choice="auto",
                        parallel_tool_calls=True,
                    ),
                    name="PipeWise Coordinator",
                    instructions=f"""
                        {RECOMMENDED_PROMPT_PREFIX}
                        
                        {coordinator_prompt}
                        
                        You are the PRIMARY COORDINATOR with multi-channel communication capabilities.
                        
                        Available MCP Servers: {len(safe_mcp_servers)}
                        
                        Core Functions:
                        1. Process incoming messages from prospects
                        2. Initiate outreach campaigns (if MCP servers available)
                        3. Coordinate with specialists through handoffs
                        4. Manage complete workflows
                        
                        Database Integration:
                        - Use mark_lead_as_contacted() for contact tracking
                        - DO NOT create or qualify leads - that's the leadAdministrator's job
                        
                        Communication Tools:
                        - Twitter: Use MCP servers for social media outreach (if available)
                        - Email: Use SendGrid MCP tools for professional outreach (if available)
                        
                        MCP Integration:
                        - Check if MCP tools are available before using them
                        - If no MCP servers are available, inform the user about the limitation
                        - Focus on database operations and coordination when MCP is unavailable
                        
                        IMPORTANT: Contact prospects first, then use handoffs to specialists!
                        \n\nUser Enabled Integrations: {enabled_list}\nOnly use tools and MCP servers from enabled integrations. If an integration is not enabled, inform the user and do not attempt to use related tools.
                    """,
                    tools=[
                        # Essential database operations only
                        mark_lead_as_contacted,
                        # Communication through MCP servers (if available)
                    ],
                    mcp_servers=safe_mcp_servers,  # Use only connected servers
                )

                return {
                    "coordinator": coordinator_agent,
                    "lead_administrator": lead_administrator_agent,
                    "meeting_scheduler": meeting_scheduler_agent,
                }

            # Create agents with properly connected MCP servers
            agents = create_agents_with_connected_mcps()

            logger.info(
                f"🔧 DEBUG: Created {len(agents)} agents: {list(agents.keys())}"
            )

            coordinator = agents["coordinator"]
            logger.info(f"🔧 DEBUG: Got coordinator agent: {coordinator.name}")

            # Build workflow prompt with lead data context
            logger.info(f"🔧 DEBUG: Building prompt for workflow type: {workflow_type}")

            # Use the coordinator's comprehensive prompt with lead data context
            lead_context = f"""
            WORKFLOW CONTEXT:
            - Workflow ID: {workflow_id}
            - Workflow Type: {workflow_type}
            - Lead Data: {lead_data}
            
            INSTRUCTIONS: Follow your coordinator prompt guidelines for {workflow_type} processing.
            """

            prompt = lead_context
            logger.info("🔧 DEBUG: Built workflow prompt with context")

            # Store the processing request in memory
            await self.memory_manager.save_volatile(
                agent_id="coordinator",
                workflow_id=workflow_id,
                content={
                    "step": "workflow_processing",
                    "prompt": prompt,
                    "lead_data": lead_data,
                    "agents_available": list(agents.keys()),
                    "real_workflow": True,
                },
                tags=["coordinator", workflow_type, "real_workflow"],
            )

            logger.info(
                f"🔧 DEBUG: About to run coordinator with prompt length: {len(prompt)}"
            )
            logger.info("🔧 DEBUG: RUNNING REAL AGENT WORKFLOW - NOT SIMPLIFIED")

            # Run the coordinator workflow with full agent capabilities
            from agents import Runner

            logger.info("🔧 DEBUG: Calling Runner.run with coordinator agent")
            coordinator_result = await Runner.run(coordinator, prompt)

            logger.info("🔧 DEBUG: Runner.run completed successfully")
            logger.info(
                f"✅ REAL {workflow_type} workflow completed: {coordinator_result}"
            )

            # Store final result in memory
            final_result = {
                "status": "completed",
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "lead_id": lead_data.get("id", workflow_id),
                "result": coordinator_result.final_output
                if hasattr(coordinator_result, "final_output")
                else str(coordinator_result),
                "workflow_completed": True,
                "agents_used": list(agents.keys()),
                "mcp_servers_available": len(mcp_servers),
                "mcp_servers_connected": len(connected_mcps),
                "real_workflow": True,
                "debug_info": {
                    "coordinator_result_type": str(type(coordinator_result)),
                    "has_final_output": hasattr(coordinator_result, "final_output"),
                    "debug_mode": lead_data.get("debug_mode", False),
                },
            }

            await self.memory_manager.save_both(
                agent_id="workflow_manager",
                workflow_id=workflow_id,
                content=final_result,
                tags=["workflow_complete", workflow_type, "real_workflow"],
                metadata={"type": "workflow_completion"},
            )

            logger.info("🔧 DEBUG: Final result prepared and saved to memory")

            return final_result

        except Exception as e:
            logger.error(
                f"❌ Error in {workflow_type} workflow {workflow_id}: {str(e)}",
                exc_info=True,
            )

            # Store error in memory for debugging
            try:
                await self.memory_manager.save_persistent(
                    agent_id="workflow_manager",
                    workflow_id=workflow_id,
                    content={
                        "error": str(e),
                        "lead_data": lead_data,
                        "step": "workflow_error",
                        "user_id": user_id,
                    },
                    tags=["workflow_error", "error"],
                    metadata={"type": "workflow_error"},
                )
            except Exception as memory_error:
                logger.error(
                    f"Failed to store workflow error in memory: {memory_error}"
                )

            return {
                "status": "error",
                "error": str(e),
                "workflow_id": workflow_id,
                "workflow_completed": False,
                "fallback_message": "I encountered an issue processing this workflow, but I've saved the information for later review.",
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
