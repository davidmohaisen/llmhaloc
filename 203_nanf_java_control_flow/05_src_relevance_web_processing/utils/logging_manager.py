"""
Logging Manager for the LLM Vulnerability Function Localization Web Processing System.

"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

from utils.config_manager import config


class LoggingManager:
    """
    Singleton class to manage logging configuration.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggingManager, cls).__new__(cls)
        return cls._instance

    def initialize(
        self, logger_name: Optional[str] = None, force_reinit: bool = True
    ) -> None:
        """
        Initialize the logging system.

        Args:
            logger_name: Optional name for the logger
            force_reinit: Force reinitialization even if already initialized
        """
        if self._initialized and not force_reinit:
            return

        # Create logs directory if it doesn't exist
        logs_dir = config.get_logs_dir()
        os.makedirs(logs_dir, exist_ok=True)

        # Get logging configuration
        log_level_str = config.get_logging_level()
        log_format = config.get_logging_format()

        # Convert string log level to logging constant
        log_level = getattr(logging, log_level_str)

        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Configure root logger
        root_logger.setLevel(log_level)

        # Create formatter
        formatter = logging.Formatter(log_format)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Create file handler
        log_file = os.path.join(logs_dir, f"{logger_name or 'app'}.log")

        # Always use 'w' mode to overwrite log file on restart
        file_handler = logging.FileHandler(log_file, mode="w")

        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        logging.info(f"Logging initialized at level {log_level_str}")
        self._initialized = True

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger with the specified name.

        Args:
            name: Name for the logger

        Returns:
            A configured logger instance
        """
        if not self._initialized:
            self.initialize()
        return logging.getLogger(name)


# Create a singleton instance
log_manager = LoggingManager()
