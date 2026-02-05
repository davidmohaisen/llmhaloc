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

# Constants
DEFAULT_LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
DEFAULT_DETAILED_LOG_FORMAT = '%(asctime)s [%(levelname)s] [File: %(filename)s:%(lineno)d] %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_LOG_DIR = '00_logs'
DEFAULT_ERROR_LOG_FILE = 'errors.log'
DEFAULT_WARNING_LOG_FILE = 'warnings.log'


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

        # Set up default log file paths
        self.error_log_path = os.path.join(DEFAULT_LOG_DIR, DEFAULT_ERROR_LOG_FILE)
        self.warning_log_path = os.path.join(DEFAULT_LOG_DIR, DEFAULT_WARNING_LOG_FILE)

        # Ensure the log directory exists
        log_dir = os.path.dirname(self.error_log_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            print(f"{Fore.GREEN}Created logs directory: {log_dir}")

        # Add error file handler (for ERROR and CRITICAL levels only)
        try:
            error_file_handler = logging.FileHandler(self.error_log_path, mode='w')  # Overwrite existing file
            error_file_handler.setLevel(logging.ERROR)  # Capture ERROR and above
            error_formatter = logging.Formatter(
                DEFAULT_DETAILED_LOG_FORMAT,
                DEFAULT_DATE_FORMAT
            )
            error_file_handler.setFormatter(error_formatter)
            self._root_logger.addHandler(error_file_handler)
        except Exception as e:
            print(f"{Fore.RED}Failed to create error log file: {e}")

        # Add warning file handler (for WARNING level only)
        try:
            warning_file_handler = logging.FileHandler(self.warning_log_path, mode='w')  # Overwrite existing file
            warning_file_handler.setLevel(logging.WARNING)
            warning_file_handler.addFilter(lambda record: record.levelno == logging.WARNING)  # Only WARNING level
            warning_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] [File: %(filename)s:%(lineno)d] %(message)s',
                DEFAULT_DATE_FORMAT
            )
            warning_file_handler.setFormatter(warning_formatter)
            self._root_logger.addHandler(warning_file_handler)
        except Exception as e:
            print(f"{Fore.RED}Failed to create warning log file: {e}")

        # Add a default console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(CustomFormatter())
        self._root_logger.addHandler(console_handler)

        # If config is provided, initialize the logger with the config
        if config:
            self.initialize(config)
        else:
            self._initialized = True
            self.info("Logging initialized with default settings")
            self.info(f"Errors will be saved to: {self.error_log_path}")
            self.info(f"Warnings will be saved to: {self.warning_log_path}")

    def initialize(self, config):
        """
        Initialize the logger with the provided configuration.

        Args:
            config (dict): Configuration dictionary containing logging settings
        """
        self.config = config

        # Get log directory from configuration
        log_dir = config['output']['log_dir']

        # Ensure log directory exists
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            print(f"{Fore.GREEN}Created logs directory: {log_dir}")

        # Get log file names from configuration
        error_log_file = config.get('logging', {}).get('error_log_file', DEFAULT_ERROR_LOG_FILE)
        warning_log_file = config.get('logging', {}).get('warning_log_file', DEFAULT_WARNING_LOG_FILE)

        self.error_log_path = os.path.join(log_dir, error_log_file)
        self.warning_log_path = os.path.join(log_dir, warning_log_file)

        # Clear any existing handlers
        if self._root_logger.handlers:
            self._root_logger.handlers.clear()

        # Add error file handler (for ERROR and CRITICAL levels only)
        try:
            error_file_handler = logging.FileHandler(self.error_log_path, mode='w')  # Overwrite existing file
            error_file_handler.setLevel(logging.ERROR)  # Capture ERROR and above
            error_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] [File: %(filename)s:%(lineno)d] %(message)s',
                DEFAULT_DATE_FORMAT
            )
            error_file_handler.setFormatter(error_formatter)
            self._root_logger.addHandler(error_file_handler)
        except Exception as e:
            print(f"{Fore.RED}Failed to create error log file: {e}")
            # Create a fallback error log file in the current directory
            try:
                fallback_path = DEFAULT_ERROR_LOG_FILE
                error_file_handler = logging.FileHandler(fallback_path, mode='w')
                error_file_handler.setLevel(logging.ERROR)
                error_file_handler.setFormatter(error_formatter)
                self._root_logger.addHandler(error_file_handler)
                print(f"{Fore.YELLOW}Using fallback error log file: {fallback_path}")
                self.error_log_path = fallback_path
            except Exception as e2:
                print(f"{Fore.RED}Failed to create fallback error log file: {e2}")
                print(f"{Fore.RED}Errors will only be displayed in the console")

        # Add warning file handler (for WARNING level only)
        try:
            warning_file_handler = logging.FileHandler(self.warning_log_path, mode='w')  # Overwrite existing file
            warning_file_handler.setLevel(logging.WARNING)
            warning_file_handler.addFilter(lambda record: record.levelno == logging.WARNING)  # Only WARNING level
            warning_formatter = logging.Formatter(
                DEFAULT_DETAILED_LOG_FORMAT,
                DEFAULT_DATE_FORMAT
            )
            warning_file_handler.setFormatter(warning_formatter)
            self._root_logger.addHandler(warning_file_handler)
        except Exception as e:
            print(f"{Fore.RED}Failed to create warning log file: {e}")
            # No fallback for warnings as they're less critical

        # Create console handler with custom formatter (for all levels)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(CustomFormatter())
        self._root_logger.addHandler(console_handler)

        self._initialized = True

        # Log initialization
        self.info("Logging initialized with updated settings")
        self.info(f"Errors will be saved to: {self.error_log_path}")
        self.info(f"Warnings will be saved to: {self.warning_log_path}")

        # Log a test warning to ensure warning logging is working
        self.warning("Test warning message - This should appear in the warning log file")
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

    def _write_to_error_log(self, level, message, exc_info=False):
        """
        Write a message directly to the error log file.

        Args:
            level (str): Log level (ERROR, CRITICAL, etc.)
            message (str): The message to log
            exc_info (bool, optional): Whether to include exception information. Defaults to False.
        """
        try:
            with open(self.error_log_path, 'a') as f:
                timestamp = datetime.now().strftime(DEFAULT_DATE_FORMAT)
                f.write(f"{timestamp} [{level}] {message}\n")
                if exc_info:
                    import traceback
                    f.write(traceback.format_exc())
                    f.write("\n")
        except Exception:
            # If we can't write to the log file, just continue
            pass

    def error(self, message, exc_info=False):
        """
        Log an error message.

        Args:
            message (str): The error message to log
            exc_info (bool, optional): Whether to include exception information. Defaults to False.
        """
        self._root_logger.error(message, exc_info=exc_info)

        # Also write to the error log file directly to ensure it's captured
        self._write_to_error_log("ERROR", message, exc_info)

    def critical(self, message, exc_info=True):
        """
        Log a critical message.

        Args:
            message (str): The critical message to log
            exc_info (bool, optional): Whether to include exception information. Defaults to True.
        """
        self._root_logger.critical(message, exc_info=exc_info)

        # Also write to the error log file directly to ensure it's captured
        self._write_to_error_log("CRITICAL", message, exc_info)

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

    def _get_progress_color(self, percent):
        """
        Get the color to use for progress based on percentage.

        Args:
            percent (float): Progress percentage (0-100)

        Returns:
            str: Color code from colorama.Fore
        """
        if percent < 25:
            return Fore.RED
        elif percent < 75:
            return Fore.YELLOW
        else:
            return Fore.GREEN

    def _format_iso_datetime(self, iso_datetime):
        """
        Format an ISO datetime string to a human-readable format.

        Args:
            iso_datetime (str): ISO format datetime string

        Returns:
            str: Formatted datetime string
        """
        if isinstance(iso_datetime, str) and 'T' in iso_datetime:
            # Convert ISO format to readable format
            try:
                dt = datetime.fromisoformat(iso_datetime)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Keep the original string if it can't be parsed
                pass
        return iso_datetime

    def _format_time_duration(self, seconds):
        """
        Format a time duration in seconds to a human-readable string.

        Args:
            seconds (float): Time in seconds

        Returns:
            str: Formatted time string (e.g., "2h 30m 45s")
        """
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def global_progress(self, current_file, total_files, file_name, time_data=None):
        """
        Display global progress information with time estimates.

        Args:
            current_file (int): Current file index (1-based)
            total_files (int): Total number of files
            file_name (str): Name of the current file
            time_data (dict, optional): Dictionary containing time estimation data
        """
        # Calculate progress percentage
        percent = (current_file / total_files) * 100 if total_files > 0 else 0
        color = self._get_progress_color(percent)

        # Create a header for the global progress section
        self.separator("-", 80)
        self._root_logger.info(f"{Fore.MAGENTA}GLOBAL PROGRESS - Processing file {current_file}/{total_files}")

        # Format the progress bar with fixed width
        progress_bar = f"[{current_file:3d}/{total_files:3d}] ({percent:6.2f}%)"
        self._root_logger.info(f"{color}{progress_bar} Current file: {file_name}")

        # If time data is provided, display time estimates
        if time_data:
            # Extract time values
            elapsed = time_data.get('elapsed_time', 0)
            remaining = time_data.get('estimated_remaining_time', 0)
            avg_time = time_data.get('avg_time_per_file', 0)
            completion_time = time_data.get('estimated_completion_time', 'Unknown')

            # Format time values
            completion_time = self._format_iso_datetime(completion_time)
            elapsed_str = self._format_time_duration(elapsed)
            remaining_str = self._format_time_duration(remaining)

            # Log the time estimates with fixed width formatting
            self._root_logger.info(f"{color}Average time per file: {avg_time:8.2f}s")
            self._root_logger.info(f"{color}Elapsed: {elapsed_str:15s} | Remaining: {remaining_str:15s}")
            self._root_logger.info(f"{color}Estimated completion time: {completion_time}")

        self.separator("-", 80)

    def file_progress(self, current_function, total_functions, function_info, time_data=None):
        """
        Display file-level progress information with time estimates.

        Args:
            current_function (int): Current function index (1-based)
            total_functions (int): Total number of functions in the file
            function_info (dict): Dictionary with function identifiers (id, sub_id, code_id, function_id)
            time_data (dict, optional): Dictionary containing time estimation data
        """
        # Calculate progress percentage
        percent = (current_function / total_functions) * 100 if total_functions > 0 else 0
        color = self._get_progress_color(percent)

        # Create a header for the file progress section
        self._root_logger.info(f"{Fore.CYAN}FILE PROGRESS - Processing function {current_function}/{total_functions}")

        # Format the progress bar with fixed width
        progress_bar = f"[{current_function:4d}/{total_functions:4d}] ({percent:6.2f}%)"

        # Format function identifier
        function_id = (
            f"ID:{function_info.get('id', 'Unknown')}, "
            f"Sub_ID:{function_info.get('sub_id', 'Unknown')}, "
            f"Code_ID:{function_info.get('code_id', 'Unknown')}, "
            f"Function_ID:{function_info.get('function_id', 'Unknown')}"
        )

        self._root_logger.info(f"{color}{progress_bar} {function_id}")

        # If time data is provided, display time estimates
        if time_data:
            # Extract time values
            avg_time = time_data.get('avg_time_per_entry', 0)
            elapsed = time_data.get('elapsed_time', 0)
            remaining = time_data.get('estimated_remaining_time', 0)
            completion_time = time_data.get('estimated_completion_time', 'Unknown')
            entries_per_minute = time_data.get('entries_per_minute', 0)

            # Format time values
            completion_time = self._format_iso_datetime(completion_time)
            elapsed_str = self._format_time_duration(elapsed)
            remaining_str = self._format_time_duration(remaining)

            # Log the time estimates with fixed width formatting
            self._root_logger.info(f"{color}Processing rate: {entries_per_minute:6.2f} functions/minute")
            self._root_logger.info(f"{color}Average time per function: {avg_time:8.2f}s")
            self._root_logger.info(f"{color}Elapsed: {elapsed_str:15s} | Remaining: {remaining_str:15s}")
            self._root_logger.info(f"{color}Estimated completion time: {completion_time}")

        self.separator("-", 60)

    def time_estimate(self, current, total, time_data):
        """
        Log time estimation information (legacy method, kept for compatibility).

        Args:
            current (int): Current progress value
            total (int): Total progress value
            time_data (dict): Dictionary containing time estimation data
        """
        # Get progress percentage
        percent = time_data.get('progress_percentage', (current / total) * 100)
        color = self._get_progress_color(percent)

        # Extract time values
        avg_time = time_data.get('avg_time_per_entry', 0)
        elapsed = time_data.get('elapsed_time', 0)
        remaining = time_data.get('estimated_remaining_time', 0)
        completion_time = time_data.get('estimated_completion_time', 'Unknown')

        # Format time values
        completion_time = self._format_iso_datetime(completion_time)
        elapsed_str = self._format_time_duration(elapsed)
        remaining_str = self._format_time_duration(remaining)

        # Log the time estimates
        progress_bar = f"[{current}/{total}] ({percent:.2f}%)"
        self._root_logger.info(f"{color}{progress_bar} Time per entry: {avg_time:.2f}s")
        self._root_logger.info(f"{color}Elapsed: {elapsed_str} | Remaining: {remaining_str}")
        self._root_logger.info(f"{color}Estimated completion time: {completion_time}")
