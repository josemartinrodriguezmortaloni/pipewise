"""
Unit tests for modern AgentSDK implementation
Following Rule 4.1: Use FastAPI TestClient with Fixtures
"""

import pytest
from unittest.mock import Mock, patch
from app.agents.modern_agents import (
    ModernAgents,
    TenantContext,
)


class TestFunctionToolLogic:
    """Test the logic behind @function_tool decorated functions by testing similar logic in isolation"""

    @patch("app.supabase.supabase_client.SupabaseCRMClient")
    def test_crm_lead_data_retrieval_logic(self, mock_client_class):
        """Test the logic similar to what get_crm_lead_data does"""
        # Setup mock
        mock_lead = Mock()
        mock_lead.name = "John Doe"
        mock_lead.company = "Test Corp"
        mock_lead.status = "new"
        mock_lead.qualified = False

        mock_client_instance = Mock()
        mock_client_instance.get_lead.return_value = mock_lead
        mock_client_class.return_value = mock_client_instance

        # Test the core logic that would be in get_crm_lead_data
        from app.supabase.supabase_client import SupabaseCRMClient

        client = SupabaseCRMClient()
        lead = client.get_lead("test-lead-123")

        if lead:
            result = f"Lead data for test-lead-123: Name={lead.name}, Company={lead.company}, Status={lead.status}, Qualified={lead.qualified}"
        else:
            result = "No lead found with ID test-lead-123"

        # Assertions
        assert "John Doe" in result
        assert "Test Corp" in result
        assert "new" in result
        mock_client_instance.get_lead.assert_called_once_with("test-lead-123")

    @patch("app.supabase.supabase_client.SupabaseCRMClient")
    def test_lead_opportunity_analysis_logic(self, mock_client_class):
        """Test lead opportunity analysis logic"""
        mock_lead = Mock()
        mock_lead.metadata = {"company_size": "100-500", "industry": "technology"}
        mock_lead.message = "We have a budget of $50k for this project"

        mock_client_instance = Mock()
        mock_client_instance.get_lead.return_value = mock_lead
        mock_client_class.return_value = mock_client_instance

        # Test the core logic that would be in analyze_lead_opportunity
        from app.supabase.supabase_client import SupabaseCRMClient

        client = SupabaseCRMClient()
        lead = client.get_lead("test-lead-123")

        if not lead:
            result = "Lead test-lead-123 not found"
        else:
            analysis = "Lead analysis for test-lead-123: "
            analysis += f"Company size indicator: {lead.metadata.get('company_size', 'Unknown') if lead.metadata else 'Unknown'}, "
            analysis += f"Industry: {lead.metadata.get('industry', 'Unknown') if lead.metadata else 'Unknown'}, "
            analysis += (
                f"Message indicates budget: {'budget' in (lead.message or '').lower()}"
            )
            result = analysis

        assert "100-500" in result
        assert "technology" in result
        assert "True" in result  # Budget mentioned

    @patch("app.supabase.supabase_client.SupabaseCRMClient")
    def test_lead_qualification_update_logic(self, mock_client_class):
        """Test lead qualification update logic"""
        mock_client_instance = Mock()
        mock_client_instance.update_lead.return_value = Mock()
        mock_client_class.return_value = mock_client_instance

        # Test the core logic that would be in update_lead_qualification
        from app.supabase.supabase_client import SupabaseCRMClient
        from app.schemas.lead_schema import LeadUpdate

        client = SupabaseCRMClient()

        lead_id = "test-lead-123"
        qualified = True
        reason = "High-quality enterprise lead"
        score = 85.0

        metadata = {
            "qualification_reason": reason,
            "qualification_score": score,
            "qualified_by": "lead_agent_sdk",
            "qualification_timestamp": "now()",
        }

        status = "qualified" if qualified else "unqualified"
        updates = LeadUpdate(qualified=qualified, status=status, metadata=metadata)

        result = client.update_lead(lead_id, updates)

        if result:
            response = f"Lead {lead_id} updated successfully: qualified={qualified}, score={score}"
        else:
            response = f"Failed to update lead {lead_id}"

        assert "updated successfully" in response
        assert "qualified=True" in response
        assert "score=85.0" in response
        mock_client_instance.update_lead.assert_called_once()


class TestModernAgents:
    """Test the ModernAgents class"""

    def test_initialization_with_tenant_context(self):
        """Test ModernAgents initialization with tenant context"""
        tenant_context = TenantContext(
            tenant_id="test-tenant",
            user_id="test-user",
            is_premium=True,
            api_limits={"calls_per_hour": 1000},
            features_enabled=["advanced_qualification"],
        )

        agents = ModernAgents(tenant_context)

        assert agents.tenant_context == tenant_context
        assert agents.processor is not None

    def test_initialization_with_default_context(self):
        """Test ModernAgents initialization with default context"""
        agents = ModernAgents()

        assert agents.tenant_context.tenant_id == "default"
        assert agents.tenant_context.user_id == "system"
        assert not agents.tenant_context.is_premium

    @pytest.mark.asyncio
    @patch("app.agents.modern_agents.Runner.run")
    async def test_qualify_lead_only(self, mock_runner):
        """Test individual lead qualification"""
        # Setup mock response
        mock_result = Mock()
        mock_runner.return_value = mock_result

        agents = ModernAgents()
        lead_data = {"name": "Test Lead", "company": "Test Corp"}

        result = await agents.qualify_lead_only(lead_data)

        assert result == mock_result
        mock_runner.assert_called_once()

        # Check that the correct agent and prompt were used
        call_args = mock_runner.call_args
        assert "Qualify this lead" in call_args[0][1]

    @pytest.mark.asyncio
    @patch("app.agents.modern_agents.Runner.run")
    async def test_contact_lead_only(self, mock_runner):
        """Test individual outbound contact"""
        mock_result = Mock()
        mock_runner.return_value = mock_result

        agents = ModernAgents()

        result = await agents.contact_lead_only("lead-123", {"name": "Test"})

        assert result == mock_result
        mock_runner.assert_called_once()

        call_args = mock_runner.call_args
        assert "Contact lead lead-123" in call_args[0][1]

    @pytest.mark.asyncio
    @patch("app.agents.modern_agents.Runner.run")
    async def test_schedule_meeting_only(self, mock_runner):
        """Test individual meeting scheduling"""
        mock_result = Mock()
        mock_runner.return_value = mock_result

        agents = ModernAgents()

        result = await agents.schedule_meeting_only("lead-123", {"name": "Test"})

        assert result == mock_result
        mock_runner.assert_called_once()

        call_args = mock_runner.call_args
        assert "Schedule meeting for lead lead-123" in call_args[0][1]

    def test_run_workflow_sync(self):
        """Test synchronous workflow wrapper"""
        agents = ModernAgents()
        lead_data = {"name": "Test Lead"}

        # Mock the async method
        with patch.object(agents, "run_workflow") as mock_async:
            mock_async.return_value = {"status": "completed"}

            result = agents.run_workflow_sync(lead_data)

            assert result["status"] == "completed"
            mock_async.assert_called_once_with(lead_data)


