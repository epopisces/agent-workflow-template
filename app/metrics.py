# Copyright (c) 2024. All rights reserved.
"""Metrics Collection for Agent Operations.

Tracks and stores performance metrics including response times, token usage,
and operation statistics for agent workflows.
"""

import json
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

# Logger for metrics
logger = logging.getLogger("workflow.metrics")

# Default metrics directory
DEFAULT_METRICS_DIR = Path("metrics")


@dataclass
class OperationMetric:
    """Metrics for a single agent operation."""
    operation: str
    agent: str
    start_time: str  # ISO format timestamp
    end_time: str | None = None
    duration_seconds: float = 0.0
    success: bool = True
    error_message: str | None = None
    input_length: int = 0
    output_length: int = 0
    chunk_count: int = 0  # For streaming operations
    model: str | None = None  # Model used for processing
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class SessionMetrics:
    """Aggregated metrics for a session."""
    session_id: str
    session_start: str
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_duration_seconds: float = 0.0
    average_duration_seconds: float = 0.0
    operations: list[OperationMetric] = field(default_factory=list)
    
    def add_operation(self, metric: OperationMetric) -> None:
        """Add an operation metric to the session."""
        self.operations.append(metric)
        self.total_operations += 1
        if metric.success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
        self.total_duration_seconds += metric.duration_seconds
        if self.total_operations > 0:
            self.average_duration_seconds = self.total_duration_seconds / self.total_operations
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "session_start": self.session_start,
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "average_duration_seconds": round(self.average_duration_seconds, 3),
            "operations": [op.to_dict() for op in self.operations],
        }


