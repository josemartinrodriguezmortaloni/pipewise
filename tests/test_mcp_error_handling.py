"""
Unit tests for MCP error handling and retry logic.

This module tests error handling functionality including:
- Exponential backoff retry mechanisms
- Circuit breaker patterns
- Error classification and handling
- Timeout and connection error scenarios
- User-friendly error message generation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Dict, Any, List, Optional
import asyncio
import time
from datetime import datetime, timedelta

from app.ai_agents.mcp.error_handler import (
    MCPConnectionError,
    MCPOperationError,
    MCPTimeoutError,
    MCPConfigurationError,
    MCPRateLimitError,
    MCPAuthenticationError,
    retry_mcp_operation,
    CircuitBreaker,
    generate_user_friendly_error_message,
    exponential_backoff_with_jitter,
)


class TestMCPErrorClasses:
    """Test MCP-specific error classes."""

    def test_mcp_connection_error(self) -> None:
        """Test MCPConnectionError creation and properties."""
        # Arrange
        error_message = "Failed to connect to SendGrid MCP"
        service_name = "sendgrid"

        # Act
        error = MCPConnectionError(error_message, service_name=service_name)

        # Assert
        assert str(error) == error_message
        assert error.service_name == service_name
        assert isinstance(error, Exception)

    def test_mcp_operation_error(self) -> None:
        """Test MCPOperationError creation and properties."""
        # Arrange
        error_message = "Tool execution failed"
        operation = "send_email"
        details = {"error_code": "invalid_recipient"}

        # Act
        error = MCPOperationError(error_message, operation=operation, details=details)

        # Assert
        assert str(error) == error_message
        assert error.operation == operation
        assert error.details == details

    def test_mcp_timeout_error(self) -> None:
        """Test MCPTimeoutError creation and properties."""
        # Arrange
        error_message = "Operation timed out after 30 seconds"
        timeout_duration = 30.0

        # Act
        error = MCPTimeoutError(error_message, timeout_duration=timeout_duration)

        # Assert
        assert str(error) == error_message
        assert error.timeout_duration == timeout_duration

    def test_mcp_configuration_error(self) -> None:
        """Test MCPConfigurationError creation and properties."""
        # Arrange
        error_message = "Missing required configuration"
        config_key = "api_key"

        # Act
        error = MCPConfigurationError(error_message, config_key=config_key)

        # Assert
        assert str(error) == error_message
        assert error.config_key == config_key

    def test_mcp_rate_limit_error(self) -> None:
        """Test MCPRateLimitError creation and properties."""
        # Arrange
        error_message = "Rate limit exceeded"
        retry_after = 300  # 5 minutes

        # Act
        error = MCPRateLimitError(error_message, retry_after=retry_after)

        # Assert
        assert str(error) == error_message
        assert error.retry_after == retry_after

    def test_mcp_authentication_error(self) -> None:
        """Test MCPAuthenticationError creation and properties."""
        # Arrange
        error_message = "Invalid OAuth token"
        service_name = "twitter"

        # Act
        error = MCPAuthenticationError(error_message, service_name=service_name)

        # Assert
        assert str(error) == error_message
        assert error.service_name == service_name


class TestRetryMechanism:
    """Test retry mechanism with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_decorator_success(self) -> None:
        """Test successful operation with retry decorator."""

        # Arrange
        @retry_mcp_operation(max_attempts=3)
        async def mock_operation() -> Dict[str, Any]:
            return {"success": True, "result": "Operation completed"}

        # Act
        result = await mock_operation()

        # Assert
        assert result["success"] is True
        assert result["result"] == "Operation completed"

    @pytest.mark.asyncio
    async def test_retry_decorator_eventual_success(self) -> None:
        """Test operation that fails twice then succeeds."""
        # Arrange
        call_count = 0

        @retry_mcp_operation(max_attempts=3, base_delay=0.01)  # Fast retry for testing
        async def mock_operation() -> Dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise MCPConnectionError("Temporary connection error")
            return {"success": True, "attempt": call_count}

        # Act
        result = await mock_operation()

        # Assert
        assert result["success"] is True
        assert result["attempt"] == 3
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_decorator_max_attempts_exceeded(self) -> None:
        """Test operation that exceeds maximum retry attempts."""

        # Arrange
        @retry_mcp_operation(max_attempts=2, base_delay=0.01)
        async def mock_operation() -> Dict[str, Any]:
            raise MCPConnectionError("Persistent connection error")

        # Act & Assert
        with pytest.raises(MCPConnectionError, match="Persistent connection error"):
            await mock_operation()

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self) -> None:
        """Test exponential backoff delay calculation."""
        # Arrange
        base_delay = 1.0
        max_delay = 10.0

        # Act
        delay1 = exponential_backoff_with_jitter(1, base_delay, max_delay)
        delay2 = exponential_backoff_with_jitter(2, base_delay, max_delay)
        delay3 = exponential_backoff_with_jitter(3, base_delay, max_delay)

        # Assert
        assert 0.5 <= delay1 <= 1.5  # Base delay with jitter
        assert 1.0 <= delay2 <= 3.0  # 2^1 * base_delay with jitter
        assert 2.0 <= delay3 <= 6.0  # 2^2 * base_delay with jitter

    @pytest.mark.asyncio
    async def test_retry_specific_error_types(self) -> None:
        """Test retry behavior for specific error types."""
        # Arrange
        call_count = 0

        @retry_mcp_operation(
            max_attempts=3, base_delay=0.01, retryable_errors=[MCPConnectionError]
        )
        async def mock_operation() -> Dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise MCPConnectionError("Connection failed")  # Should retry
            elif call_count == 2:
                raise MCPAuthenticationError("Auth failed")  # Should not retry
            return {"success": True}

        # Act & Assert
        with pytest.raises(MCPAuthenticationError, match="Auth failed"):
            await mock_operation()

        assert call_count == 2  # Should have stopped after auth error

    @pytest.mark.asyncio
    async def test_retry_rate_limit_handling(self) -> None:
        """Test retry behavior with rate limit errors."""
        # Arrange
        call_count = 0

        @retry_mcp_operation(max_attempts=3, base_delay=0.01)
        async def mock_operation() -> Dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise MCPRateLimitError("Rate limit exceeded", retry_after=1)
            return {"success": True, "call_count": call_count}

        # Act
        start_time = time.time()
        result = await mock_operation()
        elapsed_time = time.time() - start_time

        # Assert
        assert result["success"] is True
        assert result["call_count"] == 2
        assert elapsed_time >= 0.01  # Should have waited at least base delay


