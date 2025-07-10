"""
Integration tests for complete agent workflows with MCP services.

This module tests full agent workflows from start to finish, including:
- Complete lead nurturing workflows
- Meeting scheduling and follow-up workflows
- Multi-agent coordination scenarios
- Real-world business process automation
"""

import pytest
import asyncio
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from unittest.mock import patch, AsyncMock

from app.ai_agents.agents import create_agents_with_proper_mcp_integration
from app.ai_agents.mcp.agent_mcp_factory import AgentMCPFactory, AgentType
from app.ai_agents.mcp.meeting_scheduler_mcp_integration import (
    schedule_meeting_with_mcp,
)
from app.ai_agents.mcp.lead_administrator_mcp_integration import (
    mark_lead_as_contacted_with_mcp,
)
from app.ai_agents.mcp.error_handler import MCPConnectionError, MCPOperationError
from app.models.lead import Lead
from app.schemas.lead_schema import LeadCreate, LeadUpdate


# Test environment configuration
TEST_USER_ID = os.getenv("TEST_USER_ID", "integration-test-user")
TEST_LEAD_EMAIL = "test.lead@example.com"
TEST_LEAD_NAME = "John Doe"
TEST_COMPANY_NAME = "TechCorp Solutions"

# Skip if integration environment not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require RUN_INTEGRATION_TESTS=1",
)


