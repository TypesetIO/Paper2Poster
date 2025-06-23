"""
Centralized logging configuration for PosterAgent module.
Provides consistent logging across all poster generation components.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class PosterAgentLogger:
    """Centralized logger for PosterAgent with consistent formatting and levels."""
    
    _loggers = {}
    _initialized = False
    
    @classmethod
    def setup_logging(cls, 
                     log_level: str = "INFO",
                     log_file: Optional[str] = None,
                     enable_console: bool = True) -> None:
        """
        Setup logging configuration for all PosterAgent components.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file (optional)
            enable_console: Whether to log to console
        """
        if cls._initialized:
            return
            
        # Create logs directory if it doesn't exist
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger('PosterAgent')
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, log_level.upper()))
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, log_level.upper()))
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance for a specific component.
        
        Args:
            name: Logger name (typically the module name)
            
        Returns:
            Logger instance
        """
        if not cls._initialized:
            cls.setup_logging()
        
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(f'PosterAgent.{name}')
        
        return cls._loggers[name]


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger instance.
    
    Args:
        name: Logger name (typically __name__ or module name)
        
    Returns:
        Logger instance
    """
    return PosterAgentLogger.get_logger(name)


# Token consumption logging helper
def log_token_consumption(logger: logging.Logger, 
                         component: str, 
                         input_tokens: int, 
                         output_tokens: int) -> None:
    """
    Log token consumption in a consistent format.
    
    Args:
        logger: Logger instance
        component: Component name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
    """
    logger.info(f"{component} token consumption: {input_tokens} -> {output_tokens}")


# Progress logging helper
def log_progress(logger: logging.Logger, 
                component: str, 
                message: str, 
                level: str = "INFO") -> None:
    """
    Log progress messages in a consistent format.
    
    Args:
        logger: Logger instance
        component: Component name
        message: Progress message
        level: Log level
    """
    log_func = getattr(logger, level.lower())
    log_func(f"[{component}] {message}")


# Error logging helper
def log_error_and_retry(logger: logging.Logger, 
                       component: str, 
                       error_msg: str, 
                       retry_attempt: Optional[int] = None) -> None:
    """
    Log error messages with retry information.
    
    Args:
        logger: Logger instance
        component: Component name
        error_msg: Error message
        retry_attempt: Current retry attempt number
    """
    if retry_attempt:
        logger.warning(f"[{component}] {error_msg} (Attempt {retry_attempt})")
    else:
        logger.error(f"[{component}] {error_msg}") 