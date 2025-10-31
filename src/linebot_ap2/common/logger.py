"""Logging configuration for LINE Bot AP2."""

import logging
import sys
from typing import Optional
from datetime import datetime


def setup_logger(
    name: str = "linebot_ap2",
    level: str = "INFO",
    log_file: Optional[str] = None
) -> logging.Logger:
    """Set up structured logging for the application."""
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent duplicate logs
    logger.propagate = False
    
    return logger


def log_agent_interaction(
    logger: logging.Logger,
    user_id: str,
    intent: str,
    message: str,
    response: str,
    processing_time: float
):
    """Log agent interaction for monitoring and debugging."""
    logger.info(
        f"Agent Interaction | "
        f"User: {user_id} | "
        f"Intent: {intent} | "
        f"Message: {message[:100]}{'...' if len(message) > 100 else ''} | "
        f"Response: {response[:100]}{'...' if len(response) > 100 else ''} | "
        f"Time: {processing_time:.3f}s"
    )


def log_payment_event(
    logger: logging.Logger,
    event_type: str,
    user_id: str,
    mandate_id: str,
    amount: Optional[float] = None,
    status: str = "unknown"
):
    """Log payment-related events for audit trail."""
    logger.info(
        f"Payment Event | "
        f"Type: {event_type} | "
        f"User: {user_id} | "
        f"Mandate: {mandate_id} | "
        f"Amount: {amount} | "
        f"Status: {status}"
    )


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: str,
    user_id: Optional[str] = None
):
    """Log errors with contextual information."""
    logger.error(
        f"Error | "
        f"Context: {context} | "
        f"User: {user_id or 'N/A'} | "
        f"Error: {str(error)} | "
        f"Type: {type(error).__name__}"
    )