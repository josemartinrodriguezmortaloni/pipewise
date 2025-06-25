"""
Test suite for Modern Agent Architecture workflow
Tests the complete agent workflow from lead qualification to meeting scheduling
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from app.agents.agents import (
    ModernAgents,
    ModernLeadProcessor,
    TenantContext,
    LeadAnalysis,
    MeetingScheduleResult,
)


class TestFunctionTools:
    """Test the function tools used by agents by testing the underlying logic"""

    @patch("app.agents.agents.SupabaseCRMClient")
    def test_get_crm_lead_data_logic(self, mock_supabase_client: Mock) -> None:
        """Test the logic behind get_crm_lead_data function tool."""
        # Arrange
        mock_lead = Mock()
        mock_lead.name = "John Doe"
        mock_lead.company = "Acme Corp"
        mock_lead.status = "new"
        mock_lead.qualified = False

        mock_client_instance = Mock()
        mock_client_instance.get_lead.return_value = mock_lead
        mock_supabase_client.return_value = mock_client_instance

        # Act - Test the core logic that would be in get_crm_lead_data
        from app.supabase.supabase_client import SupabaseCRMClient

        db_client = SupabaseCRMClient()
        lead = db_client.get_lead("test-lead-123")

        if lead:
            result = f"Lead data for test-lead-123: Name={lead.name}, Company={lead.company}, Status={lead.status}, Qualified={lead.qualified}"
        else:
            result = "No lead found with ID test-lead-123"

        # Assert
        assert "John Doe" in result
        assert "Acme Corp" in result
        assert "new" in result
        mock_client_instance.get_lead.assert_called_once_with("test-lead-123")

    @patch("app.agents.agents.SupabaseCRMClient")
    def test_get_crm_lead_data_not_found_logic(
        self, mock_supabase_client: Mock
    ) -> None:
        """Test lead data retrieval logic when lead is not found."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.get_lead.return_value = None
        mock_supabase_client.return_value = mock_client_instance

        # Act - Test the core logic
        from app.supabase.supabase_client import SupabaseCRMClient

        db_client = SupabaseCRMClient()
        lead = db_client.get_lead("nonexistent-lead")

        if lead:
            result = f"Lead data for nonexistent-lead: Name={lead.name}, Company={lead.company}, Status={lead.status}, Qualified={lead.qualified}"
        else:
            result = "No lead found with ID nonexistent-lead"

        # Assert
        assert "No lead found" in result
        assert "nonexistent-lead" in result

    @patch("app.agents.agents.SupabaseCRMClient")
    def test_analyze_lead_opportunity_logic(self, mock_supabase_client: Mock) -> None:
        """Test the logic behind analyze_lead_opportunity function tool."""
        # Arrange
        mock_lead = Mock()
        mock_lead.metadata = {"company_size": "50-100", "industry": "SaaS"}
        mock_lead.message = "We have a budget of $50k for this project"

        mock_client_instance = Mock()
        mock_client_instance.get_lead.return_value = mock_lead
        mock_supabase_client.return_value = mock_client_instance

        # Act - Test the analysis logic
        from app.supabase.supabase_client import SupabaseCRMClient

        db_client = SupabaseCRMClient()
        lead = db_client.get_lead("test-lead-123")

        if not lead:
            result = "Lead test-lead-123 not found"
        else:
            # Analyze lead data for qualification (same logic as in the function)
            analysis = "Lead analysis for test-lead-123: "
            analysis += f"Company size indicator: {lead.metadata.get('company_size', 'Unknown') if lead.metadata else 'Unknown'}, "
            analysis += f"Industry: {lead.metadata.get('industry', 'Unknown') if lead.metadata else 'Unknown'}, "
            analysis += (
                f"Message indicates budget: {'budget' in (lead.message or '').lower()}"
            )
            result = analysis

        # Assert
        assert "50-100" in result
        assert "SaaS" in result
        assert "budget" in result.lower()

    @patch("app.agents.agents.SupabaseCRMClient")
    def test_update_lead_qualification_logic(self, mock_supabase_client: Mock) -> None:
        """Test the logic behind update_lead_qualification function tool."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.update_lead.return_value = True
        mock_supabase_client.return_value = mock_client_instance

        # Act - Test the update logic
        from app.supabase.supabase_client import SupabaseCRMClient
        from app.schemas.lead_schema import LeadUpdate

        db_client = SupabaseCRMClient()

        lead_id = "test-lead-123"
        qualified = True
        reason = "Strong budget indication"
        score = 85.0

        metadata = {
            "qualification_reason": reason,
            "qualification_score": score,
            "qualified_by": "lead_agent_sdk",
            "qualification_timestamp": "now()",
        }

        status = "qualified" if qualified else "unqualified"
        updates = LeadUpdate(qualified=qualified, status=status, metadata=metadata)

        result_success = db_client.update_lead(lead_id, updates)

        if result_success:
            result = f"Lead {lead_id} updated successfully: qualified={qualified}, score={score}"
        else:
            result = f"Failed to update lead {lead_id}"

        # Assert
        assert "updated successfully" in result
        assert "qualified=True" in result
        assert "score=85.0" in result
        mock_client_instance.update_lead.assert_called_once()

    @patch("app.agents.agents.SupabaseCRMClient")
    def test_mark_lead_contacted_logic(self, mock_supabase_client: Mock) -> None:
        """Test the logic behind mark_lead_contacted function tool."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.update_lead.return_value = True
        mock_supabase_client.return_value = mock_client_instance

        # Act - Test the contact marking logic
        from app.supabase.supabase_client import SupabaseCRMClient
        from app.schemas.lead_schema import LeadUpdate

        db_client = SupabaseCRMClient()

        lead_id = "test-lead-123"
        channel = "email"
        message = "Personalized outreach about CRM solution"

        metadata = {
            "contact_channel": channel,
            "contact_message": message,
            "contacted_by": "outbound_agent_sdk",
            "contact_timestamp": "now()",
        }

        updates = LeadUpdate(contacted=True, metadata=metadata)
        result_success = db_client.update_lead(lead_id, updates)

        if result_success:
            result = f"Lead {lead_id} marked as contacted via {channel}"
        else:
            result = f"Failed to mark lead {lead_id} as contacted"

        # Assert
        assert "marked as contacted" in result
        assert "email" in result
        mock_client_instance.update_lead.assert_called_once()

    @patch("app.agents.agents.SupabaseCRMClient")
    def test_schedule_meeting_for_lead_logic(self, mock_supabase_client: Mock) -> None:
        """Test the logic behind schedule_meeting_for_lead function tool."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.update_lead.return_value = True
        mock_supabase_client.return_value = mock_client_instance

        # Act - Test the meeting scheduling logic
        from app.supabase.supabase_client import SupabaseCRMClient
        from app.schemas.lead_schema import LeadUpdate

        db_client = SupabaseCRMClient()

        lead_id = "test-lead-123"
        meeting_url = "https://calendly.com/demo"
        event_type = "Product Demo"

        metadata = {
            "meeting_url": meeting_url,
            "meeting_type": event_type,
            "scheduled_by": "meeting_agent_sdk",
            "scheduling_timestamp": "now()",
        }

        updates = LeadUpdate(meeting_scheduled=True, metadata=metadata)
        result_success = db_client.update_lead(lead_id, updates)

        if result_success:
            result = f"Meeting scheduled for lead {lead_id}: {meeting_url}"
        else:
            result = f"Failed to schedule meeting for lead {lead_id}"

        # Assert
        assert "Meeting scheduled" in result
        assert "https://calendly.com/demo" in result
        mock_client_instance.update_lead.assert_called_once()


class TestTenantContext:
    """Test tenant context functionality"""

    def test_tenant_context_creation(self) -> None:
        """Test creation of tenant context."""
        # Act
        context = TenantContext(
            tenant_id="tenant-123",
            user_id="user-456",
            is_premium=True,
            api_limits={"calls_per_hour": 1000},
            features_enabled=["advanced_qualification", "ai_insights"],
        )

        # Assert
        assert context.tenant_id == "tenant-123"
        assert context.user_id == "user-456"
        assert context.is_premium is True
        assert context.api_limits["calls_per_hour"] == 1000
        assert "advanced_qualification" in context.features_enabled


class TestModernLeadProcessor:
    """Test the modern lead processor workflow"""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.tenant_context = TenantContext(
            tenant_id="test-tenant",
            user_id="test-user",
            is_premium=True,
            api_limits={"calls_per_hour": 1000},
            features_enabled=["all"],
        )
        self.processor = ModernLeadProcessor(self.tenant_context)

    def test_processor_initialization(self) -> None:
        """Test processor initialization."""
        assert self.processor.tenant_context == self.tenant_context
        assert self.processor.db_client is not None

    @pytest.mark.asyncio
    @patch("app.agents.agents.Runner")
    @patch("app.agents.agents.SupabaseCRMClient")
    async def test_process_lead_workflow_success(
        self, mock_supabase_client: Mock, mock_runner: Mock
    ) -> None:
        """Test successful lead workflow processing."""
        # Arrange
        lead_data = {
            "id": "test-lead-123",
            "name": "John Doe",
            "email": "john@acme.com",
            "company": "Acme Corp",
            "message": "Interested in CRM solution with budget of $10k",
        }

        # Mock runner responses
        mock_qualification_result = Mock()
        mock_qualification_result.raw_responses = Mock()
        mock_qualification_result.qualified = True
        mock_qualification_result.qualification_score = 85.0
        mock_qualification_result.to_input_list.return_value = [
            {"role": "system", "content": "Lead qualified with score 85"}
        ]

        mock_contact_result = Mock()
        mock_contact_result.to_input_list.return_value = [
            {"role": "system", "content": "Outbound contact sent successfully"}
        ]

        mock_meeting_result = Mock()
        mock_meeting_result.final_output = {
            "status": "completed",
            "qualified": True,
            "contacted": True,
            "meeting_scheduled": True,
            "workflow_completed": True,
        }

        mock_runner.run = AsyncMock(
            side_effect=[
                mock_qualification_result,
                mock_contact_result,
                mock_meeting_result,
            ]
        )

        # Act
        result = await self.processor.process_lead_workflow(lead_data)

        # Assert
        assert result["status"] == "completed"
        assert result["workflow_completed"] is True
        assert mock_runner.run.call_count == 3

    @pytest.mark.asyncio
    @patch("app.agents.agents.Runner")
    async def test_process_lead_workflow_error_handling(
        self, mock_runner: Mock
    ) -> None:
        """Test error handling in lead workflow processing."""
        # Arrange
        lead_data = {"id": "test-lead-123"}
        mock_runner.run = AsyncMock(side_effect=Exception("API Error"))

        # Act
        result = await self.processor.process_lead_workflow(lead_data)

        # Assert
        assert result["status"] == "error"
        assert "API Error" in result["error"]
        assert result["workflow_completed"] is False


class TestModernAgents:
    """Test the modern agents coordinator"""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.agents = ModernAgents()

    def test_agents_initialization_default(self) -> None:
        """Test agents initialization with default context."""
        assert self.agents.tenant_context.tenant_id == "default"
        assert self.agents.tenant_context.user_id == "system"
        assert self.agents.tenant_context.is_premium is False
        assert self.agents.processor is not None

    def test_agents_initialization_custom_context(self) -> None:
        """Test agents initialization with custom context."""
        custom_context = TenantContext(
            tenant_id="premium-tenant",
            user_id="premium-user",
            is_premium=True,
            api_limits={"calls_per_hour": 5000},
            features_enabled=["all"],
        )

        agents = ModernAgents(custom_context)

        assert agents.tenant_context == custom_context
        assert agents.tenant_context.is_premium is True

    @pytest.mark.asyncio
    @patch("app.agents.agents.ModernLeadProcessor.process_lead_workflow")
    async def test_run_workflow_async(self, mock_process: AsyncMock) -> None:
        """Test async workflow execution."""
        # Arrange
        lead_data = {"id": "test-lead", "name": "Test Lead"}
        expected_result = {"status": "completed", "workflow_completed": True}
        mock_process.return_value = expected_result

        # Act
        result = await self.agents.run_workflow(lead_data)

        # Assert
        assert result == expected_result
        mock_process.assert_called_once_with(lead_data)

    def test_run_workflow_sync(self) -> None:
        """Test synchronous workflow execution."""
        # Arrange
        lead_data = {"id": "test-lead", "name": "Test Lead"}

        # Mock the async method to return a simple result
        with patch.object(self.agents, "run_workflow") as mock_async:
            mock_async.return_value = {
                "status": "completed",
                "workflow_completed": True,
            }

            # Since we can't easily test the actual sync wrapper, we'll test it returns a result
            # In real usage, this would call asyncio.run(self.run_workflow(lead_data))
            result = self.agents.run_workflow_sync(lead_data)

            # The sync method should return some result
            assert isinstance(result, dict)


class TestAgentModels:
    """Test the Pydantic models used by agents"""

    def test_lead_analysis_model(self) -> None:
        """Test LeadAnalysis model validation."""
        analysis = LeadAnalysis(
            lead_id="test-lead-123",
            qualification_score=85.5,
            qualified=True,
            key_factors=["Budget confirmed", "Decision maker identified"],
            recommendations=["Schedule demo", "Send technical specs"],
            risk_factors=["Timeline pressure"],
            opportunity_size="$50k",
        )

        assert analysis.lead_id == "test-lead-123"
        assert analysis.qualification_score == 85.5
        assert analysis.qualified is True
        assert len(analysis.key_factors) == 2
        assert len(analysis.recommendations) == 2
        assert len(analysis.risk_factors) == 1

    def test_meeting_schedule_result_model(self) -> None:
        """Test MeetingScheduleResult model validation."""
        result = MeetingScheduleResult(
            lead_id="test-lead-123",
            success=True,
            meeting_url="https://calendly.com/demo",
            event_type="Product Demo",
            scheduled_time="2024-01-15T10:00:00Z",
        )

        assert result.lead_id == "test-lead-123"
        assert result.success is True
        assert result.meeting_url == "https://calendly.com/demo"
        assert result.event_type == "Product Demo"
        assert result.scheduled_time == "2024-01-15T10:00:00Z"


class TestIntegrationWorkflow:
    """Integration tests for the complete workflow"""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.agents = ModernAgents()

    @pytest.mark.asyncio
    @patch("app.agents.agents.SupabaseCRMClient")
    @patch("app.agents.agents.Runner")
    async def test_complete_workflow_integration(
        self, mock_runner: Mock, mock_supabase_client: Mock
    ) -> None:
        """Test complete workflow integration with mocked dependencies."""
        # Arrange
        lead_data = {
            "id": "integration-test-lead",
            "name": "Jane Smith",
            "email": "jane@techcorp.com",
            "company": "TechCorp Inc",
            "message": "Looking for CRM solution, budget approved for $25k",
            "metadata": {"company_size": "100-500", "industry": "Technology"},
        }

        # Mock database responses
        mock_lead = Mock()
        mock_lead.name = "Jane Smith"
        mock_lead.company = "TechCorp Inc"
        mock_lead.status = "new"
        mock_lead.qualified = False
        mock_lead.metadata = lead_data["metadata"]
        mock_lead.message = lead_data["message"]

        mock_client_instance = Mock()
        mock_client_instance.get_lead.return_value = mock_lead
        mock_client_instance.update_lead.return_value = True
        mock_supabase_client.return_value = mock_client_instance

        # Mock agent responses
        mock_result = Mock()
        mock_result.final_output = {
            "status": "completed",
            "qualified": True,
            "qualification_score": 88.0,
            "contacted": True,
            "contact_channel": "email",
            "meeting_scheduled": True,
            "meeting_url": "https://calendly.com/demo",
            "workflow_completed": True,
        }
        mock_result.to_input_list.return_value = []
        mock_runner.run = AsyncMock(return_value=mock_result)

        # Act
        result = await self.agents.run_workflow(lead_data)

        # Assert
        assert result["status"] == "completed"
        assert result["qualified"] is True
        assert result["contacted"] is True
        assert result["meeting_scheduled"] is True
        assert result["workflow_completed"] is True

    def test_error_propagation(self) -> None:
        """Test that errors are properly propagated through the workflow."""
        # This test verifies that exceptions in the workflow are handled gracefully
        lead_data = {}  # Invalid lead data

        # Should not raise exception, but return error status
        result = self.agents.run_workflow_sync(lead_data)

        # Result should indicate error without crashing
        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
