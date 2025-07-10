"""
MCP Error Handler

This module provides comprehensive error handling for MCP operations, including:
- Specific exception classes for different types of MCP failures
- User-friendly error message generation
- Error context and debugging information
- Error categorization and recovery suggestions

Following PRD: Task 2.0 - Implementar Sistema de Manejo de Errores y Reintentos
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


class MCPErrorCategory(Enum):
    """Categories of MCP errors for better classification"""

    CONNECTION = "connection"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    OPERATION_FAILED = "operation_failed"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    UNKNOWN = "unknown"


class MCPErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BaseMCPError(Exception):
    """
    Base exception class for all MCP-related errors.

    Provides common functionality for error handling, logging,
    and user-friendly message generation.
    """

    def __init__(
        self,
        message: str,
        service_name: str = "",
        operation: str = "",
        category: MCPErrorCategory = MCPErrorCategory.UNKNOWN,
        severity: MCPErrorSeverity = MCPErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        user_friendly: bool = True,
    ):
        self.message = message
        self.service_name = service_name
        self.operation = operation
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.original_error = original_error
        self.timestamp = datetime.now()
        self.user_friendly = user_friendly

        # Generate error code for tracking
        self.error_code = self._generate_error_code()

        # Call parent constructor with detailed message
        super().__init__(self._build_detailed_message())

    def _generate_error_code(self) -> str:
        """Generate unique error code for tracking"""
        timestamp_str = self.timestamp.strftime("%Y%m%d%H%M%S")
        category_code = self.category.value.upper()[:4]
        service_code = self.service_name.upper()[:4] if self.service_name else "UNKN"
        return f"MCP-{category_code}-{service_code}-{timestamp_str}"

    def _build_detailed_message(self) -> str:
        """Build detailed error message for logging"""
        parts = [f"[{self.error_code}]", self.message]

        if self.service_name:
            parts.append(f"Service: {self.service_name}")

        if self.operation:
            parts.append(f"Operation: {self.operation}")

        if self.original_error:
            parts.append(f"Original: {str(self.original_error)}")

        return " | ".join(parts)

    def get_user_friendly_message(self) -> str:
        """Get user-friendly error message in English"""
        if not self.user_friendly:
            return self.message

        service_display = (
            self.service_name.replace("_", " ").title()
            if self.service_name
            else "the service"
        )

        friendly_messages = {
            MCPErrorCategory.CONNECTION: f"🔌 Oops, we couldn't connect to {service_display}. Please try again in a few moments.",
            MCPErrorCategory.AUTHENTICATION: f"🔐 There seems to be an issue with {service_display} credentials. Please check your OAuth configuration.",
            MCPErrorCategory.AUTHORIZATION: f"🚫 You don't have sufficient permissions to perform this action on {service_display}. Please contact your administrator.",
            MCPErrorCategory.RATE_LIMIT: f"⏱️ You've made too many requests to {service_display}. Please wait a moment and try again.",
            MCPErrorCategory.SERVICE_UNAVAILABLE: f"🚧 {service_display} is temporarily unavailable. Our team is already working to resolve this.",
            MCPErrorCategory.TIMEOUT: f"⏰ The operation on {service_display} is taking longer than expected. Please try again.",
            MCPErrorCategory.VALIDATION: f"📝 The provided data is not valid for {service_display}. Please review the information and try again.",
            MCPErrorCategory.OPERATION_FAILED: f"❌ We couldn't complete the operation on {service_display}. Please try again.",
            MCPErrorCategory.CONFIGURATION: f"⚙️ There's a configuration issue with {service_display}. Please contact technical support.",
            MCPErrorCategory.NETWORK: f"🌐 There's a network connectivity issue. Please check your internet connection and try again.",
            MCPErrorCategory.UNKNOWN: f"🤔 An unexpected error occurred with {service_display}. Our team has been automatically notified.",
        }

        return friendly_messages.get(self.category, self.message)

    def get_recovery_suggestions(self) -> List[str]:
        """Get recovery suggestions for the user"""
        suggestions = {
            MCPErrorCategory.CONNECTION: [
                "Check your internet connection",
                "Try again in 1-2 minutes",
                "Contact support if the problem persists",
            ],
            MCPErrorCategory.AUTHENTICATION: [
                "Check OAuth credentials in settings",
                "Re-authorize the integration in settings",
                "Contact administrator if you don't have access",
            ],
            MCPErrorCategory.AUTHORIZATION: [
                "Check user permissions in the service",
                "Contact administrator to grant permissions",
                "Review role configuration",
            ],
            MCPErrorCategory.RATE_LIMIT: [
                "Wait 1-5 minutes before trying again",
                "Reduce frequency of operations",
                "Contact support to increase limits",
            ],
            MCPErrorCategory.SERVICE_UNAVAILABLE: [
                "Try again in 5-10 minutes",
                "Check service status on their official page",
                "Contact support if the problem persists",
            ],
            MCPErrorCategory.TIMEOUT: [
                "Try again with smaller data",
                "Check your internet connection",
                "Contact support if the problem persists",
            ],
            MCPErrorCategory.VALIDATION: [
                "Review format of entered data",
                "Check required fields",
                "Consult service documentation",
            ],
            MCPErrorCategory.OPERATION_FAILED: [
                "Try again in a few moments",
                "Verify that the data is correct",
                "Contact support with error details",
            ],
            MCPErrorCategory.CONFIGURATION: [
                "Review configuration in admin panel",
                "Check environment variables",
                "Contact technical support",
            ],
            MCPErrorCategory.NETWORK: [
                "Check your internet connection",
                "Try from another network",
                "Contact network administrator",
            ],
            MCPErrorCategory.UNKNOWN: [
                "Try again in a few moments",
                "Contact support with error code",
                "Check logs for more details",
            ],
        }

        return suggestions.get(self.category, ["Contact technical support"])

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_friendly_message": self.get_user_friendly_message(),
            "service_name": self.service_name,
            "operation": self.operation,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "recovery_suggestions": self.get_recovery_suggestions(),
            "original_error": str(self.original_error) if self.original_error else None,
            "traceback": traceback.format_exc() if self.original_error else None,
        }

    def log_error(self, logger_instance: Optional[logging.Logger] = None) -> None:
        """Log error with appropriate level based on severity"""
        log_instance = logger_instance or logger

        # Create safe extra dict without 'message' field to avoid LogRecord conflicts
        error_dict = self.to_dict()
        safe_extra = {k: v for k, v in error_dict.items() if k != "message"}

        log_message = f"MCP Error [{self.severity.value.upper()}]: {self.message} | Code: {self.error_code}"

        if self.severity == MCPErrorSeverity.CRITICAL:
            log_instance.critical(log_message, extra=safe_extra)
        elif self.severity == MCPErrorSeverity.HIGH:
            log_instance.error(log_message, extra=safe_extra)
        elif self.severity == MCPErrorSeverity.MEDIUM:
            log_instance.warning(log_message, extra=safe_extra)
        else:
            log_instance.info(log_message, extra=safe_extra)


class MCPConnectionError(BaseMCPError):
    """Error connecting to MCP service"""

    def __init__(self, service_name: str, message: str = "", **kwargs):
        if not message:
            message = f"Failed to connect to {service_name} MCP service"
        super().__init__(
            message=message,
            service_name=service_name,
            category=MCPErrorCategory.CONNECTION,
            severity=MCPErrorSeverity.HIGH,
            **kwargs,
        )


class MCPAuthenticationError(BaseMCPError):
    """Authentication failure with MCP service"""

    def __init__(self, service_name: str, message: str = "", **kwargs):
        if not message:
            message = f"Authentication failed for {service_name}"
        super().__init__(
            message=message,
            service_name=service_name,
            category=MCPErrorCategory.AUTHENTICATION,
            severity=MCPErrorSeverity.HIGH,
            **kwargs,
        )


class MCPAuthorizationError(BaseMCPError):
    """Authorization failure - insufficient permissions"""

    def __init__(
        self, service_name: str, operation: str = "", message: str = "", **kwargs
    ):
        if not message:
            message = (
                f"Insufficient permissions for {operation} on {service_name}"
                if operation
                else f"Insufficient permissions for {service_name}"
            )
        super().__init__(
            message=message,
            service_name=service_name,
            operation=operation,
            category=MCPErrorCategory.AUTHORIZATION,
            severity=MCPErrorSeverity.MEDIUM,
            **kwargs,
        )


class MCPRateLimitError(BaseMCPError):
    """Rate limit exceeded"""

    def __init__(
        self,
        service_name: str,
        retry_after: Optional[int] = None,
        message: str = "",
        **kwargs,
    ):
        if not message:
            retry_msg = f" Retry after {retry_after} seconds." if retry_after else ""
            message = f"Rate limit exceeded for {service_name}.{retry_msg}"

        context = kwargs.get("context", {})
        if retry_after:
            context["retry_after_seconds"] = retry_after
        kwargs["context"] = context

        super().__init__(
            message=message,
            service_name=service_name,
            category=MCPErrorCategory.RATE_LIMIT,
            severity=MCPErrorSeverity.MEDIUM,
            **kwargs,
        )


class MCPServiceUnavailableError(BaseMCPError):
    """MCP service is temporarily unavailable"""

    def __init__(self, service_name: str, message: str = "", **kwargs):
        if not message:
            message = f"{service_name} service is temporarily unavailable"
        super().__init__(
            message=message,
            service_name=service_name,
            category=MCPErrorCategory.SERVICE_UNAVAILABLE,
            severity=MCPErrorSeverity.HIGH,
            **kwargs,
        )


class MCPTimeoutError(BaseMCPError):
    """Operation timeout"""

    def __init__(
        self,
        service_name: str,
        operation: str = "",
        timeout_seconds: Optional[float] = None,
        message: str = "",
        **kwargs,
    ):
        if not message:
            timeout_msg = f" after {timeout_seconds}s" if timeout_seconds else ""
            message = (
                f"Timeout in {operation} operation on {service_name}{timeout_msg}"
                if operation
                else f"Timeout on {service_name}{timeout_msg}"
            )

        context = kwargs.get("context", {})
        if timeout_seconds:
            context["timeout_seconds"] = timeout_seconds
        kwargs["context"] = context

        super().__init__(
            message=message,
            service_name=service_name,
            operation=operation,
            category=MCPErrorCategory.TIMEOUT,
            severity=MCPErrorSeverity.MEDIUM,
            **kwargs,
        )


class MCPValidationError(BaseMCPError):
    """Data validation error"""

    def __init__(self, service_name: str, field: str = "", message: str = "", **kwargs):
        if not message:
            message = (
                f"Validation error for field '{field}' on {service_name}"
                if field
                else f"Data validation error on {service_name}"
            )

        context = kwargs.get("context", {})
        if field:
            context["field"] = field
        kwargs["context"] = context

        super().__init__(
            message=message,
            service_name=service_name,
            category=MCPErrorCategory.VALIDATION,
            severity=MCPErrorSeverity.LOW,
            **kwargs,
        )


class MCPOperationError(BaseMCPError):
    """General operation failure"""

    def __init__(
        self, service_name: str, operation: str = "", message: str = "", **kwargs
    ):
        if not message:
            message = (
                f"Operation '{operation}' failed on {service_name}"
                if operation
                else f"Operation failed on {service_name}"
            )
        super().__init__(
            message=message,
            service_name=service_name,
            operation=operation,
            category=MCPErrorCategory.OPERATION_FAILED,
            severity=MCPErrorSeverity.MEDIUM,
            **kwargs,
        )


class MCPConfigurationError(BaseMCPError):
    """Configuration or setup error"""

    def __init__(
        self, service_name: str, config_key: str = "", message: str = "", **kwargs
    ):
        if not message:
            message = (
                f"Configuration error for '{config_key}' on {service_name}"
                if config_key
                else f"Configuration error on {service_name}"
            )

        context = kwargs.get("context", {})
        if config_key:
            context["config_key"] = config_key
        kwargs["context"] = context

        super().__init__(
            message=message,
            service_name=service_name,
            category=MCPErrorCategory.CONFIGURATION,
            severity=MCPErrorSeverity.HIGH,
            **kwargs,
        )


class MCPNetworkError(BaseMCPError):
    """Network connectivity error"""

    def __init__(self, service_name: str, message: str = "", **kwargs):
        if not message:
            message = f"Network connectivity error for {service_name}"
        super().__init__(
            message=message,
            service_name=service_name,
            category=MCPErrorCategory.NETWORK,
            severity=MCPErrorSeverity.HIGH,
            **kwargs,
        )


class MCPErrorHandler:
    """
    Central error handler for MCP operations.

    Provides methods for error classification, user-friendly message generation,
    and error recovery suggestions.
    """

    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        self.logger = logger_instance or logger
        self.error_counts = {}  # Track error counts by service
        self.last_errors = {}  # Track last error by service for debugging

    def classify_error(
        self,
        error: Exception,
        service_name: str = "",
        operation: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> BaseMCPError:
        """
        Classify a raw exception into an appropriate MCP error type.

        Args:
            error: The original exception
            service_name: Name of the MCP service
            operation: Operation being performed
            context: Additional context information

        Returns:
            BaseMCPError: Classified MCP error
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Classification logic based on error content
        if "timeout" in error_str or "timed out" in error_str:
            return MCPTimeoutError(
                service_name=service_name,
                operation=operation,
                context=context,
                original_error=error,
            )

        elif (
            "connection" in error_str
            or "connect" in error_str
            or error_type in ["connectionerror", "httperror"]
        ):
            return MCPConnectionError(
                service_name=service_name, context=context, original_error=error
            )

        elif "auth" in error_str or "unauthorized" in error_str or "401" in error_str:
            return MCPAuthenticationError(
                service_name=service_name, context=context, original_error=error
            )

        elif (
            "forbidden" in error_str or "403" in error_str or "permission" in error_str
        ):
            return MCPAuthorizationError(
                service_name=service_name,
                operation=operation,
                context=context,
                original_error=error,
            )

        elif (
            "rate limit" in error_str
            or "too many requests" in error_str
            or "429" in error_str
        ):
            return MCPRateLimitError(
                service_name=service_name, context=context, original_error=error
            )

        elif (
            "unavailable" in error_str
            or "503" in error_str
            or "502" in error_str
            or "down" in error_str
        ):
            return MCPServiceUnavailableError(
                service_name=service_name, context=context, original_error=error
            )

        elif "validation" in error_str or "invalid" in error_str or "400" in error_str:
            return MCPValidationError(
                service_name=service_name, context=context, original_error=error
            )

        elif "network" in error_str or "dns" in error_str:
            return MCPNetworkError(
                service_name=service_name, context=context, original_error=error
            )

        elif "config" in error_str or "setup" in error_str:
            return MCPConfigurationError(
                service_name=service_name, context=context, original_error=error
            )

        else:
            # Default to operation error
            return MCPOperationError(
                service_name=service_name,
                operation=operation,
                message=str(error),
                context=context,
                original_error=error,
            )

    def handle_error(
        self,
        error: Union[Exception, BaseMCPError],
        service_name: str = "",
        operation: str = "",
        context: Optional[Dict[str, Any]] = None,
        log_error: bool = True,
    ) -> BaseMCPError:
        """
        Handle an error by classifying, logging, and tracking it.

        Args:
            error: The error to handle
            service_name: Name of the MCP service
            operation: Operation being performed
            context: Additional context information
            log_error: Whether to log the error

        Returns:
            BaseMCPError: Processed MCP error
        """
        # Classify error if it's not already an MCP error
        if isinstance(error, BaseMCPError):
            mcp_error = error
        else:
            mcp_error = self.classify_error(error, service_name, operation, context)

        # Track error statistics
        service_key = service_name or "unknown"
        self.error_counts[service_key] = self.error_counts.get(service_key, 0) + 1
        self.last_errors[service_key] = mcp_error

        # Log error if requested
        if log_error:
            mcp_error.log_error(self.logger)

        return mcp_error

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "errors_by_service": dict(self.error_counts),
            "last_errors": {
                service: error.to_dict() for service, error in self.last_errors.items()
            },
            "timestamp": datetime.now().isoformat(),
        }

    def reset_stats(self) -> None:
        """Reset error statistics"""
        self.error_counts.clear()
        self.last_errors.clear()

    def should_retry(
        self, error: BaseMCPError, attempt: int, max_attempts: int = 3
    ) -> bool:
        """
        Determine if an operation should be retried based on error type.

        Args:
            error: The MCP error
            attempt: Current attempt number (1-based)
            max_attempts: Maximum number of attempts

        Returns:
            bool: Whether to retry the operation
        """
        if attempt >= max_attempts:
            return False

        # Don't retry certain error types
        non_retryable = {
            MCPErrorCategory.AUTHENTICATION,
            MCPErrorCategory.AUTHORIZATION,
            MCPErrorCategory.VALIDATION,
            MCPErrorCategory.CONFIGURATION,
        }

        if error.category in non_retryable:
            return False

        # Retry other error types
        return True


