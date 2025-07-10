"""
MCP Integration module for PipeWise.

This module integrates the MCP monitoring systems with the existing PipeWise
infrastructure including:
- FastAPI application integration
- Middleware for automatic metrics collection
- Logging system integration
- Background task management
- Service initialization and configuration
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
import time
from datetime import datetime

from app.ai_agents.mcp.health_monitor import get_health_monitor
from app.ai_agents.mcp.alert_manager import get_alert_manager
from app.ai_agents.mcp.performance_metrics import get_performance_monitor
from app.ai_agents.mcp.structured_logger import get_mcp_logger, OperationType
from app.api.mcp_health import router as health_router


class MCPMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect performance metrics for all API requests.

    This middleware integrates with the MCP performance monitoring system to
    track API response times, success rates, and other metrics.
    """

    def __init__(self, app, enable_detailed_logging: bool = True):
        """
        Initialize the metrics middleware.

        Args:
            app: FastAPI application instance
            enable_detailed_logging: Whether to log detailed request information
        """
        super().__init__(app)
        self.performance_monitor = get_performance_monitor()
        self.mcp_logger = get_mcp_logger()
        self.enable_detailed_logging = enable_detailed_logging

        # Setup middleware logger
        self.logger = logging.getLogger(__name__)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and collect metrics."""
        start_time = time.time()

        # Generate operation ID for tracking
        operation_id = f"api_{int(start_time * 1000)}_{id(request)}"

        # Extract request information
        method = request.method
        path = str(request.url.path)
        user_agent = request.headers.get("user-agent", "unknown")
        client_ip = (
            getattr(request.client, "host", "unknown") if request.client else "unknown"
        )

        # Start tracking the operation
        correlation_id = self.performance_monitor.start_operation(
            operation_id=operation_id,
            service_name="pipewise_api",
            operation=f"{method} {path}",
            agent_type="api_gateway",
            user_id=self._extract_user_id(request),
            session_id=self._extract_session_id(request),
        )

        # Log request start if detailed logging is enabled
        if self.enable_detailed_logging:
            with self.mcp_logger.operation_context(
                OperationType.AGENT_WORKFLOW, service_name="pipewise_api"
            ):
                self.mcp_logger.log_usage(
                    service_name="pipewise_api",
                    agent_type="api_gateway",
                    operation="request_start",
                    tool_name=f"{method} {path}",
                    success=True,
                    execution_time_ms=0,
                    user_id=self._extract_user_id(request),
                    user_agent=user_agent,
                    client_ip=client_ip,
                    correlation_id=correlation_id,
                )

        try:
            # Process the request
            response = await call_next(request)

            # Calculate response time
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000

            # Determine if request was successful
            success = 200 <= response.status_code < 400
            error_type = None
            error_message = None

            if not success:
                error_type = f"http_{response.status_code}"
                error_message = f"HTTP {response.status_code}"

            # End operation tracking
            self.performance_monitor.end_operation(
                operation_id=operation_id,
                success=success,
                error_type=error_type,
                error_message=error_message,
                response_size_bytes=self._get_response_size(response),
            )

            # Log detailed request information
            if self.enable_detailed_logging:
                with self.mcp_logger.operation_context(
                    OperationType.AGENT_WORKFLOW, service_name="pipewise_api"
                ):
                    self.mcp_logger.log_usage(
                        service_name="pipewise_api",
                        agent_type="api_gateway",
                        operation="request_complete",
                        tool_name=f"{method} {path}",
                        success=success,
                        execution_time_ms=response_time_ms,
                        user_id=self._extract_user_id(request),
                        status_code=response.status_code,
                        user_agent=user_agent,
                        client_ip=client_ip,
                        correlation_id=correlation_id,
                    )

            # Add performance headers to response
            response.headers["X-Response-Time"] = f"{response_time_ms:.2f}ms"
            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception as e:
            # Calculate response time for failed requests
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000

            # End operation tracking with error
            self.performance_monitor.end_operation(
                operation_id=operation_id,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e),
            )

            # Log the error
            self.mcp_logger.log_error(
                error=e,
                service_name="pipewise_api",
                operation=f"{method} {path}",
                context_data={
                    "correlation_id": correlation_id,
                    "user_id": self._extract_user_id(request),
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "response_time_ms": response_time_ms,
                },
            )

            # Re-raise the exception
            raise

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request if available."""
        # Try to get user ID from headers, JWT token, or session
        user_id = request.headers.get("x-user-id")
        if user_id:
            return user_id

        # Could also extract from JWT token or session here
        # For now, return None if not found
        return None

    def _extract_session_id(self, request: Request) -> Optional[str]:
        """Extract session ID from request if available."""
        # Try to get session ID from cookies or headers
        session_id = request.headers.get("x-session-id")
        if session_id:
            return session_id

        # Could also extract from cookies here
        return None

    def _get_response_size(self, response: Response) -> Optional[int]:
        """Get response size in bytes if available."""
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                return int(content_length)
            except ValueError:
                pass
        return None


