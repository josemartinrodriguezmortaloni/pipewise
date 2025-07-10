"""
MCP Health Check API endpoint.

This module provides REST API endpoints for monitoring MCP services health including:
- /health/mcp - Overall MCP system health status
- /health/mcp/{service_name} - Specific service health details
- /health/mcp/metrics - Performance metrics summary
- /health/mcp/alerts - Active alerts and alert history
- /health/mcp/dashboard - Complete health dashboard data
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from enum import Enum

from app.ai_agents.mcp.health_monitor import (
    get_health_monitor,
    ServiceStatus,
    AlertSeverity,
)
from app.ai_agents.mcp.alert_manager import get_alert_manager
from app.ai_agents.mcp.performance_metrics import get_performance_monitor, TimeWindow
from app.ai_agents.mcp.structured_logger import get_mcp_logger


class HealthStatusResponse(BaseModel):
    """Response model for health status."""

    status: str = Field(description="Overall health status")
    timestamp: str = Field(description="Timestamp of health check")
    uptime_seconds: float = Field(description="System uptime in seconds")
    services: Dict[str, Any] = Field(
        default_factory=dict, description="Individual service statuses"
    )
    summary: Dict[str, Any] = Field(
        default_factory=dict, description="Health summary statistics"
    )


class ServiceHealthResponse(BaseModel):
    """Response model for individual service health."""

    service_name: str = Field(description="Name of the service")
    status: str = Field(description="Service health status")
    last_check: Optional[str] = Field(None, description="Last health check timestamp")
    response_time_ms: Optional[float] = Field(
        None, description="Last response time in milliseconds"
    )
    uptime_percentage: float = Field(description="Service uptime percentage")
    error_count: int = Field(default=0, description="Recent error count")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional service details"
    )


class MetricsResponse(BaseModel):
    """Response model for performance metrics."""

    timestamp: str = Field(description="Metrics timestamp")
    time_window: str = Field(description="Time window for metrics")
    services: Dict[str, Any] = Field(
        default_factory=dict, description="Service-specific metrics"
    )
    overall: Dict[str, Any] = Field(
        default_factory=dict, description="Overall system metrics"
    )


class AlertsResponse(BaseModel):
    """Response model for alerts."""

    active_alerts: List[Dict[str, Any]] = Field(
        default_factory=list, description="Currently active alerts"
    )
    alert_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="Recent alert history"
    )
    alert_statistics: Dict[str, Any] = Field(
        default_factory=dict, description="Alert statistics"
    )


class DashboardResponse(BaseModel):
    """Response model for complete health dashboard."""

    health: HealthStatusResponse
    metrics: MetricsResponse
    alerts: AlertsResponse
    trends: Dict[str, Any] = Field(
        default_factory=dict, description="Performance trends"
    )


# Create router
router = APIRouter(prefix="/health", tags=["MCP Health"])


@router.get("/mcp", response_model=HealthStatusResponse)
async def get_mcp_health_status():
    """
    Get overall MCP system health status.

    Returns comprehensive health information for all registered MCP services
    including status, uptime, error rates, and summary statistics.
    """
    try:
        health_monitor = get_health_monitor()
        alert_manager = get_alert_manager()
        performance_monitor = get_performance_monitor()

        # Get overall system health
        system_health = health_monitor.get_system_health_summary()

        # Get individual service health
        services_health = {}

        # Perform health checks for all services
        health_results = await health_monitor.check_all_services()

        for service_name, result in health_results.items():
            # Get service metrics
            service_metrics = health_monitor.get_service_metrics(service_name)

            # Get performance data
            perf_metrics = performance_monitor.get_real_time_metrics(service_name)

            services_health[service_name] = {
                "status": result.status.value,
                "last_check": result.timestamp.isoformat(),
                "response_time_ms": result.response_time_ms,
                "uptime_percentage": service_metrics.get(service_name, {}).get(
                    "uptime_percentage", 0
                ),
                "total_checks": service_metrics.get(service_name, {}).get(
                    "total_checks", 0
                ),
                "successful_checks": service_metrics.get(service_name, {}).get(
                    "successful_checks", 0
                ),
                "failed_checks": service_metrics.get(service_name, {}).get(
                    "failed_checks", 0
                ),
                "consecutive_failures": service_metrics.get(service_name, {}).get(
                    "consecutive_failures", 0
                ),
                "avg_response_time": service_metrics.get(service_name, {}).get(
                    "avg_response_time", 0
                ),
                "error_message": result.error_message,
                "performance": {
                    "total_requests": perf_metrics.get("total_requests", 0),
                    "success_rate": perf_metrics.get("success_rate", 0),
                    "avg_response_time": perf_metrics.get("avg_response_time", 0),
                    "p95_response_time": perf_metrics.get("p95_response_time", 0),
                },
            }

        # Calculate overall status
        overall_status = "healthy"
        if system_health["unhealthy_services"] > 0:
            overall_status = "unhealthy"
        elif system_health["degraded_services"] > 0:
            overall_status = "degraded"

        # Get active alerts count
        active_alerts = alert_manager.get_active_alerts()
        critical_alerts = sum(
            1 for alert in active_alerts if alert.get("severity") == "critical"
        )

        # Build response
        response = HealthStatusResponse(
            status=overall_status,
            timestamp=datetime.now().isoformat(),
            uptime_seconds=0,  # Would need to track system start time
            services=services_health,
            summary={
                "total_services": system_health["total_services"],
                "healthy_services": system_health["healthy_services"],
                "degraded_services": system_health["degraded_services"],
                "unhealthy_services": system_health["unhealthy_services"],
                "health_percentage": system_health["health_percentage"],
                "active_alerts": len(active_alerts),
                "critical_alerts": critical_alerts,
                "monitoring_active": system_health["monitoring_active"],
            },
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get health status: {str(e)}"
        )


@router.get("/mcp/{service_name}", response_model=ServiceHealthResponse)
async def get_service_health(service_name: str):
    """
    Get detailed health information for a specific MCP service.

    Args:
        service_name: Name of the service to check

    Returns:
        Detailed health information for the specified service
    """
    try:
        health_monitor = get_health_monitor()
        performance_monitor = get_performance_monitor()

        # Perform health check for the specific service
        health_result = await health_monitor.check_service_health(service_name)

        if (
            health_result.error_message
            and "not configured" in health_result.error_message
        ):
            raise HTTPException(
                status_code=404, detail=f"Service '{service_name}' not found"
            )

        # Get service metrics
        service_metrics = health_monitor.get_service_metrics(service_name)
        metrics_data = service_metrics.get(service_name, {})

        # Get performance metrics
        perf_metrics = performance_monitor.get_real_time_metrics(service_name)
        perf_summary = performance_monitor.get_service_performance_summary(service_name)

        # Get recent performance data
        recent_metrics = performance_monitor.get_service_metrics(
            service_name, TimeWindow.HOUR, limit=24
        )

        response = ServiceHealthResponse(
            service_name=service_name,
            status=health_result.status.value,
            last_check=health_result.timestamp.isoformat(),
            response_time_ms=health_result.response_time_ms,
            uptime_percentage=metrics_data.get("uptime_percentage", 0),
            error_count=metrics_data.get("failed_checks", 0),
            details={
                "health_metrics": {
                    "total_checks": metrics_data.get("total_checks", 0),
                    "successful_checks": metrics_data.get("successful_checks", 0),
                    "failed_checks": metrics_data.get("failed_checks", 0),
                    "consecutive_failures": metrics_data.get("consecutive_failures", 0),
                    "avg_response_time": metrics_data.get("avg_response_time", 0),
                    "min_response_time": metrics_data.get("min_response_time", 0),
                    "max_response_time": metrics_data.get("max_response_time", 0),
                    "p95_response_time": metrics_data.get("p95_response_time", 0),
                    "p99_response_time": metrics_data.get("p99_response_time", 0),
                    "last_successful_check": metrics_data.get("last_successful_check"),
                    "current_status": metrics_data.get("current_status", "unknown"),
                },
                "performance_metrics": perf_metrics,
                "performance_summary": perf_summary,
                "recent_performance": [m.to_dict() for m in recent_metrics]
                if recent_metrics
                else [],
                "error_details": {
                    "last_error": health_result.error_message,
                    "error_type": getattr(health_result, "error_type", None),
                },
            },
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get service health: {str(e)}"
        )


@router.get("/mcp/metrics", response_model=MetricsResponse)
async def get_mcp_metrics(
    time_window: str = Query(
        "5m", description="Time window for metrics (1m, 5m, 15m, 1h, 1d)"
    ),
    services: Optional[str] = Query(
        None, description="Comma-separated list of services to include"
    ),
):
    """
    Get performance metrics for MCP services.

    Args:
        time_window: Time window for metrics aggregation
        services: Optional comma-separated list of specific services

    Returns:
        Performance metrics for the specified time window and services
    """
    try:
        performance_monitor = get_performance_monitor()

        # Parse time window
        try:
            window = TimeWindow(time_window)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid time window: {time_window}"
            )

        # Parse services filter
        service_filter = None
        if services:
            service_filter = [s.strip() for s in services.split(",")]

        # Get overall metrics
        overall_metrics = performance_monitor.get_all_services_overview()

        # Get service-specific metrics
        services_metrics = {}

        if service_filter:
            target_services = service_filter
        else:
            # Get all services from recent data
            target_services = set(
                dp.service_name for dp in performance_monitor.data_points
            )

        for service_name in target_services:
            # Get aggregated metrics for the time window
            service_metrics_list = performance_monitor.get_service_metrics(
                service_name, window, limit=1
            )

            if service_metrics_list:
                services_metrics[service_name] = service_metrics_list[0].to_dict()
            else:
                # Fallback to real-time metrics
                services_metrics[service_name] = (
                    performance_monitor.get_real_time_metrics(service_name)
                )

        response = MetricsResponse(
            timestamp=datetime.now().isoformat(),
            time_window=time_window,
            services=services_metrics,
            overall=overall_metrics,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/mcp/alerts", response_model=AlertsResponse)
async def get_mcp_alerts(
    limit: int = Query(
        50, description="Maximum number of alerts to return", ge=1, le=1000
    ),
    include_resolved: bool = Query(
        False, description="Include resolved alerts in history"
    ),
):
    """
    Get active alerts and alert history for MCP services.

    Args:
        limit: Maximum number of alerts to return
        include_resolved: Whether to include resolved alerts

    Returns:
        Active alerts and alert history
    """
    try:
        alert_manager = get_alert_manager()

        # Get active alerts
        active_alerts = alert_manager.get_active_alerts()

        # Get alert history from health monitor
        health_monitor = get_health_monitor()
        alert_history = health_monitor.get_alert_history(limit=limit)

        # Filter resolved alerts if requested
        if not include_resolved:
            alert_history = [
                alert for alert in alert_history if not alert.get("resolved", False)
            ]

        # Get alert statistics
        alert_stats = alert_manager.get_alert_statistics()

        response = AlertsResponse(
            active_alerts=active_alerts,
            alert_history=alert_history,
            alert_statistics=alert_stats,
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.get("/mcp/dashboard", response_model=DashboardResponse)
async def get_mcp_dashboard():
    """
    Get complete MCP health dashboard data.

    Returns comprehensive data for a health monitoring dashboard including
    health status, performance metrics, alerts, and trends.
    """
    try:
        # Get all components
        health_status = await get_mcp_health_status()
        metrics = await get_mcp_metrics(time_window="5m")
        alerts = await get_mcp_alerts(limit=20)

        # Calculate trends
        performance_monitor = get_performance_monitor()
        trends = {}

        # Get services from health status
        services = list(health_status.services.keys())

        for service_name in services:
            service_summary = performance_monitor.get_service_performance_summary(
                service_name
            )
            if "trends" in service_summary:
                trends[service_name] = service_summary["trends"]

        response = DashboardResponse(
            health=health_status, metrics=metrics, alerts=alerts, trends=trends
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get dashboard data: {str(e)}"
        )


@router.post("/mcp/{service_name}/check")
async def trigger_service_health_check(service_name: str):
    """
    Trigger an immediate health check for a specific service.

    Args:
        service_name: Name of the service to check

    Returns:
        Health check result
    """
    try:
        health_monitor = get_health_monitor()

        # Perform immediate health check
        result = await health_monitor.check_service_health(service_name)

        if result.error_message and "not configured" in result.error_message:
            raise HTTPException(
                status_code=404, detail=f"Service '{service_name}' not found"
            )

        return {
            "service_name": service_name,
            "status": result.status.value,
            "response_time_ms": result.response_time_ms,
            "timestamp": result.timestamp.isoformat(),
            "error_message": result.error_message,
            "details": result.details,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to check service health: {str(e)}"
        )


@router.post("/mcp/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    acknowledged_by: str = Query(..., description="User acknowledging the alert"),
):
    """
    Acknowledge an active alert.

    Args:
        alert_id: ID of the alert to acknowledge
        acknowledged_by: User or system acknowledging the alert

    Returns:
        Acknowledgment status
    """
    try:
        alert_manager = get_alert_manager()

        success = await alert_manager.acknowledge_alert(alert_id, acknowledged_by)

        if not success:
            raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")

        return {
            "alert_id": alert_id,
            "acknowledged": True,
            "acknowledged_by": acknowledged_by,
            "acknowledged_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to acknowledge alert: {str(e)}"
        )


@router.post("/mcp/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    resolved_by: str = Query(..., description="User resolving the alert"),
    resolution_notes: str = Query("", description="Optional resolution notes"),
):
    """
    Resolve an active alert.

    Args:
        alert_id: ID of the alert to resolve
        resolved_by: User or system resolving the alert
        resolution_notes: Optional notes about the resolution

    Returns:
        Resolution status
    """
    try:
        alert_manager = get_alert_manager()

        success = await alert_manager.resolve_alert(
            alert_id, resolved_by, resolution_notes
        )

        if not success:
            raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")

        return {
            "alert_id": alert_id,
            "resolved": True,
            "resolved_by": resolved_by,
            "resolution_notes": resolution_notes,
            "resolved_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to resolve alert: {str(e)}"
        )


@router.get("/mcp/system/info")
async def get_system_info():
    """
    Get MCP system information and configuration.

    Returns:
        System information including versions, configuration, and capabilities
    """
    try:
        health_monitor = get_health_monitor()
        alert_manager = get_alert_manager()
        performance_monitor = get_performance_monitor()

        # Get system configuration info
        return {
            "system": {
                "name": "PipeWise MCP System",
                "version": "1.0.0",
                "started_at": datetime.now().isoformat(),  # Would be actual start time
                "monitoring_active": health_monitor.is_running,
                "alerting_active": alert_manager.is_running,
                "performance_tracking_active": performance_monitor.is_running,
            },
            "configuration": {
                "health_monitor": {
                    "check_interval": health_monitor.check_interval,
                    "alert_threshold": health_monitor.alert_threshold,
                    "timeout": health_monitor.timeout,
                    "auto_alerts_enabled": health_monitor.enable_auto_alerts,
                },
                "alert_manager": {
                    "auto_alerts_enabled": alert_manager.enable_auto_alerts,
                    "check_interval": alert_manager.alert_check_interval,
                    "max_active_alerts": alert_manager.max_active_alerts,
                },
                "performance_monitor": {
                    "max_data_points": performance_monitor.max_data_points,
                    "aggregation_interval": performance_monitor.aggregation_interval,
                    "real_time_metrics": performance_monitor.enable_real_time_metrics,
                    "retention_days": performance_monitor.retention_days,
                },
            },
            "capabilities": {
                "health_monitoring": True,
                "performance_tracking": True,
                "alerting": True,
                "real_time_metrics": True,
                "trend_analysis": True,
                "multi_service_support": True,
                "api_endpoints": True,
            },
            "services": {
                "registered_services": len(health_monitor.service_configs),
                "monitored_services": list(health_monitor.service_configs.keys()),
                "alert_rules": len(alert_manager.alert_rules),
                "notification_channels": len(alert_manager.notification_channels),
                "performance_thresholds": len(performance_monitor.thresholds),
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get system info: {str(e)}"
        )


# Health check specifically for the health endpoint itself
@router.get("/mcp/ping")
async def ping():
    """
    Simple ping endpoint to verify the health API is responding.

    Returns:
        Simple pong response with timestamp
    """
    return {
        "status": "ok",
        "message": "pong",
        "timestamp": datetime.now().isoformat(),
        "service": "mcp-health-api",
    }
