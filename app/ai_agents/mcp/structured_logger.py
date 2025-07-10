"""
Structured logging system for MCP operations.

This module provides comprehensive structured logging for all MCP activities including:
- Connection success/failure logging with metrics
- Usage tracking by service and agent
- OAuth authentication error logging
- Performance metrics and timing
- Operation context and correlation tracking
"""

import logging
import json
import time
import uuid
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
from contextlib import contextmanager
import asyncio
from collections import defaultdict, deque
import threading

from app.ai_agents.mcp.error_handler import (
    MCPConnectionError,
    MCPOperationError,
    MCPTimeoutError,
    MCPAuthenticationError,
    MCPRateLimitError,
)


class LogLevel(Enum):
    """Log level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class OperationType(Enum):
    """Types of MCP operations."""

    CONNECTION = "connection"
    TOOL_EXECUTION = "tool_execution"
    AUTHENTICATION = "authentication"
    HEALTH_CHECK = "health_check"
    CONFIGURATION = "configuration"
    AGENT_WORKFLOW = "agent_workflow"
    ERROR_RECOVERY = "error_recovery"
    RATE_LIMITING = "rate_limiting"


@dataclass
class LogContext:
    """Context information for structured logging."""

    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    service_name: Optional[str] = None
    agent_type: Optional[str] = None
    operation_type: Optional[OperationType] = None
    operation_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None

    # Performance metrics
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None

    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        result = asdict(self)

        # Convert enums to strings
        if self.operation_type:
            result["operation_type"] = self.operation_type.value

        # Calculate duration if not set
        if self.start_time and self.end_time and not self.duration_ms:
            result["duration_ms"] = round((self.end_time - self.start_time) * 1000, 2)

        return result


@dataclass
class ConnectionLog:
    """Log entry for MCP connection events."""

    service_name: str
    operation: str  # connect, disconnect, retry
    success: bool
    timestamp: datetime
    response_time_ms: float
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    attempt_number: int = 1
    context: Optional[LogContext] = None

    # Connection specific metrics
    connection_pool_size: Optional[int] = None
    active_connections: Optional[int] = None
    max_connections: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        if self.context:
            result["context"] = self.context.to_dict()
        return result


@dataclass
class UsageLog:
    """Log entry for MCP usage tracking."""

    service_name: str
    agent_type: str
    operation: str
    tool_name: Optional[str]
    success: bool
    timestamp: datetime
    execution_time_ms: float
    user_id: Optional[str] = None
    error_message: Optional[str] = None
    context: Optional[LogContext] = None

    # Usage specific metrics
    input_size_bytes: Optional[int] = None
    output_size_bytes: Optional[int] = None
    api_calls_count: int = 1
    rate_limit_remaining: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        if self.context:
            result["context"] = self.context.to_dict()
        return result


@dataclass
class AuthenticationLog:
    """Log entry for OAuth authentication events."""

    service_name: str
    operation: str  # authenticate, refresh, revoke
    success: bool
    timestamp: datetime
    user_id: str
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    context: Optional[LogContext] = None

    # Authentication specific details
    token_type: Optional[str] = None  # access_token, refresh_token
    expires_in: Optional[int] = None
    scopes: Optional[List[str]] = None
    provider_response_time_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        if self.context:
            result["context"] = self.context.to_dict()
        return result


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations."""

    service_name: str
    operation_type: str
    timestamp: datetime

    # Timing metrics
    response_time_ms: float
    processing_time_ms: Optional[float] = None
    network_time_ms: Optional[float] = None
    queue_time_ms: Optional[float] = None

    # Resource metrics
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None

    # Throughput metrics
    requests_per_second: Optional[float] = None
    concurrent_operations: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        return result