class MetricsCollector:
    """Collects and stores metrics for agent operations.
    
    Metrics are stored in JSON format in the metrics directory,
    organized by date for easy analysis.
    """
    
    def __init__(
        self,
        metrics_dir: Path | str | None = None,
        enabled: bool = True,
    ):
        """Initialize the metrics collector.
        
        Args:
            metrics_dir: Directory to store metrics files.
            enabled: Whether metrics collection is enabled.
        """
        self._metrics_dir = Path(metrics_dir) if metrics_dir else DEFAULT_METRICS_DIR
        self._enabled = enabled
        
        # Current session
        self._session = SessionMetrics(
            session_id=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
            session_start=datetime.now(timezone.utc).isoformat(),
        )
        
        # Ensure metrics directory exists
        if self._enabled:
            self._metrics_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Metrics collector initialized: {self._metrics_dir}")
    
    @property
    def enabled(self) -> bool:
        """Check if metrics collection is enabled."""
        return self._enabled
    
    @property
    def session(self) -> SessionMetrics:
        """Get current session metrics."""
        return self._session
    
    def _get_metrics_file(self) -> Path:
        """Get the metrics file path for today."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._metrics_dir / f"metrics_{date_str}.jsonl"
    
    def record(
        self,
        operation: str,
        agent: str,
        duration_seconds: float,
        success: bool = True,
        error_message: str | None = None,
        input_length: int = 0,
        output_length: int = 0,
        chunk_count: int = 0,
        model: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OperationMetric | None:
        """Record a completed operation.
        
        Args:
            operation: Type of operation (e.g., "query", "scrape", "ingest").
            agent: Name of the agent performing the operation.
            duration_seconds: How long the operation took.
            success: Whether the operation succeeded.
            error_message: Error message if failed.
            input_length: Length of input (characters or tokens).
            output_length: Length of output (characters or tokens).
            chunk_count: Number of chunks for streaming operations.
            model: Model identifier used for processing.
            metadata: Additional metadata to record.
            
        Returns:
            The recorded OperationMetric, or None if disabled.
        """
        if not self._enabled:
            return None
            
        now = datetime.now(timezone.utc)
        metric = OperationMetric(
            operation=operation,
            agent=agent,
            start_time=(now.timestamp() - duration_seconds).__str__(),
            end_time=now.isoformat(),
            duration_seconds=round(duration_seconds, 3),
            success=success,
            error_message=error_message,
            input_length=input_length,
            output_length=output_length,
            chunk_count=chunk_count,
            model=model,
            metadata=metadata or {},
        )
        
        self._session.add_operation(metric)
        logger.debug(
            f"Recorded metric: {operation} by {agent} - "
            f"{duration_seconds:.2f}s, success={success}"
        )
        
        # Always append to daily log for durability (efficient append operation)
        self._append_metric(metric)
            
        return metric
    
    def _append_metric(self, metric: OperationMetric) -> None:
        """Append a single metric to the daily file."""
        try:
            metrics_file = self._get_metrics_file()
            with open(metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(metric.to_dict()) + "\n")
            logger.debug(f"Appended metric to {metrics_file}")
        except Exception as e:
            logger.warning(f"Failed to append metric: {e}")
    
    def save_session(self) -> Path | None:
        """Save the current session metrics to a file.
        
        Returns:
            Path to the saved file, or None if disabled/failed.
        """
        if not self._enabled or self._session.total_operations == 0:
            return None
            
        try:
            session_file = self._metrics_dir / f"session_{self._session.session_id}.json"
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(self._session.to_dict(), f, indent=2)
            logger.info(f"Session metrics saved: {session_file}")
            return session_file
        except Exception as e:
            logger.error(f"Failed to save session metrics: {e}")
            return None
    
    def get_summary(self) -> dict[str, Any]:
        """Get a summary of current session metrics.
        
        Returns:
            Dictionary with summary statistics.
        """
        return {
            "total_operations": self._session.total_operations,
            "successful": self._session.successful_operations,
            "failed": self._session.failed_operations,
            "total_time_seconds": round(self._session.total_duration_seconds, 2),
            "average_time_seconds": round(self._session.average_duration_seconds, 2),
        }
    
    @contextmanager
    def measure(
        self,
        operation: str,
        agent: str,
        metadata: dict[str, Any] | None = None,
    ) -> Generator["MetricContext", None, None]:
        """Context manager for measuring an operation.
        
        Args:
            operation: Type of operation.
            agent: Name of the agent.
            metadata: Additional metadata.
            
        Yields:
            MetricContext for tracking the operation.
            
        Example:
            with collector.measure("query", "coordinator") as ctx:
                result = await agent.run(query)
                ctx.set_output(result)
        """
        ctx = MetricContext(self, operation, agent, metadata)
        try:
            yield ctx
        except Exception as e:
            ctx.set_error(str(e))
            raise
        finally:
            ctx.finish()


class MetricContext:
    """Context for tracking a single operation's metrics."""
    
    def __init__(
        self,
        collector: MetricsCollector,
        operation: str,
        agent: str,
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize metric context.
        
        Args:
            collector: The metrics collector.
            operation: Type of operation.
            agent: Name of the agent.
            metadata: Additional metadata.
        """
        self._collector = collector
        self._operation = operation
        self._agent = agent
        self._metadata = metadata or {}
        self._start_time = time.time()
        self._input_length = 0
        self._output_length = 0
        self._chunk_count = 0
        self._success = True
        self._error_message: str | None = None
        self._finished = False
        
    def set_input(self, input_data: str | int) -> None:
        """Set input length."""
        self._input_length = len(input_data) if isinstance(input_data, str) else input_data
        
    def set_output(self, output_data: str | int) -> None:
        """Set output length."""
        self._output_length = len(output_data) if isinstance(output_data, str) else output_data
        
    def add_chunk(self) -> None:
        """Increment chunk count for streaming operations."""
        self._chunk_count += 1
        
    def set_error(self, error_message: str) -> None:
        """Mark operation as failed."""
        self._success = False
        self._error_message = error_message
        
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the metric."""
        self._metadata[key] = value
        
    def finish(self) -> None:
        """Finalize and record the metric."""
        if self._finished:
            return
        self._finished = True
        
        duration = time.time() - self._start_time
        self._collector.record(
            operation=self._operation,
            agent=self._agent,
            duration_seconds=duration,
            success=self._success,
            error_message=self._error_message,
            input_length=self._input_length,
            output_length=self._output_length,
            chunk_count=self._chunk_count,
            metadata=self._metadata,
        )


# Global metrics collector instance (lazy loaded)
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance.
    
    Returns:
        MetricsCollector instance.
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def configure_metrics(
    metrics_dir: Path | str | None = None,
    enabled: bool = True,
) -> MetricsCollector:
    """Configure and get the global metrics collector.
    
    Args:
        metrics_dir: Directory to store metrics files.
        enabled: Whether metrics collection is enabled.
        
    Returns:
        Configured MetricsCollector instance.
    """
    global _metrics_collector
    _metrics_collector = MetricsCollector(
        metrics_dir=metrics_dir,
        enabled=enabled,
    )
    return _metrics_collector