class TestCircuitBreakerPattern:
    """Test circuit breaker pattern for failing services."""

    @pytest.fixture
    def circuit_breaker(self) -> CircuitBreaker:
        """Create a circuit breaker instance."""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,  # 1 second for testing
            expected_exception=MCPConnectionError,
        )

    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """Test circuit breaker in closed state (normal operation)."""

        # Arrange
        async def successful_operation() -> str:
            return "success"

        # Act
        result = await circuit_breaker.call(successful_operation)

        # Assert
        assert result == "success"
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_state(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """Test circuit breaker transitioning to open state."""

        # Arrange
        async def failing_operation() -> str:
            raise MCPConnectionError("Service unavailable")

        # Act - Trigger failures to open circuit
        for _ in range(3):
            with pytest.raises(MCPConnectionError):
                await circuit_breaker.call(failing_operation)

        # Circuit should be open now
        assert circuit_breaker.state == "open"

        # Next call should fail immediately without calling function
        with pytest.raises(MCPConnectionError, match="Circuit breaker is open"):
            await circuit_breaker.call(failing_operation)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_state(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """Test circuit breaker half-open state and recovery."""
        # Arrange
        call_count = 0

        async def recovering_operation() -> str:
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise MCPConnectionError("Still failing")
            return "recovered"

        # Act - First open the circuit
        for _ in range(3):
            with pytest.raises(MCPConnectionError):
                await circuit_breaker.call(recovering_operation)

        assert circuit_breaker.state == "open"

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Next call should transition to half-open
        result = await circuit_breaker.call(recovering_operation)

        # Assert
        assert result == "recovered"
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_reset_after_success(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """Test circuit breaker reset after successful operation."""
        # Arrange
        call_count = 0

        async def intermittent_operation() -> str:
            nonlocal call_count
            call_count += 1
            if call_count in [1, 2]:  # Fail first two times
                raise MCPConnectionError("Intermittent failure")
            return "success"

        # Act - Have some failures
        for _ in range(2):
            with pytest.raises(MCPConnectionError):
                await circuit_breaker.call(intermittent_operation)

        assert circuit_breaker.failure_count == 2

        # Successful call should reset failure count
        result = await circuit_breaker.call(intermittent_operation)

        # Assert
        assert result == "success"
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == "closed"


class TestUserFriendlyErrorMessages:
    """Test generation of user-friendly error messages."""

    def test_connection_error_message(self) -> None:
        """Test user-friendly message for connection errors."""
        # Arrange
        error = MCPConnectionError("Connection refused", service_name="sendgrid")

        # Act
        message = generate_user_friendly_error_message(error)

        # Assert
        assert "Oops, there was an error connecting to SendGrid" in message
        assert "Please try again in a few moments" in message

    def test_authentication_error_message(self) -> None:
        """Test user-friendly message for authentication errors."""
        # Arrange
        error = MCPAuthenticationError("Invalid token", service_name="twitter")

        # Act
        message = generate_user_friendly_error_message(error)

        # Assert
        assert "authentication issue with Twitter" in message
        assert "Please check your account connection" in message

    def test_rate_limit_error_message(self) -> None:
        """Test user-friendly message for rate limit errors."""
        # Arrange
        error = MCPRateLimitError("Rate limit exceeded", retry_after=300)

        # Act
        message = generate_user_friendly_error_message(error)

        # Assert
        assert "rate limit" in message
        assert "5 minutes" in message  # 300 seconds = 5 minutes

    def test_timeout_error_message(self) -> None:
        """Test user-friendly message for timeout errors."""
        # Arrange
        error = MCPTimeoutError("Operation timed out", timeout_duration=30.0)

        # Act
        message = generate_user_friendly_error_message(error)

        # Assert
        assert "took too long to respond" in message
        assert "30 seconds" in message

    def test_configuration_error_message(self) -> None:
        """Test user-friendly message for configuration errors."""
        # Arrange
        error = MCPConfigurationError("Missing API key", config_key="api_key")

        # Act
        message = generate_user_friendly_error_message(error)

        # Assert
        assert "configuration issue" in message
        assert "contact support" in message

    def test_generic_operation_error_message(self) -> None:
        """Test user-friendly message for generic operation errors."""
        # Arrange
        error = MCPOperationError("Tool execution failed", operation="send_email")

        # Act
        message = generate_user_friendly_error_message(error)

        # Assert
        assert "error while performing" in message
        assert "send_email" in message

    def test_unknown_error_message(self) -> None:
        """Test user-friendly message for unknown error types."""
        # Arrange
        error = ValueError("Some unexpected error")

        # Act
        message = generate_user_friendly_error_message(error)

        # Assert
        assert "unexpected error occurred" in message
        assert "please try again" in message


class TestErrorContextAndLogging:
    """Test error context capture and logging."""

    @pytest.mark.asyncio
    async def test_error_context_capture(self) -> None:
        """Test capturing error context information."""
        # Arrange
        operation_context = {
            "service": "sendgrid",
            "operation": "send_email",
            "user_id": "test-user-123",
            "timestamp": datetime.now().isoformat(),
        }

        # Act
        error = MCPOperationError(
            "Email sending failed",
            operation="send_email",
            details={"context": operation_context},
        )

        # Assert
        assert error.details["context"]["service"] == "sendgrid"
        assert error.details["context"]["user_id"] == "test-user-123"
        assert "timestamp" in error.details["context"]

    @pytest.mark.asyncio
    async def test_error_logging_integration(self) -> None:
        """Test integration with logging system."""
        # Arrange
        with patch("app.ai_agents.mcp.error_handler.logger") as mock_logger:
            error = MCPConnectionError("Connection failed", service_name="twitter")

            # Act
            from app.ai_agents.mcp.error_handler import log_mcp_error

            log_mcp_error(
                error, context={"user_id": "test-user", "operation": "post_tweet"}
            )

            # Assert
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "Connection failed" in call_args[0][0]
            assert call_args[1]["extra"]["service_name"] == "twitter"

    def test_error_aggregation_and_tracking(self) -> None:
        """Test error aggregation for monitoring and alerting."""
        # Arrange
        from app.ai_agents.mcp.error_handler import ErrorTracker

        tracker = ErrorTracker()

        # Act - Record multiple errors
        tracker.record_error("sendgrid", MCPConnectionError("Connection failed"))
        tracker.record_error("sendgrid", MCPConnectionError("Connection failed"))
        tracker.record_error("twitter", MCPRateLimitError("Rate limit exceeded"))

        # Assert
        stats = tracker.get_error_stats()
        assert stats["sendgrid"]["total_errors"] == 2
        assert stats["sendgrid"]["error_types"]["MCPConnectionError"] == 2
        assert stats["twitter"]["total_errors"] == 1
        assert stats["twitter"]["error_types"]["MCPRateLimitError"] == 1

    def test_error_threshold_alerting(self) -> None:
        """Test alerting when error thresholds are exceeded."""
        # Arrange
        from app.ai_agents.mcp.error_handler import ErrorThresholdMonitor

        monitor = ErrorThresholdMonitor(
            threshold=3, time_window=300
        )  # 3 errors in 5 minutes

        # Act - Record errors exceeding threshold
        for i in range(4):
            monitor.record_error("sendgrid", MCPConnectionError(f"Error {i}"))

        # Assert
        alerts = monitor.get_active_alerts()
        assert len(alerts) > 0
        assert alerts[0]["service"] == "sendgrid"
        assert alerts[0]["error_count"] == 4
        assert alerts[0]["threshold_exceeded"] is True


class TestErrorRecoveryStrategies:
    """Test error recovery and fallback strategies."""

    @pytest.mark.asyncio
    async def test_service_fallback_on_error(self) -> None:
        """Test fallback to alternative service on error."""
        # Arrange
        primary_service_calls = 0
        fallback_service_calls = 0

        async def primary_service() -> Dict[str, Any]:
            nonlocal primary_service_calls
            primary_service_calls += 1
            raise MCPConnectionError("Primary service unavailable")

        async def fallback_service() -> Dict[str, Any]:
            nonlocal fallback_service_calls
            fallback_service_calls += 1
            return {"success": True, "service": "fallback"}

        from app.ai_agents.mcp.error_handler import with_fallback

        # Act
        result = await with_fallback(primary_service, fallback_service)

        # Assert
        assert result["success"] is True
        assert result["service"] == "fallback"
        assert primary_service_calls == 1
        assert fallback_service_calls == 1

    @pytest.mark.asyncio
    async def test_graceful_degradation(self) -> None:
        """Test graceful degradation when services are unavailable."""

        # Arrange
        async def failing_enhanced_service() -> Dict[str, Any]:
            raise MCPConnectionError("Enhanced service unavailable")

        async def basic_service() -> Dict[str, Any]:
            return {"success": True, "features": "basic"}

        from app.ai_agents.mcp.error_handler import graceful_degradation

        # Act
        result = await graceful_degradation(failing_enhanced_service, basic_service)

        # Assert
        assert result["success"] is True
        assert result["features"] == "basic"

    def test_error_recovery_metrics(self) -> None:
        """Test tracking of error recovery metrics."""
        # Arrange
        from app.ai_agents.mcp.error_handler import RecoveryMetrics

        metrics = RecoveryMetrics()

        # Act
        metrics.record_recovery_attempt("sendgrid", "retry", success=False)
        metrics.record_recovery_attempt("sendgrid", "retry", success=True)
        metrics.record_recovery_attempt("sendgrid", "fallback", success=True)

        # Assert
        stats = metrics.get_recovery_stats("sendgrid")
        assert stats["retry"]["attempts"] == 2
        assert stats["retry"]["success_rate"] == 0.5
        assert stats["fallback"]["attempts"] == 1
        assert stats["fallback"]["success_rate"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__])
