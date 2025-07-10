"""
Performance metrics system for MCP operations.

This module provides comprehensive performance monitoring for all MCP operations including:
- Response time tracking and analysis
- Success/failure rate monitoring by service
- Retry count tracking and analysis
- Performance trend detection
- Real-time performance dashboards
- Performance threshold alerting
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import statistics
import threading

from app.ai_agents.mcp.structured_logger import get_mcp_logger


class MetricType(Enum):
    """Types of performance metrics."""

    RESPONSE_TIME = "response_time"
    SUCCESS_RATE = "success_rate"
    FAILURE_RATE = "failure_rate"
    RETRY_COUNT = "retry_count"
    THROUGHPUT = "throughput"
    LATENCY_PERCENTILE = "latency_percentile"
    ERROR_RATE = "error_rate"
    AVAILABILITY = "availability"


class TimeWindow(Enum):
    """Time windows for metric aggregation."""

    MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    HOUR = "1h"
    DAY = "1d"
    WEEK = "7d"


@dataclass
class PerformanceDataPoint:
    """Single performance measurement point."""

    timestamp: datetime
    service_name: str
    operation: str
    agent_type: Optional[str]
    user_id: Optional[str]

    # Timing metrics
    response_time_ms: float
    processing_time_ms: Optional[float] = None
    network_time_ms: Optional[float] = None
    queue_time_ms: Optional[float] = None

    # Operation results
    success: bool = True
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    attempt_number: int = 1

    # Resource metrics
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None

    # Request/Response sizes
    request_size_bytes: Optional[int] = None
    response_size_bytes: Optional[int] = None

    # Context
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        return result


@dataclass
class ServiceMetrics:
    """Aggregated metrics for a service."""

    service_name: str
    time_window: TimeWindow
    window_start: datetime
    window_end: datetime

    # Request counts
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Response time metrics (in milliseconds)
    min_response_time: float = float("inf")
    max_response_time: float = 0.0
    avg_response_time: float = 0.0
    median_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0

    # Error metrics
    error_rate: float = 0.0
    timeout_count: int = 0
    connection_error_count: int = 0
    auth_error_count: int = 0
    rate_limit_count: int = 0

    # Retry metrics
    total_retries: int = 0
    avg_retry_count: float = 0.0
    max_retry_count: int = 0

    # Throughput metrics
    requests_per_second: float = 0.0
    requests_per_minute: float = 0.0

    # Availability
    availability_percentage: float = 100.0
    uptime_seconds: float = 0.0
    downtime_seconds: float = 0.0

    # Resource usage
    avg_memory_usage_mb: Optional[float] = None
    peak_memory_usage_mb: Optional[float] = None
    avg_cpu_usage_percent: Optional[float] = None
    peak_cpu_usage_percent: Optional[float] = None

    def calculate_derived_metrics(self, response_times: List[float]) -> None:
        """Calculate derived metrics from raw data."""
        if not response_times:
            return

        # Response time statistics
        self.min_response_time = min(response_times)
        self.max_response_time = max(response_times)
        self.avg_response_time = statistics.mean(response_times)
        self.median_response_time = statistics.median(response_times)

        # Percentiles
        sorted_times = sorted(response_times)
        n = len(sorted_times)
        if n > 0:
            self.p95_response_time = sorted_times[int(n * 0.95)]
            self.p99_response_time = sorted_times[int(n * 0.99)]

        # Error rate
        if self.total_requests > 0:
            self.error_rate = (self.failed_requests / self.total_requests) * 100
            self.availability_percentage = (
                self.successful_requests / self.total_requests
            ) * 100

        # Throughput
        window_duration = (self.window_end - self.window_start).total_seconds()
        if window_duration > 0:
            self.requests_per_second = self.total_requests / window_duration
            self.requests_per_minute = self.requests_per_second * 60

        # Average retry count
        if self.total_requests > 0:
            self.avg_retry_count = self.total_retries / self.total_requests

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result["time_window"] = self.time_window.value
        result["window_start"] = self.window_start.isoformat()
        result["window_end"] = self.window_end.isoformat()

        # Round floating point values
        for key, value in result.items():
            if isinstance(value, float) and not key.endswith("_inf"):
                result[key] = round(value, 2)

        return result


@dataclass
class PerformanceThreshold:
    """Performance threshold definition for alerting."""

    metric_type: MetricType
    service_name: Optional[str]  # None for all services
    threshold_value: float
    comparison_operator: str  # '>', '<', '>=', '<=', '=='
    time_window: TimeWindow
    alert_enabled: bool = True

    def check_threshold(self, value: float) -> bool:
        """Check if a value violates this threshold."""
        if not self.alert_enabled:
            return False

        if self.comparison_operator == ">":
            return value > self.threshold_value
        elif self.comparison_operator == "<":
            return value < self.threshold_value
        elif self.comparison_operator == ">=":
            return value >= self.threshold_value
        elif self.comparison_operator == "<=":
            return value <= self.threshold_value
        elif self.comparison_operator == "==":
            return abs(value - self.threshold_value) < 0.01
        else:
            return False


class MCPPerformanceMonitor:
    """Main performance monitoring system for MCP operations."""

    def __init__(
        self,
        max_data_points: int = 100000,
        aggregation_interval: int = 60,  # seconds
        enable_real_time_metrics: bool = True,
        retention_days: int = 7,
    ):
        """
        Initialize the performance monitor.

        Args:
            max_data_points: Maximum number of data points to keep in memory
            aggregation_interval: How often to aggregate metrics (seconds)
            enable_real_time_metrics: Whether to calculate real-time metrics
            retention_days: How many days to retain detailed metrics
        """
        self.max_data_points = max_data_points
        self.aggregation_interval = aggregation_interval
        self.enable_real_time_metrics = enable_real_time_metrics
        self.retention_days = retention_days

        # Data storage
        self.data_points: deque = deque(maxlen=max_data_points)
        self.aggregated_metrics: Dict[str, Dict[TimeWindow, List[ServiceMetrics]]] = (
            defaultdict(lambda: defaultdict(list))
        )

        # Real-time tracking
        self.active_operations: Dict[str, PerformanceDataPoint] = {}
        self.operation_lock = threading.RLock()

        # Performance thresholds
        self.thresholds: List[PerformanceThreshold] = []

        # Background tasks
        self.aggregation_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        self.is_running = False

        # Metrics cache for fast retrieval
        self._metrics_cache: Dict[str, Any] = {}
        self._cache_last_updated: Optional[datetime] = None
        self._cache_ttl = timedelta(seconds=30)

        # Setup logging
        self.mcp_logger = get_mcp_logger()

        # Register default thresholds
        self.register_default_thresholds()

    def register_default_thresholds(self) -> None:
        """Register default performance thresholds."""
        # High response time threshold
        self.add_threshold(
            PerformanceThreshold(
                metric_type=MetricType.RESPONSE_TIME,
                service_name=None,  # All services
                threshold_value=5000,  # 5 seconds
                comparison_operator=">",
                time_window=TimeWindow.FIVE_MINUTES,
            )
        )

        # Low success rate threshold
        self.add_threshold(
            PerformanceThreshold(
                metric_type=MetricType.SUCCESS_RATE,
                service_name=None,
                threshold_value=95.0,  # 95%
                comparison_operator="<",
                time_window=TimeWindow.FIFTEEN_MINUTES,
            )
        )

        # High error rate threshold
        self.add_threshold(
            PerformanceThreshold(
                metric_type=MetricType.ERROR_RATE,
                service_name=None,
                threshold_value=10.0,  # 10%
                comparison_operator=">",
                time_window=TimeWindow.FIVE_MINUTES,
            )
        )

        # High retry count threshold
        self.add_threshold(
            PerformanceThreshold(
                metric_type=MetricType.RETRY_COUNT,
                service_name=None,
                threshold_value=3.0,  # Average 3 retries per operation
                comparison_operator=">",
                time_window=TimeWindow.FIFTEEN_MINUTES,
            )
        )

    def add_threshold(self, threshold: PerformanceThreshold) -> None:
        """Add a performance threshold."""
        self.thresholds.append(threshold)

    def remove_threshold(self, threshold: PerformanceThreshold) -> bool:
        """Remove a performance threshold."""
        if threshold in self.thresholds:
            self.thresholds.remove(threshold)
            return True
        return False

    def start_operation(
        self,
        operation_id: str,
        service_name: str,
        operation: str,
        agent_type: Optional[str] = None,
        user_id: Optional[str] = None,
        **context,
    ) -> str:
        """
        Start tracking a performance operation.

        Returns:
            correlation_id for the operation
        """
        data_point = PerformanceDataPoint(
            timestamp=datetime.now(),
            service_name=service_name,
            operation=operation,
            agent_type=agent_type,
            user_id=user_id,
            response_time_ms=0,  # Will be calculated when operation ends
            correlation_id=context.get("correlation_id", operation_id),
            session_id=context.get("session_id"),
        )

        with self.operation_lock:
            self.active_operations[operation_id] = data_point

        return data_point.correlation_id or operation_id

    def end_operation(
        self,
        operation_id: str,
        success: bool = True,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0,
        **metrics,
    ) -> Optional[PerformanceDataPoint]:
        """
        End tracking a performance operation.

        Returns:
            The completed performance data point
        """
        with self.operation_lock:
            if operation_id not in self.active_operations:
                return None

            data_point = self.active_operations.pop(operation_id)

        # Calculate response time
        end_time = datetime.now()
        data_point.response_time_ms = (
            end_time - data_point.timestamp
        ).total_seconds() * 1000

        # Update operation results
        data_point.success = success
        data_point.error_type = error_type
        data_point.error_message = error_message
        data_point.retry_count = retry_count

        # Add additional metrics
        for key, value in metrics.items():
            if hasattr(data_point, key):
                setattr(data_point, key, value)

        # Store data point
        self.data_points.append(data_point)

        # Log performance metrics
        self.mcp_logger.log_performance_metrics(
            service_name=data_point.service_name,
            operation_type=data_point.operation,
            response_time_ms=data_point.response_time_ms,
            success=success,
            retry_count=retry_count,
            error_type=error_type,
        )

        # Check thresholds if enabled
        if self.enable_real_time_metrics:
            asyncio.create_task(self._check_performance_thresholds(data_point))

        return data_point

    async def _check_performance_thresholds(
        self, data_point: PerformanceDataPoint
    ) -> None:
        """Check if performance thresholds are violated."""
        # Get recent metrics for comparison
        recent_metrics = self.get_service_metrics(
            service_name=data_point.service_name, time_window=TimeWindow.FIVE_MINUTES
        )

        if not recent_metrics:
            return

        metrics = recent_metrics[0]  # Most recent window

        # Check each threshold
        for threshold in self.thresholds:
            if (
                threshold.service_name
                and threshold.service_name != data_point.service_name
            ):
                continue

            violation = False
            current_value = None

            if threshold.metric_type == MetricType.RESPONSE_TIME:
                current_value = metrics.avg_response_time
                violation = threshold.check_threshold(current_value)
            elif threshold.metric_type == MetricType.SUCCESS_RATE:
                current_value = metrics.availability_percentage
                violation = threshold.check_threshold(current_value)
            elif threshold.metric_type == MetricType.ERROR_RATE:
                current_value = metrics.error_rate
                violation = threshold.check_threshold(current_value)
            elif threshold.metric_type == MetricType.RETRY_COUNT:
                current_value = metrics.avg_retry_count
                violation = threshold.check_threshold(current_value)

            if violation and current_value is not None:
                # Log performance threshold violation
                self.mcp_logger.logger.warning(
                    f"Performance threshold violated for {data_point.service_name}: "
                    f"{threshold.metric_type.value} ({current_value}) exceeds threshold ({threshold.threshold_value})",
                    extra={
                        "service_name": data_point.service_name,
                        "metric_type": threshold.metric_type.value,
                        "current_value": current_value,
                        "threshold_value": threshold.threshold_value,
                        "time_window": threshold.time_window.value,
                    },
                )

    def record_operation(
        self,
        service_name: str,
        operation: str,
        response_time_ms: float,
        success: bool = True,
        retry_count: int = 0,
        **kwargs,
    ) -> PerformanceDataPoint:
        """
        Record a completed operation directly.

        Use this for operations that don't use start/end tracking.
        """
        data_point = PerformanceDataPoint(
            timestamp=datetime.now(),
            service_name=service_name,
            operation=operation,
            response_time_ms=response_time_ms,
            success=success,
            retry_count=retry_count,
            **kwargs,
        )

        self.data_points.append(data_point)

        # Log performance metrics
        self.mcp_logger.log_performance_metrics(
            service_name=service_name,
            operation_type=operation,
            response_time_ms=response_time_ms,
            success=success,
            retry_count=retry_count,
        )

        return data_point

    def get_service_metrics(
        self,
        service_name: str,
        time_window: TimeWindow = TimeWindow.HOUR,
        limit: Optional[int] = None,
    ) -> List[ServiceMetrics]:
        """Get aggregated metrics for a service."""
        metrics_list = self.aggregated_metrics[service_name][time_window]

        if limit:
            return metrics_list[-limit:]

        return metrics_list

    def get_real_time_metrics(
        self, service_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get real-time performance metrics."""
        # Check cache first
        cache_key = f"realtime_{service_name or 'all'}"
        now = datetime.now()

        if (
            self._cache_last_updated
            and now - self._cache_last_updated < self._cache_ttl
            and cache_key in self._metrics_cache
        ):
            return self._metrics_cache[cache_key]

        # Calculate real-time metrics
        cutoff_time = now - timedelta(minutes=5)  # Last 5 minutes

        if service_name:
            recent_data = [
                dp
                for dp in self.data_points
                if dp.timestamp >= cutoff_time and dp.service_name == service_name
            ]
        else:
            recent_data = [dp for dp in self.data_points if dp.timestamp >= cutoff_time]

        if not recent_data:
            return {}

        # Calculate metrics
        total_requests = len(recent_data)
        successful_requests = sum(1 for dp in recent_data if dp.success)
        failed_requests = total_requests - successful_requests

        response_times = [dp.response_time_ms for dp in recent_data]
        retry_counts = [dp.retry_count for dp in recent_data]

        metrics = {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": (successful_requests / total_requests * 100)
            if total_requests > 0
            else 0,
            "error_rate": (failed_requests / total_requests * 100)
            if total_requests > 0
            else 0,
            "avg_response_time": statistics.mean(response_times)
            if response_times
            else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "p95_response_time": self._calculate_percentile(response_times, 95)
            if response_times
            else 0,
            "p99_response_time": self._calculate_percentile(response_times, 99)
            if response_times
            else 0,
            "total_retries": sum(retry_counts),
            "avg_retry_count": statistics.mean(retry_counts) if retry_counts else 0,
            "max_retry_count": max(retry_counts) if retry_counts else 0,
            "requests_per_minute": total_requests,  # 5-minute window, so multiply by 12 for per-hour
            "timestamp": now.isoformat(),
        }

        # Cache the result
        self._metrics_cache[cache_key] = metrics
        self._cache_last_updated = now

        return metrics

    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value from a list."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        n = len(sorted_values)
        index = int(n * percentile / 100)

        return sorted_values[min(index, n - 1)]

    def get_service_performance_summary(self, service_name: str) -> Dict[str, Any]:
        """Get comprehensive performance summary for a service."""
        # Get metrics for different time windows
        summary = {
            "service_name": service_name,
            "real_time": self.get_real_time_metrics(service_name),
            "last_hour": {},
            "last_day": {},
            "trends": {},
        }

        # Last hour metrics
        hour_metrics = self.get_service_metrics(service_name, TimeWindow.HOUR, limit=1)
        if hour_metrics:
            summary["last_hour"] = hour_metrics[0].to_dict()

        # Last day metrics (aggregate from hourly)
        day_metrics = self.get_service_metrics(service_name, TimeWindow.HOUR, limit=24)
        if day_metrics:
            summary["last_day"] = self._aggregate_metrics(day_metrics)

        # Calculate trends
        if len(day_metrics) >= 2:
            current = day_metrics[-1]
            previous = day_metrics[-2]

            summary["trends"] = {
                "response_time_trend": self._calculate_trend(
                    previous.avg_response_time, current.avg_response_time
                ),
                "success_rate_trend": self._calculate_trend(
                    previous.availability_percentage, current.availability_percentage
                ),
                "throughput_trend": self._calculate_trend(
                    previous.requests_per_minute, current.requests_per_minute
                ),
                "error_rate_trend": self._calculate_trend(
                    previous.error_rate, current.error_rate, inverse=True
                ),
            }

        return summary

    def _aggregate_metrics(self, metrics_list: List[ServiceMetrics]) -> Dict[str, Any]:
        """Aggregate a list of service metrics."""
        if not metrics_list:
            return {}

        total_requests = sum(m.total_requests for m in metrics_list)
        successful_requests = sum(m.successful_requests for m in metrics_list)
        failed_requests = sum(m.failed_requests for m in metrics_list)

        response_times = []
        for m in metrics_list:
            # Use average response time weighted by request count
            if m.total_requests > 0:
                response_times.extend([m.avg_response_time] * m.total_requests)

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": (successful_requests / total_requests * 100)
            if total_requests > 0
            else 0,
            "error_rate": (failed_requests / total_requests * 100)
            if total_requests > 0
            else 0,
            "avg_response_time": statistics.mean(response_times)
            if response_times
            else 0,
            "min_response_time": min(m.min_response_time for m in metrics_list),
            "max_response_time": max(m.max_response_time for m in metrics_list),
            "total_retries": sum(m.total_retries for m in metrics_list),
            "avg_retry_count": statistics.mean(
                [m.avg_retry_count for m in metrics_list]
            ),
            "requests_per_minute": statistics.mean(
                [m.requests_per_minute for m in metrics_list]
            ),
        }

    def _calculate_trend(
        self, previous: float, current: float, inverse: bool = False
    ) -> Dict[str, Any]:
        """Calculate trend between two values."""
        if previous == 0:
            change_percent = 100 if current > 0 else 0
        else:
            change_percent = ((current - previous) / previous) * 100

        # For inverse trends (like error rate), a decrease is good
        if inverse:
            trend_direction = (
                "improving"
                if change_percent < 0
                else "degrading"
                if change_percent > 0
                else "stable"
            )
        else:
            trend_direction = (
                "improving"
                if change_percent > 0
                else "degrading"
                if change_percent < 0
                else "stable"
            )

        return {
            "previous_value": round(previous, 2),
            "current_value": round(current, 2),
            "change_percent": round(change_percent, 2),
            "trend_direction": trend_direction,
        }

    def get_all_services_overview(self) -> Dict[str, Any]:
        """Get performance overview for all services."""
        services = set(dp.service_name for dp in self.data_points)

        overview = {
            "total_services": len(services),
            "services": {},
            "overall_metrics": self.get_real_time_metrics(),
            "timestamp": datetime.now().isoformat(),
        }

        for service_name in services:
            overview["services"][service_name] = self.get_real_time_metrics(
                service_name
            )

        return overview

    async def start_monitoring(self) -> None:
        """Start background monitoring tasks."""
        if self.is_running:
            return

        self.is_running = True

        # Start aggregation task
        self.aggregation_task = asyncio.create_task(self._aggregation_loop())

        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_monitoring(self) -> None:
        """Stop background monitoring tasks."""
        if not self.is_running:
            return

        self.is_running = False

        if self.aggregation_task:
            self.aggregation_task.cancel()
            try:
                await self.aggregation_task
            except asyncio.CancelledError:
                pass

        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

    async def _aggregation_loop(self) -> None:
        """Background task to aggregate metrics periodically."""
        while self.is_running:
            try:
                await self._aggregate_recent_metrics()
                await asyncio.sleep(self.aggregation_interval)
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue
                pass

    async def _cleanup_loop(self) -> None:
        """Background task to clean up old data."""
        while self.is_running:
            try:
                await self._cleanup_old_data()
                # Run cleanup every hour
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue
                pass

    async def _aggregate_recent_metrics(self) -> None:
        """Aggregate recent metrics into time windows."""
        now = datetime.now()

        # Group data points by service and time window
        services = set(dp.service_name for dp in self.data_points)

        for service_name in services:
            # Aggregate for different time windows
            for time_window in TimeWindow:
                window_size = self._get_window_size(time_window)
                window_start = now - window_size

                # Get data points in this window
                service_data = [
                    dp
                    for dp in self.data_points
                    if dp.service_name == service_name and dp.timestamp >= window_start
                ]

                if not service_data:
                    continue

                # Create aggregated metrics
                metrics = ServiceMetrics(
                    service_name=service_name,
                    time_window=time_window,
                    window_start=window_start,
                    window_end=now,
                )

                # Calculate metrics
                metrics.total_requests = len(service_data)
                metrics.successful_requests = sum(
                    1 for dp in service_data if dp.success
                )
                metrics.failed_requests = (
                    metrics.total_requests - metrics.successful_requests
                )

                # Response time calculations
                response_times = [dp.response_time_ms for dp in service_data]
                metrics.calculate_derived_metrics(response_times)

                # Error type counting
                for dp in service_data:
                    if not dp.success and dp.error_type:
                        if "timeout" in dp.error_type.lower():
                            metrics.timeout_count += 1
                        elif "connection" in dp.error_type.lower():
                            metrics.connection_error_count += 1
                        elif "auth" in dp.error_type.lower():
                            metrics.auth_error_count += 1
                        elif "rate" in dp.error_type.lower():
                            metrics.rate_limit_count += 1

                # Retry calculations
                metrics.total_retries = sum(dp.retry_count for dp in service_data)
                metrics.max_retry_count = max(
                    (dp.retry_count for dp in service_data), default=0
                )

                # Resource usage
                memory_values = [
                    dp.memory_usage_mb for dp in service_data if dp.memory_usage_mb
                ]
                cpu_values = [
                    dp.cpu_usage_percent for dp in service_data if dp.cpu_usage_percent
                ]

                if memory_values:
                    metrics.avg_memory_usage_mb = statistics.mean(memory_values)
                    metrics.peak_memory_usage_mb = max(memory_values)

                if cpu_values:
                    metrics.avg_cpu_usage_percent = statistics.mean(cpu_values)
                    metrics.peak_cpu_usage_percent = max(cpu_values)

                # Store aggregated metrics
                metrics_list = self.aggregated_metrics[service_name][time_window]

                # Replace existing metrics for this window or add new
                existing_index = -1
                for i, existing_metrics in enumerate(metrics_list):
                    if (
                        abs(
                            (
                                existing_metrics.window_start - window_start
                            ).total_seconds()
                        )
                        < 60
                    ):
                        existing_index = i
                        break

                if existing_index >= 0:
                    metrics_list[existing_index] = metrics
                else:
                    metrics_list.append(metrics)

                # Keep only recent metrics
                cutoff = now - timedelta(days=self.retention_days)
                self.aggregated_metrics[service_name][time_window] = [
                    m for m in metrics_list if m.window_start >= cutoff
                ]

        # Clear cache
        self._metrics_cache.clear()
        self._cache_last_updated = None

    def _get_window_size(self, time_window: TimeWindow) -> timedelta:
        """Get timedelta for a time window."""
        window_map = {
            TimeWindow.MINUTE: timedelta(minutes=1),
            TimeWindow.FIVE_MINUTES: timedelta(minutes=5),
            TimeWindow.FIFTEEN_MINUTES: timedelta(minutes=15),
            TimeWindow.HOUR: timedelta(hours=1),
            TimeWindow.DAY: timedelta(days=1),
            TimeWindow.WEEK: timedelta(weeks=1),
        }
        return window_map[time_window]

    async def _cleanup_old_data(self) -> None:
        """Clean up old performance data."""
        cutoff_time = datetime.now() - timedelta(days=self.retention_days)

        # Clean up raw data points
        self.data_points = deque(
            (dp for dp in self.data_points if dp.timestamp >= cutoff_time),
            maxlen=self.max_data_points,
        )

        # Clean up aggregated metrics
        for service_metrics in self.aggregated_metrics.values():
            for time_window_metrics in service_metrics.values():
                time_window_metrics[:] = [
                    m for m in time_window_metrics if m.window_start >= cutoff_time
                ]

        # Clear cache after cleanup
        self._metrics_cache.clear()
        self._cache_last_updated = None


# Global performance monitor instance
performance_monitor = MCPPerformanceMonitor()


def get_performance_monitor() -> MCPPerformanceMonitor:
    """Get the global performance monitor instance."""
    return performance_monitor


# Convenience functions for common operations
def start_mcp_operation(
    operation_id: str, service_name: str, operation: str, **kwargs
) -> str:
    """Start tracking an MCP operation."""
    return performance_monitor.start_operation(
        operation_id, service_name, operation, **kwargs
    )


def end_mcp_operation(
    operation_id: str, success: bool = True, **kwargs
) -> Optional[PerformanceDataPoint]:
    """End tracking an MCP operation."""
    return performance_monitor.end_operation(operation_id, success, **kwargs)


def record_mcp_operation(
    service_name: str,
    operation: str,
    response_time_ms: float,
    success: bool = True,
    **kwargs,
) -> PerformanceDataPoint:
    """Record a completed MCP operation."""
    return performance_monitor.record_operation(
        service_name, operation, response_time_ms, success, **kwargs
    )