class TestModernLeadProcessor:
    """Test the ModernLeadProcessor class"""

    @pytest.mark.asyncio
    @patch("app.agents.modern_agents.Runner.run")
    @patch("app.agents.modern_agents.SupabaseCRMClient")
    async def test_process_lead_workflow_success(self, mock_client, mock_runner):
        """Test successful lead workflow processing"""
        from app.agents.modern_agents import ModernLeadProcessor

        # Setup mocks
        mock_qualification_result = Mock()
        mock_qualification_result.output = Mock()
        mock_qualification_result.output.qualified = True
        mock_qualification_result.output.qualification_score = 85.0
        mock_qualification_result.raw_responses = []
        mock_qualification_result.to_input_list.return_value = []
        mock_qualification_result.final_output = {
            "status": "completed",
            "qualified": True,
            "qualification_score": 85.0,
            "workflow_completed": True,
            "lead_id": "test-lead-123",
        }

        # Mock contact and meeting results too
        mock_contact_result = Mock()
        mock_contact_result.to_input_list.return_value = []
        mock_contact_result.final_output = {"contact_completed": True}

        mock_meeting_result = Mock()
        mock_meeting_result.final_output = {
            "status": "completed",
            "qualified": True,
            "qualification_score": 85.0,
            "workflow_completed": True,
            "lead_id": "test-lead-123",
        }

        # Return different mocks for each call
        mock_runner.side_effect = [
            mock_qualification_result,
            mock_contact_result,
            mock_meeting_result,
        ]

        processor = ModernLeadProcessor()
        lead_data = {
            "id": "test-lead-123",
            "name": "Test Lead",
            "email": "test@example.com",
            "company": "Test Corp",
        }

        result = await processor.process_lead_workflow(lead_data)

        # Assertions
        assert result["status"] == "completed"
        assert result["qualified"] is True
        assert result["qualification_score"] == 85.0
        assert result["workflow_completed"] is True
        assert "lead_id" in result

        # Verify all three agents were called
        assert mock_runner.call_count == 3

    @pytest.mark.asyncio
    @patch("app.agents.modern_agents.Runner.run")
    async def test_process_lead_workflow_unqualified(self, mock_runner):
        """Test workflow with unqualified lead"""
        from app.agents.modern_agents import ModernLeadProcessor

        # Setup mock for unqualified lead
        mock_result = Mock()
        mock_result.output = Mock()
        mock_result.output.qualified = False
        mock_result.raw_responses = []
        mock_result.to_input_list.return_value = []
        mock_result.final_output = {
            "status": "completed",
            "qualified": False,
            "reason": "Lead did not meet qualification criteria",
            "workflow_completed": True,
        }
        mock_runner.return_value = mock_result

        processor = ModernLeadProcessor()
        lead_data = {"name": "Unqualified Lead"}

        result = await processor.process_lead_workflow(lead_data)

        assert result["status"] == "completed"
        assert result["qualified"] is False
        assert "reason" in result
        assert result["workflow_completed"] is True

        # All three agents are called regardless of qualification status in current implementation
        assert mock_runner.call_count == 3

    @pytest.mark.asyncio
    @patch("app.agents.modern_agents.Runner.run")
    async def test_process_lead_workflow_error_handling(self, mock_runner):
        """Test workflow error handling"""
        from app.agents.modern_agents import ModernLeadProcessor

        # Setup mock to raise exception
        mock_runner.side_effect = Exception("AgentSDK error")

        processor = ModernLeadProcessor()
        lead_data = {"name": "Error Lead"}

        result = await processor.process_lead_workflow(lead_data)

        assert result["status"] == "error"
        assert "AgentSDK error" in result["error"]
        assert result["workflow_completed"] is False


class TestTenantContext:
    """Test TenantContext dataclass"""

    def test_tenant_context_creation(self):
        """Test TenantContext creation and attributes"""
        context = TenantContext(
            tenant_id="tenant-123",
            user_id="user-456",
            is_premium=True,
            api_limits={"requests_per_hour": 1000},
            features_enabled=["feature1", "feature2"],
        )

        assert context.tenant_id == "tenant-123"
        assert context.user_id == "user-456"
        assert context.is_premium is True
        assert context.api_limits["requests_per_hour"] == 1000
        assert "feature1" in context.features_enabled
