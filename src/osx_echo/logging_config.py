"""
Centralized logging configuration for OSX Echo.

This module provides consistent logging setup with performance metrics tracking
and structured output for debugging and monitoring.
"""

import logging
import json
import time
from contextlib import contextmanager
from typing import Dict, Any, Optional
from functools import wraps


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs for easier parsing."""

    def format(self, record):
        """Format log record as JSON for structured logging."""
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        if hasattr(record, "audio_size_bytes"):
            log_obj["audio_size_bytes"] = record.audio_size_bytes
        if hasattr(record, "transcribed_length"):
            log_obj["transcribed_length"] = record.transcribed_length
        if hasattr(record, "language"):
            log_obj["language"] = record.language
        if hasattr(record, "device_name"):
            log_obj["device_name"] = record.device_name

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter with performance metrics."""

    def __init__(self):
        super().__init__(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            "%(performance_suffix)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record):
        """Format with optional performance metrics appended."""
        # Add performance suffix if metrics are present
        perf_parts = []
        if hasattr(record, "duration_ms"):
            perf_parts.append(f"duration={record.duration_ms:.2f}ms")
        if hasattr(record, "audio_size_bytes"):
            perf_parts.append(f"size={record.audio_size_bytes}B")
        if hasattr(record, "transcribed_length"):
            perf_parts.append(f"chars={record.transcribed_length}")

        record.performance_suffix = f" [{', '.join(perf_parts)}]" if perf_parts else ""

        return super().format(record)


class PerformanceLogger:
    """Logger wrapper with performance tracking capabilities."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    @contextmanager
    def track_operation(self, operation_name: str, **extra_fields):
        """
        Context manager to track operation duration and log metrics.

        Usage:
            with logger.track_operation("transcription", language="en") as tracker:
                # Do work here
                tracker.set("transcribed_length", len(text))

        Args:
            operation_name: Name of the operation being tracked
            **extra_fields: Additional fields to include in the log
        """
        start_time = time.perf_counter()
        tracker = OperationTracker()

        try:
            yield tracker
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Merge tracker fields with extra fields
            all_fields = {**extra_fields, **tracker.fields}
            all_fields["duration_ms"] = duration_ms

            self.logger.info(
                f"{operation_name} completed in {duration_ms:.2f}ms",
                extra=all_fields,
            )

    def log_metric(self, message: str, **metrics):
        """
        Log a message with associated metrics.

        Args:
            message: Log message
            **metrics: Metric key-value pairs
        """
        self.logger.info(message, extra=metrics)


class OperationTracker:
    """Tracker for collecting metrics during an operation."""

    def __init__(self):
        self.fields: Dict[str, Any] = {}

    def set(self, key: str, value: Any):
        """Set a metric value."""
        self.fields[key] = value

    def increment(self, key: str, amount: int = 1):
        """Increment a counter metric."""
        self.fields[key] = self.fields.get(key, 0) + amount


def setup_logging(
    level: str = "INFO",
    structured: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure logging for the entire application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: If True, use JSON structured logging
        log_file: Optional file path to write logs to
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    if structured:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(HumanReadableFormatter())
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter())  # Always structured for files
        root_logger.addHandler(file_handler)


def get_performance_logger(name: str) -> PerformanceLogger:
    """
    Get a performance logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        PerformanceLogger instance
    """
    return PerformanceLogger(logging.getLogger(name))


def log_performance(func):
    """
    Decorator to automatically log function performance.

    Usage:
        @log_performance
        def my_function():
            # Function code here
            pass
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_performance_logger(func.__module__)

        with logger.track_operation(
            f"{func.__name__}",
            module=func.__module__,
            function=func.__name__,
        ) as tracker:
            result = func(*args, **kwargs)

            # Try to extract meaningful metrics from result
            if isinstance(result, str):
                tracker.set("result_length", len(result))
            elif isinstance(result, (list, tuple, dict)):
                tracker.set("result_size", len(result))

            return result

    return wrapper