class TestCoordinatorAgentWorkflow:
    """Test complete Coordinator Agent workflows."""

    @pytest.fixture
    async def coordinator_agent(self) -> Dict[str, Any]:
        """Create Coordinator Agent with MCP integration."""
        agents = await create_agents_with_proper_mcp_integration(TEST_USER_ID)
        return agents["coordinator"]

    @pytest.fixture
    def sample_lead_data(self) -> Dict[str, Any]:
        """Create sample lead data for testing."""
        return {
            "name": TEST_LEAD_NAME,
            "email": TEST_LEAD_EMAIL,
            "company": TEST_COMPANY_NAME,
            "phone": "+1-555-0123",
            "industry": "Technology",
            "company_size": "50-100",
            "budget": 25000,
            "pain_points": ["Manual processes", "Scalability issues"],
            "source": "website_form",
        }

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_lead_welcome_workflow(
        self, coordinator_agent: Dict[str, Any], sample_lead_data: Dict[str, Any]
    ) -> None:
        """Test complete lead welcome workflow with email and social media."""
        # Arrange
        lead = LeadCreate(**sample_lead_data)

        # Act - Execute welcome workflow
        workflow_result = await coordinator_agent["agent"].execute_workflow(
            "lead_welcome_sequence",
            {
                "lead": lead.dict(),
                "workflow_type": "new_lead_welcome",
                "personalization_level": "high",
            },
        )

        # Assert - Workflow executed successfully
        assert workflow_result["success"] is True
        assert "email_sent" in workflow_result["actions_completed"]
        assert "social_media_research" in workflow_result["actions_completed"]

        # Verify email was sent via SendGrid MCP
        email_results = workflow_result["actions_completed"]["email_sent"]
        assert email_results["service"] == "sendgrid"
        assert email_results["to"] == TEST_LEAD_EMAIL
        assert "welcome" in email_results["subject"].lower()

        # Verify social media research via Twitter MCP
        social_results = workflow_result["actions_completed"]["social_media_research"]
        assert social_results["service"] == "twitter"
        assert social_results["company_found"] in [
            True,
            False,
        ]  # May or may not find company

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_lead_nurturing_sequence(
        self, coordinator_agent: Dict[str, Any], sample_lead_data: Dict[str, Any]
    ) -> None:
        """Test multi-step lead nurturing sequence."""
        # Arrange
        lead = LeadCreate(**sample_lead_data)

        # Act - Execute nurturing sequence (Day 1, 3, 7 emails)
        nurturing_result = await coordinator_agent["agent"].execute_workflow(
            "lead_nurturing_sequence",
            {
                "lead": lead.dict(),
                "sequence_type": "tech_company_nurturing",
                "duration_days": 7,
                "touchpoints": ["email", "social_media", "content_sharing"],
            },
        )

        # Assert - Multi-step sequence completed
        assert nurturing_result["success"] is True
        assert nurturing_result["sequence_length"] >= 3
        assert len(nurturing_result["emails_sent"]) >= 3

        # Verify email sequence progression
        emails = nurturing_result["emails_sent"]
        assert "day_1" in emails
        assert "day_3" in emails
        assert "day_7" in emails

        # Verify content personalization
        day_1_email = emails["day_1"]
        assert TEST_COMPANY_NAME in day_1_email["content"]
        assert any(
            pain_point in day_1_email["content"]
            for pain_point in sample_lead_data["pain_points"]
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_social_media_outreach_workflow(
        self, coordinator_agent: Dict[str, Any], sample_lead_data: Dict[str, Any]
    ) -> None:
        """Test social media outreach and engagement workflow."""
        # Arrange
        lead = LeadCreate(**sample_lead_data)

        # Act - Execute social media outreach
        social_result = await coordinator_agent["agent"].execute_workflow(
            "social_media_outreach",
            {
                "lead": lead.dict(),
                "platforms": ["twitter", "linkedin"],
                "outreach_type": "company_engagement",
                "follow_company": True,
                "engage_with_content": True,
            },
        )

        # Assert - Social outreach completed
        assert social_result["success"] is True
        assert "twitter_actions" in social_result

        twitter_actions = social_result["twitter_actions"]
        assert twitter_actions["company_followed"] in [True, False]
        assert twitter_actions["content_liked"] >= 0
        assert "engagement_score" in twitter_actions

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_coordinator_error_recovery(
        self, coordinator_agent: Dict[str, Any], sample_lead_data: Dict[str, Any]
    ) -> None:
        """Test Coordinator Agent error recovery and fallback mechanisms."""
        # Arrange
        lead = LeadCreate(**sample_lead_data)

        # Simulate SendGrid service failure
        with patch(
            "app.ai_agents.tools.sendgrid_mcp.SendGridMCP.send_email"
        ) as mock_email:
            mock_email.side_effect = MCPConnectionError("SendGrid service unavailable")

            # Act - Execute workflow with service failure
            result = await coordinator_agent["agent"].execute_workflow(
                "lead_welcome_sequence", {"lead": lead.dict(), "enable_fallbacks": True}
            )

            # Assert - Should handle failure gracefully with fallbacks
            assert result["success"] is True  # Overall workflow succeeds
            assert result["email_sent"] is False  # Primary email failed
            assert result["fallback_used"] is True  # Fallback mechanism activated
            assert (
                "social_media_research" in result["actions_completed"]
            )  # Other actions still work


class TestMeetingSchedulerAgentWorkflow:
    """Test complete Meeting Scheduler Agent workflows."""

    @pytest.fixture
    async def scheduler_agent(self) -> Dict[str, Any]:
        """Create Meeting Scheduler Agent with MCP integration."""
        agents = await create_agents_with_proper_mcp_integration(TEST_USER_ID)
        return agents["meeting_scheduler"]

    @pytest.fixture
    def sample_meeting_request(self) -> Dict[str, Any]:
        """Create sample meeting request data."""
        return {
            "lead_email": TEST_LEAD_EMAIL,
            "lead_name": TEST_LEAD_NAME,
            "company": TEST_COMPANY_NAME,
            "meeting_type": "discovery_call",
            "duration": 30,
            "preferred_times": [
                (datetime.now() + timedelta(days=2, hours=10)).isoformat(),
                (datetime.now() + timedelta(days=3, hours=14)).isoformat(),
                (datetime.now() + timedelta(days=4, hours=11)).isoformat(),
            ],
            "timezone": "America/New_York",
            "notes": "Interested in automation solutions for their tech stack",
        }

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_meeting_scheduling_workflow(
        self, scheduler_agent: Dict[str, Any], sample_meeting_request: Dict[str, Any]
    ) -> None:
        """Test complete meeting scheduling workflow."""
        # Act - Execute meeting scheduling
        scheduling_result = await schedule_meeting_with_mcp(
            user_id=TEST_USER_ID,
            lead_email=sample_meeting_request["lead_email"],
            meeting_type=sample_meeting_request["meeting_type"],
            duration=sample_meeting_request["duration"],
            preferred_times=sample_meeting_request["preferred_times"],
            notes=sample_meeting_request["notes"],
        )

        # Assert - Meeting scheduled successfully
        assert scheduling_result["success"] is True
        assert "meeting_url" in scheduling_result
        assert "calendar_event_id" in scheduling_result

        # Verify Calendly integration
        assert "calendly.com" in scheduling_result["meeting_url"]
        assert scheduling_result["calendly_event_created"] is True

        # Verify Google Calendar integration
        assert scheduling_result["google_calendar_synced"] is True
        assert scheduling_result["calendar_event_id"] is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_meeting_confirmation_workflow(
        self, scheduler_agent: Dict[str, Any], sample_meeting_request: Dict[str, Any]
    ) -> None:
        """Test meeting confirmation and reminder workflow."""
        # Arrange - First schedule a meeting
        scheduling_result = await schedule_meeting_with_mcp(
            user_id=TEST_USER_ID,
            lead_email=sample_meeting_request["lead_email"],
            meeting_type=sample_meeting_request["meeting_type"],
            duration=30,
            preferred_times=sample_meeting_request["preferred_times"][:1],
        )

        meeting_id = scheduling_result["meeting_id"]

        # Act - Execute confirmation workflow
        confirmation_result = await scheduler_agent["agent"].execute_workflow(
            "meeting_confirmation_sequence",
            {
                "meeting_id": meeting_id,
                "lead_email": sample_meeting_request["lead_email"],
                "lead_name": sample_meeting_request["lead_name"],
                "send_confirmation": True,
                "schedule_reminders": True,
            },
        )

        # Assert - Confirmation workflow completed
        assert confirmation_result["success"] is True
        assert confirmation_result["confirmation_sent"] is True
        assert confirmation_result["reminders_scheduled"] is True
        assert len(confirmation_result["reminder_times"]) >= 2  # 24h and 1h reminders

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_meeting_rescheduling_workflow(
        self, scheduler_agent: Dict[str, Any], sample_meeting_request: Dict[str, Any]
    ) -> None:
        """Test meeting rescheduling workflow."""
        # Arrange - Schedule initial meeting
        initial_meeting = await schedule_meeting_with_mcp(
            user_id=TEST_USER_ID,
            lead_email=sample_meeting_request["lead_email"],
            meeting_type=sample_meeting_request["meeting_type"],
            duration=30,
            preferred_times=sample_meeting_request["preferred_times"][:1],
        )

        meeting_id = initial_meeting["meeting_id"]
        new_time = (datetime.now() + timedelta(days=5, hours=15)).isoformat()

        # Act - Execute rescheduling
        reschedule_result = await scheduler_agent["agent"].execute_workflow(
            "reschedule_meeting",
            {
                "meeting_id": meeting_id,
                "new_time": new_time,
                "reason": "Lead requested different time",
                "notify_attendees": True,
            },
        )

        # Assert - Meeting rescheduled successfully
        assert reschedule_result["success"] is True
        assert reschedule_result["calendly_updated"] is True
        assert reschedule_result["google_calendar_updated"] is True
        assert reschedule_result["notifications_sent"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_availability_checking_workflow(
        self, scheduler_agent: Dict[str, Any]
    ) -> None:
        """Test availability checking across multiple calendar services."""
        # Arrange
        check_dates = [
            (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(1, 8)  # Next 7 days
        ]

        # Act - Check availability
        availability_result = await scheduler_agent["agent"].execute_workflow(
            "check_availability",
            {
                "dates": check_dates,
                "time_slots": ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"],
                "duration": 30,
                "timezone": "America/New_York",
            },
        )

        # Assert - Availability checked successfully
        assert availability_result["success"] is True
        assert len(availability_result["available_slots"]) > 0

        for slot in availability_result["available_slots"]:
            assert "date" in slot
            assert "time" in slot
            assert "calendly_available" in slot
            assert "google_calendar_available" in slot


class TestLeadAdministratorAgentWorkflow:
    """Test complete Lead Administrator Agent workflows."""

    @pytest.fixture
    async def admin_agent(self) -> Dict[str, Any]:
        """Create Lead Administrator Agent with MCP integration."""
        agents = await create_agents_with_proper_mcp_integration(TEST_USER_ID)
        return agents["lead_administrator"]

    @pytest.fixture
    def sample_lead_update(self) -> Dict[str, Any]:
        """Create sample lead update data."""
        return {
            "lead_id": "test-lead-123",
            "name": TEST_LEAD_NAME,
            "email": TEST_LEAD_EMAIL,
            "company": TEST_COMPANY_NAME,
            "status": "contacted",
            "stage": "discovery",
            "contact_method": "email",
            "notes": "Initial outreach sent, lead responded positively",
            "next_action": "schedule_discovery_call",
            "crm_systems": ["pipedrive", "salesforce"],
        }

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_lead_update_workflow(
        self, admin_agent: Dict[str, Any], sample_lead_update: Dict[str, Any]
    ) -> None:
        """Test complete lead update workflow across multiple CRM systems."""
        # Act - Execute lead update
        update_result = await mark_lead_as_contacted_with_mcp(
            user_id=TEST_USER_ID,
            lead_id=sample_lead_update["lead_id"],
            contact_method=sample_lead_update["contact_method"],
            notes=sample_lead_update["notes"],
            crm_systems=sample_lead_update["crm_systems"],
        )

        # Assert - Lead updated across all CRM systems
        assert update_result["success"] is True
        assert "pipedrive" in update_result["crm_updates"]
        assert "salesforce" in update_result["crm_updates"]

        # Verify Pipedrive update
        pipedrive_result = update_result["crm_updates"]["pipedrive"]
        assert pipedrive_result["updated"] is True
        assert pipedrive_result["deal_id"] is not None

        # Verify Salesforce update
        salesforce_result = update_result["crm_updates"]["salesforce"]
        assert salesforce_result["updated"] is True
        assert salesforce_result["lead_id"] is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_lead_scoring_workflow(
        self, admin_agent: Dict[str, Any], sample_lead_update: Dict[str, Any]
    ) -> None:
        """Test lead scoring and qualification workflow."""
        # Arrange
        lead_data = {
            **sample_lead_update,
            "company_size": "100-500",
            "budget": 50000,
            "decision_timeframe": "3_months",
            "pain_points": ["manual_processes", "scalability", "integration"],
            "engagement_score": 85,
        }

        # Act - Execute lead scoring
        scoring_result = await admin_agent["agent"].execute_workflow(
            "lead_scoring_and_qualification",
            {"lead": lead_data, "scoring_model": "enterprise_saas", "update_crm": True},
        )

        # Assert - Lead scored and qualified
        assert scoring_result["success"] is True
        assert "lead_score" in scoring_result
        assert "qualification_status" in scoring_result
        assert scoring_result["lead_score"] >= 0
        assert scoring_result["qualification_status"] in [
            "qualified",
            "unqualified",
            "nurture",
        ]

        # Verify CRM updates with score
        assert scoring_result["crm_updated"] is True
        assert scoring_result["score_synced_to_crm"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_lead_assignment_workflow(
        self, admin_agent: Dict[str, Any], sample_lead_update: Dict[str, Any]
    ) -> None:
        """Test lead assignment and routing workflow."""
        # Arrange
        assignment_criteria = {
            "lead": sample_lead_update,
            "assignment_rules": {
                "territory": "east_coast",
                "industry": "technology",
                "deal_size": "enterprise",
            },
            "sales_team": [
                {
                    "id": "rep_1",
                    "name": "Alice Johnson",
                    "territory": "east_coast",
                    "specialization": "enterprise",
                },
                {
                    "id": "rep_2",
                    "name": "Bob Smith",
                    "territory": "west_coast",
                    "specialization": "mid_market",
                },
            ],
        }

        # Act - Execute lead assignment
        assignment_result = await admin_agent["agent"].execute_workflow(
            "lead_assignment_and_routing", assignment_criteria
        )

        # Assert - Lead assigned correctly
        assert assignment_result["success"] is True
        assert "assigned_rep" in assignment_result
        assert (
            assignment_result["assigned_rep"]["id"] == "rep_1"
        )  # Should match territory
        assert assignment_result["crm_updated"] is True
        assert assignment_result["rep_notified"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_crm_synchronization_workflow(
        self, admin_agent: Dict[str, Any]
    ) -> None:
        """Test CRM synchronization workflow across multiple systems."""
        # Arrange
        sync_config = {
            "source_crm": "pipedrive",
            "target_crms": ["salesforce", "zoho"],
            "sync_fields": ["name", "email", "company", "stage", "value", "notes"],
            "conflict_resolution": "latest_update_wins",
        }

        # Act - Execute CRM sync
        sync_result = await admin_agent["agent"].execute_workflow(
            "crm_synchronization", sync_config
        )

        # Assert - CRM data synchronized
        assert sync_result["success"] is True
        assert "records_synced" in sync_result
        assert sync_result["records_synced"] >= 0
        assert "sync_errors" in sync_result
        assert len(sync_result["sync_errors"]) == 0  # No errors expected in test


class TestMultiAgentCoordination:
    """Test coordination between multiple agents with MCP services."""

    @pytest.fixture
    async def all_agents(self) -> Dict[str, Any]:
        """Create all agents with MCP integration."""
        return await create_agents_with_proper_mcp_integration(TEST_USER_ID)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_lead_to_meeting_workflow(
        self, all_agents: Dict[str, Any]
    ) -> None:
        """Test complete workflow from lead capture to meeting scheduled."""
        # Arrange
        new_lead = {
            "name": "Sarah Wilson",
            "email": "sarah.wilson@innovatetech.com",
            "company": "InnovateTech",
            "source": "website_form",
            "interest": "automation_platform",
        }

        # Act - Execute complete workflow
        # 1. Coordinator handles initial outreach
        coordinator = all_agents["coordinator"]
        outreach_result = await coordinator["agent"].execute_workflow(
            "lead_welcome_sequence", {"lead": new_lead}
        )

        # 2. Lead Administrator updates CRM
        admin = all_agents["lead_administrator"]
        crm_result = await mark_lead_as_contacted_with_mcp(
            user_id=TEST_USER_ID,
            lead_id=f"lead_{new_lead['email'].replace('@', '_').replace('.', '_')}",
            contact_method="email",
            notes="Welcome sequence sent",
        )

        # 3. Meeting Scheduler schedules discovery call
        scheduler = all_agents["meeting_scheduler"]
        meeting_result = await schedule_meeting_with_mcp(
            user_id=TEST_USER_ID,
            lead_email=new_lead["email"],
            meeting_type="discovery_call",
            duration=30,
            preferred_times=[
                (datetime.now() + timedelta(days=3, hours=14)).isoformat()
            ],
        )

        # Assert - Complete workflow successful
        assert outreach_result["success"] is True
        assert crm_result["success"] is True
        assert meeting_result["success"] is True

        # Verify end-to-end connectivity
        assert "meeting_url" in meeting_result
        assert crm_result["crm_updates"]["pipedrive"]["updated"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_agent_handoff_workflow(self, all_agents: Dict[str, Any]) -> None:
        """Test handoff between agents during workflow execution."""
        # Arrange
        lead_data = {
            "name": "Michael Chen",
            "email": "m.chen@techstartup.io",
            "company": "TechStartup",
            "engagement_level": "high",
            "ready_for_meeting": True,
        }

        # Act - Execute handoff workflow
        coordinator = all_agents["coordinator"]

        # Coordinator identifies meeting-ready lead
        handoff_result = await coordinator["agent"].execute_workflow(
            "identify_meeting_ready_leads", {"leads": [lead_data]}
        )

        # Automatic handoff to Meeting Scheduler
        if handoff_result["meeting_ready_leads"]:
            scheduler = all_agents["meeting_scheduler"]
            meeting_ready_lead = handoff_result["meeting_ready_leads"][0]

            scheduling_result = await scheduler["agent"].execute_workflow(
                "auto_schedule_discovery_call", {"lead": meeting_ready_lead}
            )

            # Assert - Handoff successful
            assert scheduling_result["success"] is True
            assert "handoff_from_coordinator" in scheduling_result
            assert scheduling_result["handoff_from_coordinator"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_failure_recovery(self, all_agents: Dict[str, Any]) -> None:
        """Test workflow failure recovery and error propagation between agents."""
        # Arrange
        problematic_lead = {
            "name": "Test User",
            "email": "invalid-email-format",  # Invalid email to trigger failure
            "company": "Test Company",
        }

        # Act - Execute workflow with expected failure
        coordinator = all_agents["coordinator"]

        with patch(
            "app.ai_agents.tools.sendgrid_mcp.SendGridMCP.send_email"
        ) as mock_email:
            mock_email.side_effect = MCPOperationError("Invalid email address")

            workflow_result = await coordinator["agent"].execute_workflow(
                "lead_welcome_sequence",
                {
                    "lead": problematic_lead,
                    "enable_error_recovery": True,
                    "fallback_to_admin_notification": True,
                },
            )

        # Assert - Error handled gracefully
        assert workflow_result["success"] is False
        assert "error_details" in workflow_result
        assert workflow_result["fallback_executed"] is True
        assert workflow_result["admin_notified"] is True


if __name__ == "__main__":
    # Run agent workflow integration tests
    pytest.main(
        [
            __file__,
            "-v",
            "-m",
            "integration",
            "--tb=short",
            "-x",  # Stop on first failure
        ]
    )
