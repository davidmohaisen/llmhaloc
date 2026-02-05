"""
Logger class for LLM vulnerability function localization.

This module provides a centralized, object-oriented logging system
that can be used consistently across all modules.

"""

import os
import logging
from datetime import datetime
import colorama
from colorama import Fore, Style

# Initialize colorama for cross-platform colored terminal output
colorama.init(autoreset=True)


class CustomFormatter(logging.Formatter):
    """Custom logging formatter with colored output and timestamp formatting."""

    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        self.FORMATS = {
            logging.DEBUG: Fore.CYAN + Style.DIM + "%(asctime)s [DEBUG] %(message)s" + Style.RESET_ALL,
            logging.INFO: Fore.BLUE + "%(asctime)s [INFO] %(message)s" + Style.RESET_ALL,
            logging.WARNING: Fore.YELLOW + "%(asctime)s [WARNING] %(message)s" + Style.RESET_ALL,
            logging.ERROR: Fore.RED + "%(asctime)s [ERROR] %(message)s" + Style.RESET_ALL,
            logging.CRITICAL: Fore.RED + Style.BRIGHT + "%(asctime)s [CRITICAL] %(message)s" + Style.RESET_ALL
        }

    def formatTime(self, record, datefmt=None):
        """Format the timestamp in the log record."""
        ct = datetime.fromtimestamp(record.created)
        if datefmt:
            return ct.strftime(datefmt)
        return ct.isoformat()

    def format(self, record):
        """Format the log record with appropriate color."""
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, "%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


class Logger:
    """
    A centralized logger class that provides consistent logging across all modules.

    This class follows the Singleton pattern to ensure only one logger instance
    exists throughout the application.
    """

    _instance = None

    def __new__(cls, *_args, **_kwargs):
        """
        Ensure only one Logger instance exists (Singleton pattern).

        Args:
            *_args: Variable length argument list (unused)
            **_kwargs: Arbitrary keyword arguments (unused)

        Returns:
            Logger: The singleton Logger instance
        """
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config=None):
        """
        Initialize the logger if it hasn't been initialized yet.

        Args:
            config (dict, optional): Configuration dictionary containing logging settings.
                                    If None, the logger will be initialized later.
        """
        if self._initialized:
            return

        self._root_logger = logging.getLogger()
        self._root_logger.setLevel(logging.INFO)

        # Clear any existing handlers
        if self._root_logger.handlers:
            self._root_logger.handlers.clear()

        # Store config for later use
        self.config = config

        # If config is provided, initialize the logger
        if config:
            self.initialize(config)
        else:
            self._initialized = True

            # Add a default console handler for now
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(CustomFormatter())
            self._root_logger.addHandler(console_handler)

    def initialize(self, config):
        """
        Initialize the logger with the provided configuration.

        Args:
            config (dict): Configuration dictionary containing logging settings
        """
        self.config = config

        # Get machine name and log directory
        machine_name = config['machine']['name']
        log_dir = config['output']['log_dir']

        # Ensure log directory exists
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            print(f"{Fore.GREEN}Created logs directory: {log_dir}")

        # Get error log file name from configuration
        error_log_file = config['logging'].get('error_log_file', 'errors.log')
        self.error_log_path = os.path.join(log_dir, error_log_file)

        # Clear any existing handlers
        if self._root_logger.handlers:
            self._root_logger.handlers.clear()

        # Create error file handler (for ERROR and WARNING levels only)
        error_file_handler = logging.FileHandler(self.error_log_path)
        error_file_handler.setLevel(logging.WARNING)  # Capture WARNING and above (ERROR, CRITICAL)
        error_file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', "%Y-%m-%d %H:%M:%S"))

        # Create console handler with custom formatter (for all levels)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(CustomFormatter())

        # Add handlers to logger
        self._root_logger.addHandler(error_file_handler)
        self._root_logger.addHandler(console_handler)

        self._initialized = True

        # Log initialization
        self.info(f"Logging initialized - Errors and warnings will be saved to: {self.error_log_path}")
        self.info(f"Machine: {machine_name}")

        # Log a test warning to ensure error logging is working
        self.warning("Test warning message - This should appear in the error log file")
        self.info("Normal logs will only appear in the console, not in any log file")

    def debug(self, message):
        """Log a debug message."""
        self._root_logger.debug(message)

    def info(self, message):
        """Log an info message."""
        self._root_logger.info(message)

    def warning(self, message):
        """Log a warning message."""
        self._root_logger.warning(message)

    def error(self, message):
        """Log an error message."""
        self._root_logger.error(message)

    def critical(self, message):
        """Log a critical message."""
        self._root_logger.critical(message)

    def section(self, message):
        """Log a section header with special formatting."""
        self._root_logger.info(f"{Fore.MAGENTA}{message}")

    def success(self, message):
        """Log a success message with special formatting."""
        self._root_logger.info(f"{Fore.GREEN}{message}")

    def progress(self, current, total, message=""):
        """
        Log a progress message.

        Args:
            current (int): Current progress value
            total (int): Total progress value
            message (str, optional): Additional message to include
        """
        percent = (current / total) * 100

        if percent < 25:
            color = Fore.RED
        elif percent < 75:
            color = Fore.YELLOW
        else:
            color = Fore.GREEN

        progress_bar = f"[{current}/{total}] ({percent:.2f}%)"
        self._root_logger.info(f"{color}{progress_bar} {message}")

    def separator(self, char="=", length=80, color=Fore.MAGENTA):
        """Log a separator line."""
        self._root_logger.info(f"{color}{char * length}")

    def time_estimate(self, current, total, time_data):
        """
        Log time estimation information.

        Args:
            current (int): Current progress value
            total (int): Total progress value
            time_data (dict): Dictionary containing time estimation data
        """
        percent = time_data.get('progress_percentage', (current / total) * 100)

        # Determine color based on progress
        if percent < 25:
            color = Fore.RED
        elif percent < 75:
            color = Fore.YELLOW
        else:
            color = Fore.GREEN

        # Format time values
        avg_time = time_data.get('avg_time_per_entry', 0)
        elapsed = time_data.get('elapsed_time', 0)
        remaining = time_data.get('estimated_remaining_time', 0)
        completion_time = time_data.get('estimated_completion_time', 'Unknown')

        # Format times for display
        if isinstance(completion_time, str) and 'T' in completion_time:
            # Convert ISO format to readable format
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(completion_time)
                completion_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Keep the original string if it can't be parsed
                pass

        # Format durations
        def format_time(seconds):
            hours, remainder = divmod(int(seconds), 3600)
            minutes, seconds = divmod(remainder, 60)

            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"

        elapsed_str = format_time(elapsed)
        remaining_str = format_time(remaining)

        # Log the time estimates
        progress_bar = f"[{current}/{total}] ({percent:.2f}%)"
        self._root_logger.info(f"{color}{progress_bar} Time per entry: {avg_time:.2f}s")
        self._root_logger.info(f"{color}Elapsed: {elapsed_str} | Remaining: {remaining_str}")
        self._root_logger.info(f"{color}Estimated completion: {completion_time}")
