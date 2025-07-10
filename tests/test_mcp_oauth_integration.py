"""
Unit tests for MCP OAuth integration functionality.

This module tests OAuth integration with MCP services including:
- OAuth token retrieval and mapping
- Credential validation and refresh
- Service-specific OAuth configurations
- Token expiration and auto-renewal
- Integration status monitoring
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta
import jwt
import json

from app.ai_agents.mcp.oauth_integration import (
    get_mcp_credentials_for_user,
    refresh_oauth_token_if_needed,
    validate_oauth_token,
    map_oauth_tokens_to_mcp_credentials,
    OAuthTokenManager,
    IntegrationStatusMonitor,
)
from app.ai_agents.mcp.error_handler import (
    MCPAuthenticationError,
    MCPConfigurationError,
)
from app.supabase.supabase_client import supabase_client


class TestOAuthCredentialRetrieval:
    """Test OAuth credential retrieval for MCP services."""

    @pytest.fixture
    def mock_supabase_response(self) -> Dict[str, Any]:
        """Create mock Supabase response with OAuth tokens."""
        return {
            "data": [
                {
                    "user_id": "test-user-123",
                    "service_name": "sendgrid",
                    "access_token": "sg_test_token_123",
                    "refresh_token": "sg_refresh_token_123",
                    "token_expires_at": (
                        datetime.now() + timedelta(hours=1)
                    ).isoformat(),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "is_active": True,
                }
            ],
            "error": None,
        }

    @pytest.fixture
    def mock_expired_token_response(self) -> Dict[str, Any]:
        """Create mock response with expired token."""
        return {
            "data": [
                {
                    "user_id": "test-user-123",
                    "service_name": "twitter",
                    "access_token": "twitter_expired_token",
                    "refresh_token": "twitter_refresh_token",
                    "token_expires_at": (
                        datetime.now() - timedelta(hours=1)
                    ).isoformat(),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "is_active": True,
                }
            ],
            "error": None,
        }

    @pytest.mark.asyncio
    async def test_get_mcp_credentials_success(
        self, mock_supabase_response: Dict[str, Any]
    ) -> None:
        """Test successful retrieval of MCP credentials."""
        # Arrange
        user_id = "test-user-123"
        service_name = "sendgrid"

        with patch.object(supabase_client, "table") as mock_table:
            mock_table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_supabase_response

            # Act
            credentials = await get_mcp_credentials_for_user(user_id, service_name)

            # Assert
            assert credentials is not None
            assert credentials["access_token"] == "sg_test_token_123"
            assert credentials["refresh_token"] == "sg_refresh_token_123"
            assert credentials["service_name"] == "sendgrid"
            assert "token_expires_at" in credentials

    @pytest.mark.asyncio
    async def test_get_mcp_credentials_not_found(self) -> None:
        """Test credential retrieval when no tokens found."""
        # Arrange
        user_id = "test-user-123"
        service_name = "nonexistent_service"
        empty_response = {"data": [], "error": None}

        with patch.object(supabase_client, "table") as mock_table:
            mock_table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = empty_response

            # Act
            credentials = await get_mcp_credentials_for_user(user_id, service_name)

            # Assert
            assert credentials is None

    @pytest.mark.asyncio
    async def test_get_mcp_credentials_database_error(self) -> None:
        """Test credential retrieval with database error."""
        # Arrange
        user_id = "test-user-123"
        service_name = "sendgrid"
        error_response = {
            "data": None,
            "error": {"message": "Database connection failed"},
        }

        with patch.object(supabase_client, "table") as mock_table:
            mock_table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = error_response

            # Act & Assert
            with pytest.raises(
                MCPConfigurationError, match="Failed to retrieve OAuth credentials"
            ):
                await get_mcp_credentials_for_user(user_id, service_name)

    @pytest.mark.asyncio
    async def test_get_all_user_credentials(self) -> None:
        """Test retrieval of all OAuth credentials for a user."""
        # Arrange
        user_id = "test-user-123"
        multi_service_response = {
            "data": [
                {
                    "user_id": "test-user-123",
                    "service_name": "sendgrid",
                    "access_token": "sg_token",
                    "refresh_token": "sg_refresh",
                    "token_expires_at": (
                        datetime.now() + timedelta(hours=1)
                    ).isoformat(),
                    "is_active": True,
                },
                {
                    "user_id": "test-user-123",
                    "service_name": "twitter",
                    "access_token": "tw_token",
                    "refresh_token": "tw_refresh",
                    "token_expires_at": (
                        datetime.now() + timedelta(hours=2)
                    ).isoformat(),
                    "is_active": True,
                },
            ],
            "error": None,
        }

        with patch.object(supabase_client, "table") as mock_table:
            mock_table.return_value.select.return_value.eq.return_value.execute.return_value = multi_service_response

            # Act
            from app.ai_agents.mcp.oauth_integration import get_all_user_credentials

            credentials = await get_all_user_credentials(user_id)

            # Assert
            assert len(credentials) == 2
            assert "sendgrid" in credentials
            assert "twitter" in credentials
            assert credentials["sendgrid"]["access_token"] == "sg_token"
            assert credentials["twitter"]["access_token"] == "tw_token"


class TestOAuthTokenValidation:
    """Test OAuth token validation functionality."""

    def test_validate_oauth_token_valid(self) -> None:
        """Test validation of valid OAuth token."""
        # Arrange
        valid_token_data = {
            "access_token": "valid_token_123",
            "token_expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            "is_active": True,
        }

        # Act
        is_valid = validate_oauth_token(valid_token_data)

        # Assert
        assert is_valid is True

    def test_validate_oauth_token_expired(self) -> None:
        """Test validation of expired OAuth token."""
        # Arrange
        expired_token_data = {
            "access_token": "expired_token_123",
            "token_expires_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "is_active": True,
        }

        # Act
        is_valid = validate_oauth_token(expired_token_data)

        # Assert
        assert is_valid is False

    def test_validate_oauth_token_inactive(self) -> None:
        """Test validation of inactive OAuth token."""
        # Arrange
        inactive_token_data = {
            "access_token": "inactive_token_123",
            "token_expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            "is_active": False,
        }

        # Act
        is_valid = validate_oauth_token(inactive_token_data)

        # Assert
        assert is_valid is False

    def test_validate_oauth_token_missing_fields(self) -> None:
        """Test validation with missing required fields."""
        # Arrange
        incomplete_token_data = {
            "access_token": "token_123"
            # Missing token_expires_at and is_active
        }

        # Act
        is_valid = validate_oauth_token(incomplete_token_data)

        # Assert
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_token_with_service_check(self) -> None:
        """Test token validation with actual service verification."""
        # Arrange
        token_data = {
            "access_token": "valid_token_123",
            "service_name": "sendgrid",
            "token_expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            "is_active": True,
        }

        with patch(
            "app.ai_agents.mcp.oauth_integration.verify_token_with_service"
        ) as mock_verify:
            mock_verify.return_value = True

            # Act
            from app.ai_agents.mcp.oauth_integration import validate_token_with_service

            is_valid = await validate_token_with_service(token_data)

            # Assert
            assert is_valid is True
            mock_verify.assert_called_once_with("sendgrid", "valid_token_123")


class TestOAuthTokenRefresh:
    """Test OAuth token refresh functionality."""

    @pytest.fixture
    def mock_refresh_response(self) -> Dict[str, Any]:
        """Create mock token refresh response."""
        return {
            "access_token": "new_access_token_123",
            "refresh_token": "new_refresh_token_123",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self,
        mock_expired_token_response: Dict[str, Any],
        mock_refresh_response: Dict[str, Any],
    ) -> None:
        """Test successful token refresh."""
        # Arrange
        user_id = "test-user-123"
        service_name = "twitter"

        with patch(
            "app.ai_agents.mcp.oauth_integration.call_service_refresh_endpoint"
        ) as mock_refresh:
            mock_refresh.return_value = mock_refresh_response

            with patch.object(supabase_client, "table") as mock_table:
                # Mock getting expired token
                mock_table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_expired_token_response
                # Mock updating with new token
                mock_table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = {
                    "error": None
                }

                # Act
                new_credentials = await refresh_oauth_token_if_needed(
                    user_id, service_name
                )

                # Assert
                assert new_credentials is not None
                assert new_credentials["access_token"] == "new_access_token_123"
                mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_token_failure(
        self, mock_expired_token_response: Dict[str, Any]
    ) -> None:
        """Test token refresh failure."""
        # Arrange
        user_id = "test-user-123"
        service_name = "twitter"

        with patch(
            "app.ai_agents.mcp.oauth_integration.call_service_refresh_endpoint"
        ) as mock_refresh:
            mock_refresh.side_effect = MCPAuthenticationError("Refresh token invalid")

            with patch.object(supabase_client, "table") as mock_table:
                mock_table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_expired_token_response

                # Act & Assert
                with pytest.raises(
                    MCPAuthenticationError, match="Refresh token invalid"
                ):
                    await refresh_oauth_token_if_needed(user_id, service_name)

    @pytest.mark.asyncio
    async def test_refresh_token_not_needed(
        self, mock_supabase_response: Dict[str, Any]
    ) -> None:
        """Test when token refresh is not needed."""
        # Arrange
        user_id = "test-user-123"
        service_name = "sendgrid"

        with patch.object(supabase_client, "table") as mock_table:
            mock_table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_supabase_response

            # Act
            credentials = await refresh_oauth_token_if_needed(user_id, service_name)

            # Assert
            assert credentials is not None
            assert credentials["access_token"] == "sg_test_token_123"  # Original token

    @pytest.mark.asyncio
    async def test_automatic_token_refresh_middleware(self) -> None:
        """Test automatic token refresh in middleware."""
        # Arrange
        user_id = "test-user-123"
        service_name = "sendgrid"

        with patch(
            "app.ai_agents.mcp.oauth_integration.get_mcp_credentials_for_user"
        ) as mock_get:
            with patch(
                "app.ai_agents.mcp.oauth_integration.refresh_oauth_token_if_needed"
            ) as mock_refresh:
                mock_get.return_value = {
                    "access_token": "expired_token",
                    "token_expires_at": (
                        datetime.now() - timedelta(minutes=5)
                    ).isoformat(),
                    "is_active": True,
                }
                mock_refresh.return_value = {
                    "access_token": "refreshed_token",
                    "token_expires_at": (
                        datetime.now() + timedelta(hours=1)
                    ).isoformat(),
                    "is_active": True,
                }

                # Act
                from app.ai_agents.mcp.oauth_integration import (
                    get_valid_credentials_with_refresh,
                )

                credentials = await get_valid_credentials_with_refresh(
                    user_id, service_name
                )

                # Assert
                assert credentials["access_token"] == "refreshed_token"
                mock_refresh.assert_called_once_with(user_id, service_name)


class TestOAuthTokenMapping:
    """Test mapping OAuth tokens to MCP credentials."""

    @pytest.fixture
    def sample_oauth_tokens(self) -> Dict[str, Any]:
        """Create sample OAuth tokens for multiple services."""
        return {
            "sendgrid": {
                "access_token": "sg_token_123",
                "refresh_token": "sg_refresh_123",
                "token_expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
                "service_name": "sendgrid",
            },
            "twitter": {
                "access_token": "tw_token_456",
                "refresh_token": "tw_refresh_456",
                "token_expires_at": (datetime.now() + timedelta(hours=2)).isoformat(),
                "service_name": "twitter",
            },
            "calendly": {
                "access_token": "cal_token_789",
                "refresh_token": "cal_refresh_789",
                "token_expires_at": (datetime.now() + timedelta(hours=3)).isoformat(),
                "service_name": "calendly",
            },
        }

    def test_map_oauth_tokens_to_mcp_credentials(
        self, sample_oauth_tokens: Dict[str, Any]
    ) -> None:
        """Test mapping OAuth tokens to MCP credential format."""
        # Act
        mcp_credentials = map_oauth_tokens_to_mcp_credentials(sample_oauth_tokens)

        # Assert
        assert "sendgrid" in mcp_credentials
        assert "twitter" in mcp_credentials
        assert "calendly" in mcp_credentials

        # Check SendGrid mapping
        assert mcp_credentials["sendgrid"]["api_key"] == "sg_token_123"
        assert mcp_credentials["sendgrid"]["service"] == "sendgrid"

        # Check Twitter mapping
        assert mcp_credentials["twitter"]["bearer_token"] == "tw_token_456"
        assert mcp_credentials["twitter"]["service"] == "twitter"

        # Check Calendly mapping
        assert mcp_credentials["calendly"]["access_token"] == "cal_token_789"
        assert mcp_credentials["calendly"]["service"] == "calendly"

    def test_map_oauth_tokens_agent_specific(
        self, sample_oauth_tokens: Dict[str, Any]
    ) -> None:
        """Test mapping OAuth tokens for specific agent types."""
        # Arrange
        from app.ai_agents.mcp.agent_mcp_factory import AgentType

        # Act - Map for Coordinator Agent (SendGrid + Twitter)
        coordinator_credentials = map_oauth_tokens_to_mcp_credentials(
            sample_oauth_tokens, agent_type=AgentType.COORDINATOR
        )

        # Assert
        assert "sendgrid" in coordinator_credentials
        assert "twitter" in coordinator_credentials
        assert "calendly" not in coordinator_credentials  # Should be filtered out

    def test_map_oauth_tokens_with_custom_mapping(self) -> None:
        """Test OAuth token mapping with custom service configurations."""
        # Arrange
        custom_tokens = {
            "custom_service": {
                "access_token": "custom_token_123",
                "service_name": "custom_service",
            }
        }

        custom_mapping = {
            "custom_service": {
                "token_field": "api_token",
                "additional_fields": {"endpoint": "https://api.custom.com"},
            }
        }

        # Act
        mcp_credentials = map_oauth_tokens_to_mcp_credentials(
            custom_tokens, custom_mapping=custom_mapping
        )

        # Assert
        assert "custom_service" in mcp_credentials
        assert mcp_credentials["custom_service"]["api_token"] == "custom_token_123"
        assert mcp_credentials["custom_service"]["endpoint"] == "https://api.custom.com"


class TestOAuthTokenManager:
    """Test OAuth token manager functionality."""

    @pytest.fixture
    def token_manager(self) -> OAuthTokenManager:
        """Create OAuth token manager instance."""
        return OAuthTokenManager()

    @pytest.mark.asyncio
    async def test_token_manager_get_credentials(
        self, token_manager: OAuthTokenManager
    ) -> None:
        """Test token manager credential retrieval."""
        # Arrange
        user_id = "test-user-123"
        service_name = "sendgrid"

        with patch.object(token_manager, "_fetch_from_database") as mock_fetch:
            mock_fetch.return_value = {
                "access_token": "sg_token_123",
                "service_name": "sendgrid",
                "token_expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            }

            # Act
            credentials = await token_manager.get_credentials(user_id, service_name)

            # Assert
            assert credentials["access_token"] == "sg_token_123"
            mock_fetch.assert_called_once_with(user_id, service_name)

    @pytest.mark.asyncio
    async def test_token_manager_caching(
        self, token_manager: OAuthTokenManager
    ) -> None:
        """Test token manager caching functionality."""
        # Arrange
        user_id = "test-user-123"
        service_name = "sendgrid"

        with patch.object(token_manager, "_fetch_from_database") as mock_fetch:
            mock_fetch.return_value = {
                "access_token": "sg_token_123",
                "service_name": "sendgrid",
            }

            # Act - First call
            credentials1 = await token_manager.get_credentials(user_id, service_name)
            # Second call should use cache
            credentials2 = await token_manager.get_credentials(user_id, service_name)

            # Assert
            assert credentials1 == credentials2
            mock_fetch.assert_called_once()  # Should only fetch once due to caching

    @pytest.mark.asyncio
    async def test_token_manager_cache_expiry(
        self, token_manager: OAuthTokenManager
    ) -> None:
        """Test token manager cache expiry."""
        # Arrange
        user_id = "test-user-123"
        service_name = "sendgrid"
        token_manager.cache_ttl = 0.1  # 100ms for testing

        with patch.object(token_manager, "_fetch_from_database") as mock_fetch:
            mock_fetch.return_value = {
                "access_token": "sg_token_123",
                "service_name": "sendgrid",
            }

            # Act
            credentials1 = await token_manager.get_credentials(user_id, service_name)
            await asyncio.sleep(0.15)  # Wait for cache to expire
            credentials2 = await token_manager.get_credentials(user_id, service_name)

            # Assert
            assert mock_fetch.call_count == 2  # Should fetch twice after cache expiry

    @pytest.mark.asyncio
    async def test_token_manager_bulk_refresh(
        self, token_manager: OAuthTokenManager
    ) -> None:
        """Test bulk token refresh for multiple services."""
        # Arrange
        user_id = "test-user-123"
        services = ["sendgrid", "twitter", "calendly"]

        with patch.object(token_manager, "refresh_token") as mock_refresh:
            mock_refresh.return_value = {"status": "refreshed"}

            # Act
            results = await token_manager.bulk_refresh_tokens(user_id, services)

            # Assert
            assert len(results) == 3
            assert all(result["status"] == "refreshed" for result in results.values())
            assert mock_refresh.call_count == 3


class TestIntegrationStatusMonitor:
    """Test integration status monitoring."""

    @pytest.fixture
    def status_monitor(self) -> IntegrationStatusMonitor:
        """Create integration status monitor instance."""
        return IntegrationStatusMonitor()

    @pytest.mark.asyncio
    async def test_monitor_service_health(
        self, status_monitor: IntegrationStatusMonitor
    ) -> None:
        """Test monitoring service health status."""
        # Arrange
        user_id = "test-user-123"

        with patch.object(status_monitor, "_check_service_connectivity") as mock_check:
            mock_check.side_effect = [
                {"service": "sendgrid", "status": "healthy", "response_time": 120},
                {"service": "twitter", "status": "unhealthy", "error": "Rate limited"},
                {"service": "calendly", "status": "healthy", "response_time": 200},
            ]

            # Act
            health_status = await status_monitor.check_user_integrations_health(user_id)

            # Assert
            assert health_status["sendgrid"]["status"] == "healthy"
            assert health_status["twitter"]["status"] == "unhealthy"
            assert health_status["calendly"]["status"] == "healthy"
            assert "error" in health_status["twitter"]

    @pytest.mark.asyncio
    async def test_monitor_token_expiry_alerts(
        self, status_monitor: IntegrationStatusMonitor
    ) -> None:
        """Test token expiry alerting."""
        # Arrange
        user_id = "test-user-123"

        # Mock tokens with different expiry times
        mock_tokens = {
            "sendgrid": {
                "token_expires_at": (
                    datetime.now() + timedelta(minutes=10)
                ).isoformat(),  # Expires soon
                "service_name": "sendgrid",
            },
            "twitter": {
                "token_expires_at": (
                    datetime.now() + timedelta(hours=2)
                ).isoformat(),  # Healthy
                "service_name": "twitter",
            },
        }

        with patch(
            "app.ai_agents.mcp.oauth_integration.get_all_user_credentials"
        ) as mock_get:
            mock_get.return_value = mock_tokens

            # Act
            expiry_alerts = await status_monitor.check_token_expiry_alerts(user_id)

            # Assert
            assert len(expiry_alerts) == 1
            assert expiry_alerts[0]["service"] == "sendgrid"
            assert expiry_alerts[0]["severity"] == "warning"

    def test_monitor_usage_analytics(
        self, status_monitor: IntegrationStatusMonitor
    ) -> None:
        """Test usage analytics tracking."""
        # Arrange
        user_id = "test-user-123"

        # Act - Record some usage
        status_monitor.record_service_usage(
            user_id, "sendgrid", "send_email", success=True
        )
        status_monitor.record_service_usage(
            user_id, "sendgrid", "send_email", success=False
        )
        status_monitor.record_service_usage(
            user_id, "twitter", "post_tweet", success=True
        )

        # Get analytics
        analytics = status_monitor.get_usage_analytics(user_id)

        # Assert
        assert analytics["sendgrid"]["total_calls"] == 2
        assert analytics["sendgrid"]["success_rate"] == 0.5
        assert analytics["twitter"]["total_calls"] == 1
        assert analytics["twitter"]["success_rate"] == 1.0


class TestOAuthMiddleware:
    """Test OAuth validation middleware."""

    @pytest.mark.asyncio
    async def test_oauth_validation_middleware_success(self) -> None:
        """Test successful OAuth validation middleware."""
        # Arrange
        from app.ai_agents.mcp.oauth_integration import oauth_validation_middleware

        mock_request = MagicMock()
        mock_request.user_id = "test-user-123"
        mock_request.service_name = "sendgrid"

        with patch(
            "app.ai_agents.mcp.oauth_integration.get_valid_credentials_with_refresh"
        ) as mock_get:
            mock_get.return_value = {
                "access_token": "valid_token",
                "service_name": "sendgrid",
            }

            # Act
            result = await oauth_validation_middleware(mock_request)

            # Assert
            assert result is True
            assert hasattr(mock_request, "oauth_credentials")
            assert mock_request.oauth_credentials["access_token"] == "valid_token"

    @pytest.mark.asyncio
    async def test_oauth_validation_middleware_failure(self) -> None:
        """Test OAuth validation middleware with invalid credentials."""
        # Arrange
        from app.ai_agents.mcp.oauth_integration import oauth_validation_middleware

        mock_request = MagicMock()
        mock_request.user_id = "test-user-123"
        mock_request.service_name = "invalid_service"

        with patch(
            "app.ai_agents.mcp.oauth_integration.get_valid_credentials_with_refresh"
        ) as mock_get:
            mock_get.return_value = None

            # Act & Assert
            with pytest.raises(
                MCPAuthenticationError, match="Invalid or missing OAuth credentials"
            ):
                await oauth_validation_middleware(mock_request)


if __name__ == "__main__":
    pytest.main([__file__])
