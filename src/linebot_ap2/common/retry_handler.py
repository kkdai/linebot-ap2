"""Retry handler with exponential backoff and circuit breaker pattern."""

import asyncio
import time
import functools
from typing import Any, Callable, Optional, Type, Union, List
from dataclasses import dataclass
from enum import Enum

from .logger import setup_logger


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, not allowing requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    # Circuit breaker settings
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: float = 30.0


class CircuitBreaker:
    """Circuit breaker implementation for preventing cascade failures."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.logger = setup_logger("circuit_breaker")
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function through circuit breaker."""
        
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.config.timeout_seconds:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                self.logger.info("Circuit breaker moved to HALF_OPEN state")
            else:
                raise CircuitBreakerError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.logger.info("Circuit breaker moved to CLOSED state")
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.logger.warning("Circuit breaker moved to OPEN state from HALF_OPEN")
            elif self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                self.logger.warning("Circuit breaker moved to OPEN state due to failures")
            
            raise


class CircuitBreakerError(Exception):
    """Circuit breaker is open."""
    pass


class RetryableError(Exception):
    """Error that should trigger a retry."""
    pass


class NonRetryableError(Exception):
    """Error that should not trigger a retry."""
    pass


class RetryHandler:
    """Enhanced retry handler with circuit breaker and exponential backoff."""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self.circuit_breaker = CircuitBreaker(self.config)
        self.logger = setup_logger("retry_handler")
    
    def retry(
        self,
        retryable_exceptions: Union[Type[Exception], List[Type[Exception]]] = (Exception,),
        non_retryable_exceptions: Union[Type[Exception], List[Type[Exception]]] = (NonRetryableError,)
    ):
        """Decorator for adding retry logic to functions."""
        
        if not isinstance(retryable_exceptions, (list, tuple)):
            retryable_exceptions = [retryable_exceptions]
        
        if not isinstance(non_retryable_exceptions, (list, tuple)):
            non_retryable_exceptions = [non_retryable_exceptions]
        
        def decorator(func: Callable):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._execute_with_retry(
                    func, args, kwargs, retryable_exceptions, non_retryable_exceptions
                )
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if asyncio.iscoroutinefunction(func):
                    # Run async function in sync context
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(async_wrapper(*args, **kwargs))
                    finally:
                        loop.close()
                else:
                    # Handle sync function
                    return asyncio.run(self._execute_with_retry(
                        func, args, kwargs, retryable_exceptions, non_retryable_exceptions
                    ))
            
            # Return appropriate wrapper based on function type
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    async def _execute_with_retry(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        retryable_exceptions: List[Type[Exception]],
        non_retryable_exceptions: List[Type[Exception]]
    ):
        """Execute function with retry logic."""
        
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                # Execute through circuit breaker
                result = await self.circuit_breaker.call(func, *args, **kwargs)
                
                if attempt > 0:
                    self.logger.info(f"Function succeeded on attempt {attempt + 1}")
                
                return result
                
            except CircuitBreakerError:
                self.logger.error("Circuit breaker is open, failing fast")
                raise
                
            except Exception as e:
                last_exception = e
                
                # Check if exception is non-retryable
                if any(isinstance(e, exc_type) for exc_type in non_retryable_exceptions):
                    self.logger.error(f"Non-retryable error: {str(e)}")
                    raise
                
                # Check if exception is retryable
                if not any(isinstance(e, exc_type) for exc_type in retryable_exceptions):
                    self.logger.error(f"Non-retryable error (not in allowed list): {str(e)}")
                    raise
                
                # Log retry attempt
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"All {self.config.max_attempts} attempts failed")
        
        # All attempts failed
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for exponential backoff with jitter."""
        
        delay = self.config.initial_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            import random
            # Add random jitter (±25%)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(delay, 0.1)  # Minimum delay of 100ms


class ErrorHandler:
    """Enhanced error handler for categorizing and handling different error types."""
    
    def __init__(self):
        self.logger = setup_logger("error_handler")
        
        # Error categorization
        self.network_errors = (
            ConnectionError, 
            TimeoutError,
            OSError
        )
        
        self.temporary_errors = (
            RetryableError,
            *self.network_errors
        )
        
        self.permanent_errors = (
            NonRetryableError,
            ValueError,
            TypeError,
            AttributeError
        )
    
    def categorize_error(self, error: Exception) -> str:
        """Categorize error for appropriate handling."""
        
        if isinstance(error, self.permanent_errors):
            return "permanent"
        elif isinstance(error, self.temporary_errors):
            return "temporary"
        elif isinstance(error, CircuitBreakerError):
            return "circuit_breaker"
        else:
            return "unknown"
    
    def create_error_response(
        self, 
        error: Exception, 
        context: str = "",
        user_friendly: bool = True
    ) -> dict:
        """Create structured error response."""
        
        error_category = self.categorize_error(error)
        
        response = {
            "error": True,
            "error_type": type(error).__name__,
            "error_category": error_category,
            "context": context,
            "timestamp": time.time()
        }
        
        if user_friendly:
            response["message"] = self._get_user_friendly_message(error, error_category)
        else:
            response["message"] = str(error)
            response["details"] = {
                "error_class": error.__class__.__module__ + "." + error.__class__.__name__,
                "args": error.args if error.args else []
            }
        
        # Add retry information for temporary errors
        if error_category == "temporary":
            response["retry_info"] = {
                "can_retry": True,
                "suggested_delay": 5.0,
                "max_retries": 3
            }
        elif error_category == "circuit_breaker":
            response["retry_info"] = {
                "can_retry": False,
                "reason": "Service temporarily unavailable",
                "try_again_after": 30.0
            }
        else:
            response["retry_info"] = {
                "can_retry": False,
                "reason": "Permanent error"
            }
        
        return response
    
    def _get_user_friendly_message(self, error: Exception, category: str) -> str:
        """Get user-friendly error message."""
        
        if category == "network":
            return "無法連接到服務，請檢查網路連線後重試。"
        elif category == "temporary":
            return "服務暫時無法使用，請稍後重試。"
        elif category == "circuit_breaker":
            return "服務目前正在維護中，請稍後再試。"
        elif category == "permanent":
            return "請求格式錯誤，請檢查輸入資料。"
        else:
            return "系統發生未預期的錯誤，請聯繫客服。"


# Global instances for easy import
default_retry_handler = RetryHandler()
default_error_handler = ErrorHandler()


# Convenience decorators
def retry_on_failure(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    retryable_exceptions: Union[Type[Exception], List[Type[Exception]]] = (Exception,)
):
    """Simple retry decorator with default configuration."""
    
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=initial_delay
    )
    
    handler = RetryHandler(config)
    return handler.retry(retryable_exceptions=retryable_exceptions)


def handle_errors(context: str = "", user_friendly: bool = True):
    """Error handling decorator."""
    
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_response = default_error_handler.create_error_response(
                    e, context, user_friendly
                )
                default_error_handler.logger.error(
                    f"Error in {func.__name__}: {str(e)}", 
                    extra={"error_response": error_response}
                )
                return error_response
        
        return wrapper
    
    return decorator