class MCPSystemManager:
    """
    Manager for all MCP monitoring systems.

    This class provides centralized management of health monitoring,
    alerting, performance tracking, and logging systems.
    """

    def __init__(self):
        """Initialize the MCP system manager."""
        self.health_monitor = get_health_monitor()
        self.alert_manager = get_alert_manager()
        self.performance_monitor = get_performance_monitor()
        self.mcp_logger = get_mcp_logger()

        self.logger = logging.getLogger(__name__)
        self.is_initialized = False
        self.background_tasks: list = []

    async def initialize(self, app: FastAPI) -> None:
        """
        Initialize all MCP systems and integrate with FastAPI app.

        Args:
            app: FastAPI application instance
        """
        if self.is_initialized:
            self.logger.warning("MCP systems already initialized")
            return

        try:
            # Configure MCP services
            await self._configure_mcp_services()

            # Start monitoring systems
            await self._start_monitoring_systems()

            # Register health endpoints
            self._register_health_endpoints(app)

            # Add middleware
            self._add_middleware(app)

            # Setup logging integration
            self._setup_logging_integration()

            self.is_initialized = True
            self.logger.info("MCP systems initialized successfully")

            # Log system startup
            with self.mcp_logger.operation_context(
                OperationType.CONFIGURATION, service_name="pipewise_mcp"
            ):
                self.mcp_logger.log_usage(
                    service_name="pipewise_mcp",
                    agent_type="system",
                    operation="system_startup",
                    tool_name="initialization",
                    success=True,
                    execution_time_ms=0,
                )

        except Exception as e:
            self.logger.error(f"Failed to initialize MCP systems: {str(e)}")

            # Log initialization failure
            self.mcp_logger.log_error(
                error=e,
                service_name="pipewise_mcp",
                operation="system_startup",
                context_data={"initialization_failed": True},
            )
            raise

    async def _configure_mcp_services(self) -> None:
        """Configure all MCP services with their connection details."""
        from app.ai_agents.mcp.config import get_enabled_services, validate_mcp_config

        # Get enabled services from configuration
        enabled_services = get_enabled_services()

        # Validate configurations
        validation_errors = validate_mcp_config()
        if validation_errors:
            self.logger.warning(f"Configuration validation errors: {validation_errors}")

        # Register services with health monitor
        for service_name, service_config in enabled_services.items():
            if service_config.enabled and service_config.health_check_enabled:
                self.health_monitor.register_service(
                    service_name, service_config.config
                )

        configured_count = len([s for s in enabled_services.values() if s.enabled])
        self.logger.info(
            f"Configured {configured_count} MCP services from environment variables"
        )

    async def _start_monitoring_systems(self) -> None:
        """Start all monitoring background tasks."""
        # Start health monitoring
        await self.health_monitor.start_monitoring()

        # Start alert monitoring
        await self.alert_manager.start_monitoring()

        # Start performance monitoring
        await self.performance_monitor.start_monitoring()

        self.logger.info("All monitoring systems started")

    def _register_health_endpoints(self, app: FastAPI) -> None:
        """Register health check endpoints with the FastAPI app."""
        app.include_router(health_router)
        self.logger.info("Health check endpoints registered")

    def _add_middleware(self, app: FastAPI) -> None:
        """Add MCP middleware to the FastAPI app."""
        app.add_middleware(MCPMetricsMiddleware, enable_detailed_logging=True)
        self.logger.info("MCP metrics middleware added")

    def _setup_logging_integration(self) -> None:
        """Setup integration with existing PipeWise logging system."""
        # Get the root logger
        root_logger = logging.getLogger()

        # Create a custom handler that forwards to MCP structured logger
        class MCPLogHandler(logging.Handler):
            def __init__(self, mcp_logger):
                super().__init__()
                self.mcp_logger = mcp_logger

            def emit(self, record):
                # Forward log records to MCP structured logger
                if record.levelno >= logging.ERROR:
                    # Create exception from log record
                    exc_info = record.exc_info
                    if exc_info:
                        error = exc_info[1]
                    else:
                        error = Exception(record.getMessage())

                    self.mcp_logger.log_error(
                        error=error,
                        service_name="pipewise",
                        operation=getattr(record, "operation", "unknown"),
                        context_data={
                            "logger_name": record.name,
                            "log_level": record.levelname,
                            "module": record.module,
                            "function": record.funcName,
                            "line": record.lineno,
                        },
                    )

        # Add the handler to forward high-level logs to MCP
        mcp_handler = MCPLogHandler(self.mcp_logger)
        mcp_handler.setLevel(logging.ERROR)  # Only forward errors and above
        root_logger.addHandler(mcp_handler)

        self.logger.info("Logging integration setup complete")

    async def shutdown(self) -> None:
        """Shutdown all MCP systems gracefully."""
        if not self.is_initialized:
            return

        try:
            # Stop monitoring systems
            await self.health_monitor.stop_monitoring()
            await self.alert_manager.stop_monitoring()
            await self.performance_monitor.stop_monitoring()

            # Stop cleanup tasks
            self.mcp_logger.stop_cleanup_task()

            self.logger.info("MCP systems shutdown complete")

            # Log system shutdown
            with self.mcp_logger.operation_context(
                OperationType.CONFIGURATION, service_name="pipewise_mcp"
            ):
                self.mcp_logger.log_usage(
                    service_name="pipewise_mcp",
                    agent_type="system",
                    operation="system_shutdown",
                    tool_name="cleanup",
                    success=True,
                    execution_time_ms=0,
                )

        except Exception as e:
            self.logger.error(f"Error during MCP systems shutdown: {str(e)}")
            self.mcp_logger.log_error(
                error=e,
                service_name="pipewise_mcp",
                operation="system_shutdown",
                context_data={"shutdown_error": True},
            )

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        return {
            "initialized": self.is_initialized,
            "health_monitor_running": self.health_monitor.is_running,
            "alert_manager_running": self.alert_manager.is_running,
            "performance_monitor_running": self.performance_monitor.is_running,
            "services_registered": len(self.health_monitor.service_configs),
            "active_alerts": len(self.alert_manager.get_active_alerts()),
            "timestamp": datetime.now().isoformat(),
        }