class MCPStructuredLogger:
    """Main structured logging system for MCP operations."""

    def __init__(
        self,
        logger_name: str = "mcp_operations",
        log_level: LogLevel = LogLevel.INFO,
        enable_metrics: bool = True,
        enable_usage_tracking: bool = True,
        metrics_retention_hours: int = 24,
    ):
        """
        Initialize the structured logger.

        Args:
            logger_name: Name for the logger instance
            log_level: Minimum log level to process
            enable_metrics: Whether to collect performance metrics
            enable_usage_tracking: Whether to track usage statistics
            metrics_retention_hours: How long to retain metrics in memory
        """
        self.logger_name = logger_name
        self.log_level = log_level
        self.enable_metrics = enable_metrics
        self.enable_usage_tracking = enable_usage_tracking
        self.metrics_retention_hours = metrics_retention_hours

        # Setup core logger
        self.logger = logging.getLogger(logger_name)
        self.setup_logger()

        # Context management
        self._context_stack: List[LogContext] = []
        self._context_lock = threading.RLock()

        # In-memory storage for metrics and analytics
        self.connection_logs: deque = deque(maxlen=10000)
        self.usage_logs: deque = deque(maxlen=50000)
        self.auth_logs: deque = deque(maxlen=5000)
        self.performance_metrics: deque = deque(maxlen=20000)

        # Usage statistics
        self.usage_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "total_execution_time_ms": 0,
                "avg_execution_time_ms": 0,
                "last_operation": None,
                "error_count_by_type": defaultdict(int),
            }
        )

        # Connection statistics
        self.connection_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "total_connections": 0,
                "successful_connections": 0,
                "failed_connections": 0,
                "avg_response_time_ms": 0,
                "current_status": "unknown",
                "last_connection_attempt": None,
            }
        )

        # Start cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self.start_cleanup_task()

    def setup_logger(self) -> None:
        """Setup the core logger with structured formatting."""

        # Create custom formatter for structured JSON logs
        class StructuredFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                # Create base log entry
                log_entry = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }

                # Add extra fields if present
                extra_fields = getattr(record, "extra_fields", None)
                if extra_fields:
                    log_entry.update(extra_fields)

                # Add exception info if present
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)

                return json.dumps(log_entry, default=str)

        # Configure logger
        self.logger.setLevel(getattr(logging, self.log_level.value))

        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Add console handler with structured formatter
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(console_handler)

        # Prevent propagation to avoid double logging
        self.logger.propagate = False

    @contextmanager
    def operation_context(
        self,
        operation_type: OperationType,
        service_name: Optional[str] = None,
        agent_type: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Context manager for operation logging.

        Usage:
            with logger.operation_context(OperationType.TOOL_EXECUTION, service_name="sendgrid"):
                # Your operation code here
                pass
        """
        context = LogContext(
            operation_type=operation_type,
            service_name=service_name,
            agent_type=agent_type,
            user_id=user_id,
            start_time=time.time(),
            **kwargs,
        )

        with self._context_lock:
            self._context_stack.append(context)

        try:
            yield context
        finally:
            context.end_time = time.time()
            if context.start_time is not None:
                context.duration_ms = (context.end_time - context.start_time) * 1000

            with self._context_lock:
                if self._context_stack and self._context_stack[-1] == context:
                    self._context_stack.pop()

    def get_current_context(self) -> Optional[LogContext]:
        """Get the current operation context."""
        with self._context_lock:
            return self._context_stack[-1] if self._context_stack else None

    def log_connection(
        self,
        service_name: str,
        operation: str,
        success: bool,
        response_time_ms: float,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        attempt_number: int = 1,
        **kwargs,
    ) -> None:
        """Log MCP connection events."""
        context = self.get_current_context()

        connection_log = ConnectionLog(
            service_name=service_name,
            operation=operation,
            success=success,
            timestamp=datetime.now(),
            response_time_ms=response_time_ms,
            error_message=error_message,
            error_type=error_type,
            attempt_number=attempt_number,
            context=context,
            **kwargs,
        )

        # Store in memory for analytics
        self.connection_logs.append(connection_log)

        # Update connection statistics
        stats = self.connection_stats[service_name]
        stats["total_connections"] += 1
        if success:
            stats["successful_connections"] += 1
            stats["current_status"] = "connected"
        else:
            stats["failed_connections"] += 1
            stats["current_status"] = "failed"

        # Update average response time
        total_successful = stats["successful_connections"]
        if total_successful > 0:
            current_avg = stats["avg_response_time_ms"]
            stats["avg_response_time_ms"] = (
                current_avg * (total_successful - 1) + response_time_ms
            ) / total_successful

        stats["last_connection_attempt"] = datetime.now().isoformat()

        # Log the event
        log_level = LogLevel.INFO if success else LogLevel.ERROR
        self._log_structured(
            log_level,
            f"MCP {operation} - {service_name}",
            {
                "event_type": "connection",
                "service_name": service_name,
                "operation": operation,
                "success": success,
                "response_time_ms": response_time_ms,
                "attempt_number": attempt_number,
                "error_message": error_message,
                "error_type": error_type,
            },
        )

    def log_usage(
        self,
        service_name: str,
        agent_type: str,
        operation: str,
        tool_name: Optional[str],
        success: bool,
        execution_time_ms: float,
        user_id: Optional[str] = None,
        error_message: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Log MCP usage events."""
        if not self.enable_usage_tracking:
            return

        context = self.get_current_context()

        usage_log = UsageLog(
            service_name=service_name,
            agent_type=agent_type,
            operation=operation,
            tool_name=tool_name,
            success=success,
            timestamp=datetime.now(),
            execution_time_ms=execution_time_ms,
            user_id=user_id,
            error_message=error_message,
            context=context,
            **kwargs,
        )

        # Store in memory for analytics
        self.usage_logs.append(usage_log)

        # Update usage statistics
        key = f"{service_name}:{agent_type}"
        stats = self.usage_stats[key]
        stats["total_operations"] += 1
        stats["total_execution_time_ms"] += execution_time_ms

        if success:
            stats["successful_operations"] += 1
        else:
            stats["failed_operations"] += 1
            if error_message:
                # Extract error type from error message or exception
                error_type = (
                    error_message.split(":")[0] if ":" in error_message else "unknown"
                )
                stats["error_count_by_type"][error_type] += 1

        # Update average execution time
        if stats["total_operations"] > 0:
            stats["avg_execution_time_ms"] = (
                stats["total_execution_time_ms"] / stats["total_operations"]
            )

        stats["last_operation"] = datetime.now().isoformat()

        # Log the event
        log_level = LogLevel.INFO if success else LogLevel.WARNING
        self._log_structured(
            log_level,
            f"MCP usage - {service_name} - {operation}",
            {
                "event_type": "usage",
                "service_name": service_name,
                "agent_type": agent_type,
                "operation": operation,
                "tool_name": tool_name,
                "success": success,
                "execution_time_ms": execution_time_ms,
                "user_id": user_id,
                "error_message": error_message,
            },
        )

    def log_authentication(
        self,
        service_name: str,
        operation: str,
        success: bool,
        user_id: str,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Log OAuth authentication events."""
        context = self.get_current_context()

        auth_log = AuthenticationLog(
            service_name=service_name,
            operation=operation,
            success=success,
            timestamp=datetime.now(),
            user_id=user_id,
            error_message=error_message,
            error_code=error_code,
            context=context,
            **kwargs,
        )

        # Store in memory for analytics
        self.auth_logs.append(auth_log)

        # Log the event
        log_level = LogLevel.INFO if success else LogLevel.ERROR
        self._log_structured(
            log_level,
            f"OAuth {operation} - {service_name}",
            {
                "event_type": "authentication",
                "service_name": service_name,
                "operation": operation,
                "success": success,
                "user_id": user_id,
                "error_message": error_message,
                "error_code": error_code,
            },
        )

    def log_performance_metrics(
        self, service_name: str, operation_type: str, response_time_ms: float, **kwargs
    ) -> None:
        """Log performance metrics."""
        if not self.enable_metrics:
            return

        metrics = PerformanceMetrics(
            service_name=service_name,
            operation_type=operation_type,
            timestamp=datetime.now(),
            response_time_ms=response_time_ms,
            **kwargs,
        )

        # Store in memory for analytics
        self.performance_metrics.append(metrics)

        # Log the metrics
        self._log_structured(
            LogLevel.DEBUG,
            f"Performance metrics - {service_name} - {operation_type}",
            {
                "event_type": "performance",
                "service_name": service_name,
                "operation_type": operation_type,
                "response_time_ms": response_time_ms,
                **kwargs,
            },
        )

    def log_error(
        self,
        error: Exception,
        service_name: Optional[str] = None,
        operation: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log errors with structured context."""
        error_type = type(error).__name__
        error_message = str(error)

        # Determine log level based on error type
        if isinstance(error, (MCPConnectionError, MCPTimeoutError)):
            log_level = LogLevel.ERROR
        elif isinstance(error, MCPAuthenticationError):
            log_level = LogLevel.CRITICAL
        elif isinstance(error, MCPRateLimitError):
            log_level = LogLevel.WARNING
        else:
            log_level = LogLevel.ERROR

        log_data = {
            "event_type": "error",
            "error_type": error_type,
            "error_message": error_message,
            "service_name": service_name,
            "operation": operation,
        }

        if context_data:
            log_data.update(context_data)

        # Add error-specific details
        if isinstance(error, MCPAuthenticationError):
            log_data["auth_error"] = True
            if hasattr(error, "service_name"):
                log_data["service_name"] = error.service_name

        if isinstance(error, MCPRateLimitError):
            log_data["rate_limit_error"] = True
            retry_after = getattr(error, "retry_after", None)
            if retry_after is not None:
                log_data["retry_after"] = retry_after

        self._log_structured(log_level, f"MCP Error: {error_message}", log_data)

    def _log_structured(
        self, level: LogLevel, message: str, extra_fields: Dict[str, Any]
    ) -> None:
        """Internal method to log with structured data."""
        # Add current context if available
        context = self.get_current_context()
        if context:
            extra_fields["context"] = context.to_dict()

        # Create log record
        log_method = getattr(self.logger, level.value.lower())

        # Create a custom log record with extra fields
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=getattr(logging, level.value),
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=None,
        )
        record.extra_fields = extra_fields

        # Log the record
        self.logger.handle(record)

    def get_usage_statistics(
        self,
        service_name: Optional[str] = None,
        time_window_hours: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get usage statistics for analysis."""
        if time_window_hours:
            cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
            filtered_logs = [
                log for log in self.usage_logs if log.timestamp >= cutoff_time
            ]
        else:
            filtered_logs = list(self.usage_logs)

        if service_name:
            filtered_logs = [
                log for log in filtered_logs if log.service_name == service_name
            ]

        # Calculate statistics
        total_operations = len(filtered_logs)
        successful_operations = sum(1 for log in filtered_logs if log.success)
        failed_operations = total_operations - successful_operations

        if total_operations > 0:
            avg_execution_time = (
                sum(log.execution_time_ms for log in filtered_logs) / total_operations
            )
            success_rate = (successful_operations / total_operations) * 100
        else:
            avg_execution_time = 0
            success_rate = 0

        # Group by service and agent
        by_service = defaultdict(lambda: {"operations": 0, "success": 0, "avg_time": 0})
        for log in filtered_logs:
            key = f"{log.service_name}:{log.agent_type}"
            by_service[key]["operations"] += 1
            if log.success:
                by_service[key]["success"] += 1
            by_service[key]["avg_time"] += log.execution_time_ms

        # Calculate averages
        for stats in by_service.values():
            if stats["operations"] > 0:
                stats["avg_time"] /= stats["operations"]
                stats["success_rate"] = (stats["success"] / stats["operations"]) * 100

        return {
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "failed_operations": failed_operations,
            "success_rate": round(success_rate, 2),
            "avg_execution_time_ms": round(avg_execution_time, 2),
            "by_service_and_agent": dict(by_service),
            "time_window_hours": time_window_hours,
        }

    def get_connection_statistics(
        self, service_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get connection statistics for analysis."""
        if service_name:
            return {service_name: self.connection_stats[service_name]}
        else:
            return dict(self.connection_stats)

    def get_authentication_statistics(
        self, time_window_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get authentication statistics for analysis."""
        if time_window_hours:
            cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
            filtered_logs = [
                log for log in self.auth_logs if log.timestamp >= cutoff_time
            ]
        else:
            filtered_logs = list(self.auth_logs)

        # Group by service
        by_service = defaultdict(
            lambda: {
                "total_attempts": 0,
                "successful_attempts": 0,
                "failed_attempts": 0,
                "error_types": defaultdict(int),
            }
        )

        for log in filtered_logs:
            stats = by_service[log.service_name]
            stats["total_attempts"] += 1

            if log.success:
                stats["successful_attempts"] += 1
            else:
                stats["failed_attempts"] += 1
                if log.error_code:
                    stats["error_types"][log.error_code] += 1

        # Calculate success rates
        for stats in by_service.values():
            if stats["total_attempts"] > 0:
                stats["success_rate"] = (
                    stats["successful_attempts"] / stats["total_attempts"]
                ) * 100

        return {"by_service": dict(by_service), "time_window_hours": time_window_hours}

    def start_cleanup_task(self) -> None:
        """Start the background cleanup task for old metrics."""

        async def cleanup_old_metrics():
            while True:
                try:
                    cutoff_time = datetime.now() - timedelta(
                        hours=self.metrics_retention_hours
                    )

                    # Clean up old logs
                    self.connection_logs = deque(
                        (
                            log
                            for log in self.connection_logs
                            if log.timestamp >= cutoff_time
                        ),
                        maxlen=self.connection_logs.maxlen,
                    )

                    self.usage_logs = deque(
                        (
                            log
                            for log in self.usage_logs
                            if log.timestamp >= cutoff_time
                        ),
                        maxlen=self.usage_logs.maxlen,
                    )

                    self.auth_logs = deque(
                        (log for log in self.auth_logs if log.timestamp >= cutoff_time),
                        maxlen=self.auth_logs.maxlen,
                    )

                    self.performance_metrics = deque(
                        (
                            log
                            for log in self.performance_metrics
                            if log.timestamp >= cutoff_time
                        ),
                        maxlen=self.performance_metrics.maxlen,
                    )

                    # Sleep for 1 hour before next cleanup
                    await asyncio.sleep(3600)

                except Exception as e:
                    self.log_error(e, operation="cleanup_task")
                    await asyncio.sleep(3600)

        # Start the cleanup task
        try:
            loop = asyncio.get_event_loop()
            self._cleanup_task = loop.create_task(cleanup_old_metrics())
        except RuntimeError:
            # No event loop running, cleanup will be manual
            pass

    def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()


# Global structured logger instance
mcp_logger = MCPStructuredLogger()


def get_mcp_logger() -> MCPStructuredLogger:
    """Get the global MCP structured logger instance."""
    return mcp_logger


# Convenience functions for common logging operations
def log_mcp_connection(
    service_name: str, success: bool, response_time_ms: float, **kwargs
) -> None:
    """Log MCP connection event."""
    mcp_logger.log_connection(
        service_name=service_name,
        operation="connect",
        success=success,
        response_time_ms=response_time_ms,
        **kwargs,
    )


def log_mcp_usage(
    service_name: str,
    agent_type: str,
    operation: str,
    success: bool,
    execution_time_ms: float,
    **kwargs,
) -> None:
    """Log MCP usage event."""
    mcp_logger.log_usage(
        service_name=service_name,
        agent_type=agent_type,
        operation=operation,
        tool_name=kwargs.get("tool_name"),
        success=success,
        execution_time_ms=execution_time_ms,
        **kwargs,
    )


def log_oauth_authentication(
    service_name: str, operation: str, success: bool, user_id: str, **kwargs
) -> None:
    """Log OAuth authentication event."""
    mcp_logger.log_authentication(
        service_name=service_name,
        operation=operation,
        success=success,
        user_id=user_id,
        **kwargs,
    )
