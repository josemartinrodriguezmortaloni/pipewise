"""
MCP (Model Context Protocol) monitoring and observability package for PipeWise.

This package provides comprehensive monitoring, alerting, and observability
for all MCP services integrated with PipeWise including:

- Health monitoring with automated checks
- Structured logging and metrics collection
- Alert management with notification channels
- Performance monitoring and analytics
- Integration with FastAPI and existing PipeWise infrastructure
"""

from app.ai_agents.mcp.health_monitor import get_health_monitor, MCPHealthMonitor
from app.ai_agents.mcp.alert_manager import get_alert_manager, MCPAlertManager
from app.ai_agents.mcp.performance_metrics import (
    get_performance_monitor,
    MCPPerformanceMonitor,
)
from app.ai_agents.mcp.structured_logger import get_mcp_logger, MCPStructuredLogger

__all__ = [
    # Main system instances
    "get_health_monitor",
    "get_alert_manager",
    "get_performance_monitor",
    "get_mcp_logger",
    # Class types
    "MCPHealthMonitor",
    "MCPAlertManager",
    "MCPPerformanceMonitor",
    "MCPStructuredLogger",
]

__version__ = "1.0.0"
