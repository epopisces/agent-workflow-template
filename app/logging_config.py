"""Logging configuration for Multi-Agent Workflow.

Provides consistent logging across the application with configurable levels.
Uses Python standard logging conventions:
- DEBUG: Detailed information for diagnosing problems
- INFO: Confirmation that things are working as expected  
- WARNING: Indication of unexpected events
- ERROR: Serious problem preventing function execution
- CRITICAL: Program may not be able to continue
"""

import logging
import sys
from typing import Literal

# Log format with timestamp, level, logger name, and message
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"

# Logger names for different components
LOGGER_ROOT = "workflow"
LOGGER_COORDINATOR = "workflow.coordinator"
LOGGER_URL_SCRAPER = "workflow.url_scraper"
LOGGER_CONFIG = "workflow.config"
LOGGER_CLI = "workflow.cli"


def setup_logging(
    level: int | str = logging.INFO,
    log_file: str | None = None,
) -> logging.Logger:
    """Configure logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Can be string or logging constant.
        log_file: Optional file path to write logs to.
        
    Returns:
        The root workflow logger.
    """
    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    # Get root workflow logger
    logger = logging.getLogger(LOGGER_ROOT)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    
    # Console handler (stderr for visibility)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific component.
    
    Args:
        name: Logger name (should start with 'workflow.')
        
    Returns:
        Logger instance.
    """
    return logging.getLogger(name)


# Convenience functions for getting component loggers
def get_coordinator_logger() -> logging.Logger:
    """Get the coordinator agent logger."""
    return logging.getLogger(LOGGER_COORDINATOR)


def get_url_scraper_logger() -> logging.Logger:
    """Get the URL scraper agent logger."""
    return logging.getLogger(LOGGER_URL_SCRAPER)


def get_config_logger() -> logging.Logger:
    """Get the configuration logger."""
    return logging.getLogger(LOGGER_CONFIG)


def get_cli_logger() -> logging.Logger:
    """Get the CLI logger."""
    return logging.getLogger(LOGGER_CLI)