# Global MCP system manager instance
mcp_manager = MCPSystemManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for MCP systems.

    This manages the startup and shutdown of all MCP monitoring systems
    as part of the FastAPI application lifecycle.
    """
    # Startup
    try:
        await mcp_manager.initialize(app)
        yield
    finally:
        # Shutdown
        await mcp_manager.shutdown()


def get_mcp_manager() -> MCPSystemManager:
    """Get the global MCP system manager instance."""
    return mcp_manager


def setup_mcp_integration(app: FastAPI) -> None:
    """
    Setup MCP integration with a FastAPI application.

    This is a convenience function that can be called from main.py
    to quickly integrate MCP monitoring with an existing FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # Add the lifespan manager
    app.router.lifespan_context = lifespan

    # The actual initialization will happen during app startup
    logging.getLogger(__name__).info("MCP integration setup complete")


async def manual_initialize_mcp() -> None:
    """
    Manually initialize MCP systems.

    Use this if you're not using the FastAPI lifespan integration.
    """
    from fastapi import FastAPI

    # Create a dummy app for initialization
    app = FastAPI()
    await mcp_manager.initialize(app)


# Convenience functions for common operations
def log_mcp_operation(
    service_name: str, operation: str, success: bool, execution_time_ms: float, **kwargs
) -> None:
    """Log an MCP operation with automatic context."""
    mcp_logger = get_mcp_logger()

    with mcp_logger.operation_context(
        OperationType.TOOL_EXECUTION, service_name=service_name
    ):
        mcp_logger.log_usage(
            service_name=service_name,
            agent_type=kwargs.get("agent_type", "unknown"),
            operation=operation,
            tool_name=kwargs.get("tool_name"),
            success=success,
            execution_time_ms=execution_time_ms,
            **kwargs,
        )


def check_mcp_service_health(service_name: str) -> Dict[str, Any]:
    """Check health of a specific MCP service."""
    health_monitor = get_health_monitor()

    # This would need to be made synchronous or wrapped in asyncio.run()
    # For now, return cached metrics
    metrics = health_monitor.get_service_metrics(service_name)
    return metrics.get(service_name, {})


def get_mcp_performance_summary() -> Dict[str, Any]:
    """Get overall MCP performance summary."""
    performance_monitor = get_performance_monitor()
    return performance_monitor.get_all_services_overview()


def trigger_mcp_alert_check(service_name: str, status: str) -> None:
    """Trigger alert check for a service status change."""
    from app.ai_agents.mcp.health_monitor import ServiceStatus

    alert_manager = get_alert_manager()

    # Convert string status to enum
    try:
        service_status = ServiceStatus(status.lower())
    except ValueError:
        service_status = ServiceStatus.UNKNOWN

    # Trigger alert check asynchronously
    asyncio.create_task(
        alert_manager.check_service_unavailability(service_name, service_status)
    )
