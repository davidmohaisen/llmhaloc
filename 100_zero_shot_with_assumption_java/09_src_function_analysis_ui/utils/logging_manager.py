"""
Logging manager for the LLM Vulnerability Function Localization Web Processing.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

from .config_manager import config


class ElementNotFoundFilter(logging.Filter):
    """
    Filter to suppress repetitive 'Element not found' messages from the frontend.
    """
    def filter(self, record):
        if "Element not found for key" in record.getMessage():
            return False  # Don't log these messages
        return True


class LoggingManager:
    """
    Logging manager for the application.
    Handles setting up and configuring logging.
    """

    def __init__(self):
        """
        Initialize the logging manager.
        """
        self.logs_dir = config.get_logs_dir()
        self.level = self._get_log_level(config.get_logging_level())
        self.format = config.get_logging_format()
        self.file_rotation = config.get('logging.file_rotation', True)
        self.max_bytes = config.get('logging.max_bytes', 10485760)  # 10MB
        self.backup_count = config.get('logging.backup_count', 5)

        # Create logs directory if it doesn't exist
        os.makedirs(self.logs_dir, exist_ok=True)

        # Always clear log files on startup
        self._clear_log_files()

        # Set up logging
        self._setup_logging()

    def _get_log_level(self, level_str: str) -> int:
        """
        Convert a string log level to a logging level constant.

        Args:
            level_str: The log level as a string.

        Returns:
            The log level as a logging constant.
        """
        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        # Default to WARNING instead of DEBUG for less verbose logging
        return levels.get(level_str.upper(), logging.WARNING)

    def _clear_log_files(self):
        """
        Clear all log files in the logs directory.
        """
        for log_file in ['server.log', 'errors.log', 'frontend_errors.log']:
            log_path = os.path.join(self.logs_dir, log_file)
            if os.path.exists(log_path):
                with open(log_path, 'w') as f:
                    f.write('')
        print("Log files cleared on startup")

    def _setup_logging(self):
        """
        Set up logging with the configured settings.
        """
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Set up basic configuration
        logging.basicConfig(
            level=self.level,
            format=self.format,
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )

        # Add filter to suppress repetitive messages
        root_logger.addFilter(ElementNotFoundFilter())

        # Add file handlers
        self._add_file_handler('server.log')
        self._add_file_handler('errors.log', logging.ERROR)
        self._add_file_handler('frontend_errors.log', logging.ERROR)

    def _add_file_handler(self, filename: str, level: Optional[int] = None):
        """
        Add a file handler to the root logger.

        Args:
            filename: The name of the log file.
            level: The log level for this handler. If None, uses the default level.
        """
        if level is None:
            level = self.level

        log_path = os.path.join(self.logs_dir, filename)

        # Always use non-rotating file handlers and clear files on startup
        handler = logging.FileHandler(log_path)

        handler.setLevel(level)
        formatter = logging.Formatter(self.format)
        handler.setFormatter(formatter)
        handler.addFilter(ElementNotFoundFilter())
        logging.getLogger().addHandler(handler)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger with the specified name.

        Args:
            name: The name of the logger.

        Returns:
            A logger instance.
        """
        return logging.getLogger(name)


# Create a singleton instance
logging_manager = LoggingManager()

# Create a default logger
logger = logging_manager.get_logger('app')
