"""
Base MCP Server Implementation

This module provides a base class for all MCP server implementations,
centralizing common functionality like connection management, error handling,
logging, health monitoring, and retry logic.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum

from app.core.config import get_settings, get_mcp_config

logger = logging.getLogger(__name__)


class MCPServerState(Enum):
    """MCP Server connection states"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    CIRCUIT_OPEN = "circuit_open"


class MCPOperationResult:
    """Result wrapper for MCP operations"""

    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        retry_count: int = 0,
        duration_ms: float = 0.0,
        service_name: str = "",
    ):
        self.success = success
        self.data = data
        self.error = error
        self.retry_count = retry_count
        self.duration_ms = duration_ms
        self.service_name = service_name
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "retry_count": self.retry_count,
            "duration_ms": self.duration_ms,
            "service_name": self.service_name,
            "timestamp": self.timestamp.isoformat(),
        }


class CircuitBreaker:
    """Circuit breaker implementation for MCP operations"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = MCPServerState.DISCONNECTED

    def can_execute(self) -> bool:
        """Check if operation can be executed"""
        if self.state != MCPServerState.CIRCUIT_OPEN:
            return True

        # Check if we should attempt recovery
        if (
            self.last_failure_time
            and datetime.now() - self.last_failure_time
            > timedelta(seconds=self.recovery_timeout)
        ):
            logger.info("🔄 Circuit breaker attempting recovery...")
            self.state = MCPServerState.CONNECTING  # Half-open state
            return True

        return False

    def record_success(self) -> None:
        """Record successful operation"""
        self.failure_count = 0
        self.state = MCPServerState.CONNECTED
        logger.debug(
            "✅ Circuit breaker: Operation successful, resetting failure count"
        )

    def record_failure(self) -> None:
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = MCPServerState.CIRCUIT_OPEN
            logger.warning(
                f"⚡ Circuit breaker opened after {self.failure_count} failures. "
                f"Will retry in {self.recovery_timeout} seconds"
            )
        else:
            logger.debug(
                f"❌ Circuit breaker: Failure {self.failure_count}/{self.failure_threshold}"
            )


class BaseMCPServer(ABC):
    """
    Base class for all MCP server implementations.

    Provides common functionality including:
    - Connection management
    - Error handling and retries
    - Circuit breaker pattern
    - Health monitoring
    - Logging and metrics
    - Configuration management
    """

    def __init__(
        self,
        service_name: str,
        external_user_id: str,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.service_name = service_name
        self.external_user_id = external_user_id

        # Load configurations
        self.settings = get_settings()
        self.mcp_config = get_mcp_config()
        self.config = config or self.mcp_config.get_service_config(service_name)

        # Initialize state
        self.state = MCPServerState.DISCONNECTED
        self.connection = None
        self.last_health_check: Optional[datetime] = None
        self.health_check_failures = 0

        # Initialize circuit breaker
        circuit_config = self.mcp_config.get_circuit_breaker_config()
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_config["failure_threshold"],
            recovery_timeout=circuit_config["recovery_timeout"],
        )

        # Initialize logging
        self.logger = logging.getLogger(f"mcp.{service_name}")
        if self.mcp_config.is_logging_enabled("DEBUG"):
            self.logger.setLevel(logging.DEBUG)

        self.logger.info(f"🏗️ Initializing MCP server for {service_name}")

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the MCP server.
        Must be implemented by subclasses.

        Returns:
            bool: True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Disconnect from the MCP server.
        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    async def execute_operation(self, operation: str, **kwargs) -> MCPOperationResult:
        """
        Execute a specific MCP operation.
        Must be implemented by subclasses.

        Args:
            operation: Name of the operation to execute
            **kwargs: Operation-specific parameters

        Returns:
            MCPOperationResult: Result of the operation
        """
        pass

    async def safe_execute(self, operation: str, **kwargs) -> MCPOperationResult:
        """
        Execute operation with error handling, retries, and circuit breaker.

        Args:
            operation: Name of the operation to execute
            **kwargs: Operation-specific parameters

        Returns:
            MCPOperationResult: Result of the operation
        """
        start_time = time.time()
        retry_count = 0
        last_error = None

        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            self.logger.warning(f"⚡ Circuit breaker open for {self.service_name}")
            return MCPOperationResult(
                success=False,
                error="Circuit breaker open - service temporarily unavailable",
                service_name=self.service_name,
                duration_ms=(time.time() - start_time) * 1000,
            )

        max_retries = self.config.get("max_retries", 3)

        for attempt in range(max_retries + 1):
            try:
                self.logger.debug(
                    f"🔄 Executing {operation} on {self.service_name} "
                    f"(attempt {attempt + 1}/{max_retries + 1})"
                )

                # Ensure connection
                if self.state != MCPServerState.CONNECTED:
                    await self.ensure_connected()

                # Execute the operation
                result = await self.execute_operation(operation, **kwargs)

                if result.success:
                    self.circuit_breaker.record_success()
                    result.retry_count = retry_count
                    result.duration_ms = (time.time() - start_time) * 1000

                    self.logger.info(
                        f"✅ {operation} completed successfully on {self.service_name} "
                        f"({result.duration_ms:.1f}ms, {retry_count} retries)"
                    )
                    return result
                else:
                    last_error = result.error
                    self.logger.warning(
                        f"❌ {operation} failed on {self.service_name}: {result.error}"
                    )

            except Exception as e:
                last_error = str(e)
                self.logger.error(
                    f"❌ Exception during {operation} on {self.service_name}: {e}",
                    exc_info=True,
                )
                self.state = MCPServerState.ERROR

            # Increment retry count and apply backoff
            retry_count += 1
            if attempt < max_retries:
                delay = self._calculate_backoff_delay(attempt)
                self.logger.debug(f"⏱️ Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)

        # All retries exhausted
        self.circuit_breaker.record_failure()
        duration_ms = (time.time() - start_time) * 1000

        self.logger.error(
            f"💥 All retries exhausted for {operation} on {self.service_name} "
            f"after {retry_count} attempts ({duration_ms:.1f}ms)"
        )

        return MCPOperationResult(
            success=False,
            error=last_error or "Unknown error",
            retry_count=retry_count,
            duration_ms=duration_ms,
            service_name=self.service_name,
        )

    async def ensure_connected(self) -> bool:
        """
        Ensure the server is connected, attempting connection if needed.

        Returns:
            bool: True if connected, False otherwise
        """
        if self.state == MCPServerState.CONNECTED:
            return True

        if self.state == MCPServerState.CONNECTING:
            # Wait a bit for ongoing connection
            await asyncio.sleep(0.1)
            return self.state == MCPServerState.CONNECTED

        try:
            self.state = MCPServerState.CONNECTING
            self.logger.info(f"🔌 Connecting to {self.service_name}...")

            success = await self.connect()

            if success:
                self.state = MCPServerState.CONNECTED
                self.logger.info(f"✅ Connected to {self.service_name}")
                return True
            else:
                self.state = MCPServerState.ERROR
                self.logger.error(f"❌ Failed to connect to {self.service_name}")
                return False

        except Exception as e:
            self.state = MCPServerState.ERROR
            self.logger.error(f"❌ Connection error for {self.service_name}: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the MCP server.

        Returns:
            Dict containing health status information
        """
        start_time = time.time()

        try:
            # Basic connectivity check
            if self.state != MCPServerState.CONNECTED:
                if not await self.ensure_connected():
                    self.health_check_failures += 1
                    return {
                        "healthy": False,
                        "service": self.service_name,
                        "error": "Connection failed",
                        "failures": self.health_check_failures,
                        "timestamp": datetime.now().isoformat(),
                        "duration_ms": (time.time() - start_time) * 1000,
                    }

            # Service-specific health check (can be overridden)
            health_result = await self.perform_health_check()

            if health_result.get("healthy", True):
                self.health_check_failures = 0
                self.last_health_check = datetime.now()

            duration_ms = (time.time() - start_time) * 1000

            return {
                "healthy": health_result.get("healthy", True),
                "service": self.service_name,
                "state": self.state.value,
                "circuit_breaker": self.circuit_breaker.state.value,
                "failures": self.health_check_failures,
                "last_check": self.last_health_check.isoformat()
                if self.last_health_check
                else None,
                "duration_ms": duration_ms,
                "timestamp": datetime.now().isoformat(),
                **health_result,
            }

        except Exception as e:
            self.health_check_failures += 1
            self.logger.error(f"❌ Health check failed for {self.service_name}: {e}")

            return {
                "healthy": False,
                "service": self.service_name,
                "error": str(e),
                "failures": self.health_check_failures,
                "timestamp": datetime.now().isoformat(),
                "duration_ms": (time.time() - start_time) * 1000,
            }

    async def perform_health_check(self) -> Dict[str, Any]:
        """
        Perform service-specific health check.
        Can be overridden by subclasses for custom health checks.

        Returns:
            Dict containing health check results
        """
        # Default implementation: just check connection state
        return {
            "healthy": self.state == MCPServerState.CONNECTED,
            "connection_state": self.state.value,
        }

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate backoff delay for retry attempts.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            float: Delay in seconds
        """
        backoff_factor = self.config.get("backoff_factor", 2.0)
        max_delay = self.config.get("max_delay", 60)

        # Exponential backoff: 1s, 2s, 4s, 8s, etc.
        delay = min(backoff_factor**attempt, max_delay)

        # Add jitter to prevent thundering herd
        if self.mcp_config.mcp_retry_jitter:
            import random

            jitter = random.uniform(0.1, 0.3) * delay
            delay += jitter

        return delay

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the MCP server.

        Returns:
            Dict containing status information
        """
        return {
            "service_name": self.service_name,
            "state": self.state.value,
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "circuit_breaker_failures": self.circuit_breaker.failure_count,
            "health_check_failures": self.health_check_failures,
            "last_health_check": self.last_health_check.isoformat()
            if self.last_health_check
            else None,
            "external_user_id": self.external_user_id,
            "config": self.config,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics for monitoring and observability.

        Returns:
            Dict containing metrics data
        """
        return {
            "service_name": self.service_name,
            "state": self.state.value,
            "circuit_breaker": {
                "state": self.circuit_breaker.state.value,
                "failure_count": self.circuit_breaker.failure_count,
                "failure_threshold": self.circuit_breaker.failure_threshold,
                "last_failure": (
                    self.circuit_breaker.last_failure_time.isoformat()
                    if self.circuit_breaker.last_failure_time
                    else None
                ),
            },
            "health": {
                "failures": self.health_check_failures,
                "last_check": (
                    self.last_health_check.isoformat()
                    if self.last_health_check
                    else None
                ),
            },
            "timestamp": datetime.now().isoformat(),
        }

    async def cleanup(self) -> None:
        """
        Clean up resources and disconnect.
        """
        try:
            self.logger.info(f"🧹 Cleaning up MCP server for {self.service_name}")
            await self.disconnect()
            self.state = MCPServerState.DISCONNECTED
        except Exception as e:
            self.logger.error(f"❌ Error during cleanup for {self.service_name}: {e}")

    def __repr__(self) -> str:
        return (
            f"BaseMCPServer(service={self.service_name}, "
            f"state={self.state.value}, user={self.external_user_id})"
        )

    async def __aenter__(self):
        """Async context manager entry"""
        await self.ensure_connected()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()


class MCPServerManager:
    """
    Manager for multiple MCP servers with centralized monitoring.
    """

    def __init__(self):
        self.servers: Dict[str, BaseMCPServer] = {}
        self.logger = logging.getLogger("mcp.manager")

    def register_server(self, server: BaseMCPServer) -> None:
        """Register an MCP server for management"""
        self.servers[server.service_name] = server
        self.logger.info(f"📝 Registered MCP server: {server.service_name}")

    def unregister_server(self, service_name: str) -> None:
        """Unregister an MCP server"""
        if service_name in self.servers:
            del self.servers[service_name]
            self.logger.info(f"🗑️ Unregistered MCP server: {service_name}")

    async def health_check_all(self) -> Dict[str, Any]:
        """
        Perform health check on all registered servers.

        Returns:
            Dict containing health status for all servers
        """
        results = {}

        for service_name, server in self.servers.items():
            try:
                results[service_name] = await server.health_check()
            except Exception as e:
                results[service_name] = {
                    "healthy": False,
                    "service": service_name,
                    "error": f"Health check failed: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }

        # Calculate overall health
        healthy_servers = sum(
            1 for result in results.values() if result.get("healthy", False)
        )
        total_servers = len(results)

        return {
            "overall_healthy": healthy_servers == total_servers and total_servers > 0,
            "healthy_servers": healthy_servers,
            "total_servers": total_servers,
            "servers": results,
            "timestamp": datetime.now().isoformat(),
        }

    async def cleanup_all(self) -> None:
        """Clean up all registered servers"""
        for service_name, server in self.servers.items():
            try:
                await server.cleanup()
            except Exception as e:
                self.logger.error(f"❌ Error cleaning up {service_name}: {e}")

    def get_server(self, service_name: str) -> Optional[BaseMCPServer]:
        """Get a specific server by name"""
        return self.servers.get(service_name)

    def list_servers(self) -> List[str]:
        """Get list of registered server names"""
        return list(self.servers.keys())


# Global server manager instance
_server_manager: Optional[MCPServerManager] = None


def get_server_manager() -> MCPServerManager:
    """Get the global server manager instance"""
    global _server_manager
    if _server_manager is None:
        _server_manager = MCPServerManager()
    return _server_manager