# Global error handler instance
_error_handler: Optional[MCPErrorHandler] = None


def get_error_handler() -> MCPErrorHandler:
    """Get the global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = MCPErrorHandler()
    return _error_handler


def create_user_friendly_error(
    service_name: str,
    category: MCPErrorCategory = MCPErrorCategory.UNKNOWN,
    operation: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a user-friendly error message for display to end users.

    Args:
        service_name: Name of the service that failed
        category: Category of error
        operation: Operation that was being performed
        context: Additional context

    Returns:
        str: User-friendly error message in English
    """
    # Create a temporary error to get user-friendly message
    temp_error = BaseMCPError(
        message="Temporary error for message generation",
        service_name=service_name,
        operation=operation,
        category=category,
        context=context,
    )

    return temp_error.get_user_friendly_message()


# Convenience functions for common error types
def connection_error(service_name: str, **kwargs) -> MCPConnectionError:
    """Create a connection error"""
    return MCPConnectionError(service_name=service_name, **kwargs)


def auth_error(service_name: str, **kwargs) -> MCPAuthenticationError:
    """Create an authentication error"""
    return MCPAuthenticationError(service_name=service_name, **kwargs)


def timeout_error(service_name: str, operation: str = "", **kwargs) -> MCPTimeoutError:
    """Create a timeout error"""
    return MCPTimeoutError(service_name=service_name, operation=operation, **kwargs)


def rate_limit_error(service_name: str, **kwargs) -> MCPRateLimitError:
    """Create a rate limit error"""
    return MCPRateLimitError(service_name=service_name, **kwargs)


def service_unavailable_error(
    service_name: str, **kwargs
) -> MCPServiceUnavailableError:
    """Create a service unavailable error"""
    return MCPServiceUnavailableError(service_name=service_name, **kwargs)
