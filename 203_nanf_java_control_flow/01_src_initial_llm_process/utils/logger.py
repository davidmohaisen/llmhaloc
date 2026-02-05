"""
Logger class for LLM vulnerability function localization.

This module provides a centralized, object-oriented logging system
that can be used consistently across all modules.

"""

import os
import logging
import traceback
from datetime import datetime
import colorama
from colorama import Fore, Style
import socket
import platform
import sys
import json

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
        if getattr(self, '_initialized', False):
            return

        self._root_logger = logging.getLogger()
        self._root_logger.setLevel(logging.INFO)

        # Clear any existing handlers
        if self._root_logger.handlers:
            self._root_logger.handlers.clear()

        # Store config for later use
        self.config = config

        # Initialize log files
        self.error_log_path = None
        self.warning_log_path = None
        self.error_handler = None
        self.warning_handler = None
        self.file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [PID:%(process)d] %(message)s',
            "%Y-%m-%d %H:%M:%S"
        )
        self.system_info = self._collect_system_info()

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

    def _collect_system_info(self):
        """
        Collect system information for logging.

        Returns:
            dict: System information including hostname, platform, Python version, etc.
        """
        return {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python_version": sys.version,
            "timestamp": datetime.now().isoformat(),
            "process_id": os.getpid()
        }

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

        # Get log file names from configuration
        error_log_file = config['logging'].get('error_log_file', 'errors.log')
        warning_log_file = "warnings.log"  # New separate file for warnings

        # Create full paths
        self.error_log_path = os.path.join(log_dir, error_log_file)
        self.warning_log_path = os.path.join(log_dir, warning_log_file)

        # Clear any existing handlers
        if self._root_logger.handlers:
            self._root_logger.handlers.clear()

        # Create custom file handlers that only create files when needed
        self.error_handler = None
        self.warning_handler = None

        # Create console handler with custom formatter (for all levels)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(CustomFormatter())

        # Add only the console handler initially
        self._root_logger.addHandler(console_handler)

        # Store formatter for later use when creating file handlers
        self.file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [PID:%(process)d] %(message)s',
            "%Y-%m-%d %H:%M:%S"
        )

        self._initialized = True

        # Log initialization to console only
        self.info(f"Logging initialized - Errors will be saved to: {self.error_log_path} (when needed)")
        self.info(f"Warnings will be saved to: {self.warning_log_path} (when needed)")
        self.info(f"Machine: {machine_name}")

    def _log_system_info(self, log_type=None):
        """
        Log system information to log files.

        Args:
            log_type (str, optional): Type of log file to write to ('error', 'warning', or None for both)
        """
        # Don't do anything if no log type is specified and no handlers exist
        if log_type is None and self.error_handler is None and self.warning_handler is None:
            return

        system_info_str = json.dumps(self.system_info, indent=2)
        session_header = f"\n--- NEW SESSION STARTED AT {datetime.now().isoformat()} ---\n"
        system_info = f"SYSTEM INFO:\n{system_info_str}\n\n"

        # Write to error log if requested or if no specific type
        if (log_type == 'error' or log_type is None) and self.error_log_path is not None:
            # Check if the directory exists
            log_dir = os.path.dirname(self.error_log_path)
            if os.path.exists(log_dir):
                try:
                    with open(self.error_log_path, 'a') as f:
                        f.write(session_header)
                        f.write(system_info)
                except (IOError, PermissionError) as e:
                    # Just print to console if we can't write to the file
                    print(f"{Fore.YELLOW}Warning: Could not write to error log: {e}")

        # Write to warning log if requested or if no specific type
        if (log_type == 'warning' or log_type is None) and self.warning_log_path is not None:
            # Check if the directory exists
            log_dir = os.path.dirname(self.warning_log_path)
            if os.path.exists(log_dir):
                try:
                    with open(self.warning_log_path, 'a') as f:
                        f.write(session_header)
                        f.write(system_info)
                except (IOError, PermissionError) as e:
                    # Just print to console if we can't write to the file
                    print(f"{Fore.YELLOW}Warning: Could not write to warning log: {e}")

    def debug(self, message):
        """Log a debug message."""
        self._root_logger.debug(message)

    def info(self, message):
        """Log an info message."""
        self._root_logger.info(message)

    def _ensure_warning_handler(self):
        """Ensure the warning handler is created and added to the logger."""
        # Check if warning_log_path is None, which means the logger wasn't properly initialized
        if self.warning_log_path is None:
            # Use a default path in the current directory if not initialized
            self.warning_log_path = os.path.join(os.getcwd(), "00_logs", "warnings.log")
            # Ensure the directory exists
            log_dir = os.path.dirname(self.warning_log_path)
            if not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir)
                    print(f"{Fore.YELLOW}Warning: Created default log directory: {log_dir}")
                except Exception as e:
                    print(f"{Fore.RED}Error: Could not create default log directory: {e}")
                    # If we can't create the directory, just log to console
                    return False

        if self.warning_handler is None:
            try:
                # Create the log directory if it doesn't exist
                log_dir = os.path.dirname(self.warning_log_path)
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)

                # Create the warning handler
                self.warning_handler = logging.FileHandler(self.warning_log_path)
                self.warning_handler.setLevel(logging.WARNING)
                self.warning_handler.addFilter(lambda record: record.levelno == logging.WARNING)
                self.warning_handler.setFormatter(self.file_formatter)

                # Add the handler to the logger
                self._root_logger.addHandler(self.warning_handler)

                # Log system information to the warning log
                self._log_system_info('warning')

                return True
            except (IOError, PermissionError) as e:
                print(f"{Fore.YELLOW}Warning: Could not create warning log file: {e}")
                return False
        elif not os.path.exists(self.warning_log_path):
            # File was deleted, recreate it
            self._root_logger.removeHandler(self.warning_handler)
            self.warning_handler = None
            return self._ensure_warning_handler()
        return True

    def _ensure_error_handler(self):
        """Ensure the error handler is created and added to the logger."""
        # Check if error_log_path is None, which means the logger wasn't properly initialized
        if self.error_log_path is None:
            # Use a default path in the current directory if not initialized
            self.error_log_path = os.path.join(os.getcwd(), "00_logs", "errors.log")
            # Ensure the directory exists
            log_dir = os.path.dirname(self.error_log_path)
            if not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir)
                    print(f"{Fore.YELLOW}Warning: Created default log directory: {log_dir}")
                except Exception as e:
                    print(f"{Fore.RED}Error: Could not create default log directory: {e}")
                    # If we can't create the directory, just log to console
                    return False

        if self.error_handler is None:
            try:
                # Create the log directory if it doesn't exist
                log_dir = os.path.dirname(self.error_log_path)
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)

                # Create the error handler
                self.error_handler = logging.FileHandler(self.error_log_path)
                self.error_handler.setLevel(logging.ERROR)
                self.error_handler.setFormatter(self.file_formatter)

                # Add the handler to the logger
                self._root_logger.addHandler(self.error_handler)

                # Log system information to the error log
                self._log_system_info('error')

                return True
            except (IOError, PermissionError) as e:
                print(f"{Fore.YELLOW}Warning: Could not create error log file: {e}")
                return False
        elif not os.path.exists(self.error_log_path):
            # File was deleted, recreate it
            self._root_logger.removeHandler(self.error_handler)
            self.error_handler = None
            return self._ensure_error_handler()
        return True

    def warning(self, message, process_info=None):
        """
        Log a warning message with optional process information.

        Args:
            message (str): The warning message
            process_info (dict, optional): Additional process information to include
        """
        # Ensure warning handler exists before logging
        self._ensure_warning_handler()

        if process_info:
            message = f"[{process_info}] {message}"
        self._root_logger.warning(message)

    def error(self, message, exc_info=False, process_info=None):
        """
        Log an error message with optional exception info and process information.

        Args:
            message (str): The error message
            exc_info (bool, optional): Whether to include exception info
            process_info (dict, optional): Additional process information to include
        """
        # Ensure error handler exists before logging
        self._ensure_error_handler()

        if process_info:
            message = f"[{process_info}] {message}"

        if exc_info:
            self._root_logger.error(message, exc_info=True)
        else:
            self._root_logger.error(message)

    def critical(self, message, exc_info=False, process_info=None):
        """
        Log a critical message with optional exception info and process information.

        Args:
            message (str): The critical message
            exc_info (bool, optional): Whether to include exception info
            process_info (dict, optional): Additional process information to include
        """
        # Ensure error handler exists before logging (critical uses the same handler)
        self._ensure_error_handler()

        if process_info:
            message = f"[{process_info}] {message}"

        if exc_info:
            self._root_logger.critical(message, exc_info=True)
        else:
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
            progress_icon = "⬤"  # Red circle for early progress
        elif percent < 75:
            color = Fore.YELLOW
            progress_icon = "⬤"  # Yellow circle for mid progress
        else:
            color = Fore.GREEN
            progress_icon = "⬤"  # Green circle for late progress

        # Format with fixed width for better alignment
        progress_bar = f"[{current:4d}/{total:4d}] ({percent:6.2f}%)"
        self._root_logger.info(f"{color}{progress_icon} PROGRESS: {progress_bar} {message}")

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
            time_icon = "⏱"  # Clock icon for time
        elif percent < 75:
            color = Fore.YELLOW
            time_icon = "⏱"  # Clock icon for time
        else:
            color = Fore.GREEN
            time_icon = "⏱"  # Clock icon for time

        # Format time values
        avg_time = time_data.get('avg_time_per_entry', 0)
        weighted_avg = time_data.get('weighted_avg_time', 0)
        elapsed = time_data.get('elapsed_time', 0)
        remaining = time_data.get('estimated_remaining_time', 0)
        completion_time = time_data.get('estimated_completion_time', 'Unknown')
        entries_per_minute = time_data.get('entries_per_minute', 0)

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

        # Format durations using the class method
        elapsed_str = self._format_time_duration(elapsed)
        remaining_str = self._format_time_duration(remaining)

        # Create a visually distinct section for time estimates using symbols and fixed-width formatting
        self._root_logger.info("")
        self._root_logger.info(f"{color}▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ TIME ESTIMATES ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓")

        # Show processing rates with indentation for visual hierarchy
        rate_info = f"{color}  {time_icon} Average: {avg_time:.2f}s/entry"
        if weighted_avg > 0:
            rate_info += f" | Weighted: {weighted_avg:.2f}s/entry"
        if entries_per_minute > 0:
            rate_info += f" | Rate: {entries_per_minute:.2f} entries/min"
        self._root_logger.info(rate_info)

        # Show time information with indentation
        time_info = f"{color}  {time_icon} Elapsed: {elapsed_str} | Remaining: {remaining_str}"
        self._root_logger.info(time_info)

        # Show completion time with indentation
        completion_info = f"{color}  {time_icon} Estimated completion: {completion_time}"
        self._root_logger.info(completion_info)

        # End with a fixed-width separator
        self._root_logger.info(f"{color}▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓")
        self._root_logger.info("")

    def global_progress(self, current_model, total_models, models_completed, process_start_time, time_estimates=None):
        """
        Log global progress across all models.

        Args:
            current_model (int): Current model index (1-based)
            total_models (int): Total number of models
            models_completed (int): Number of models completed
            process_start_time (float): Start time of the entire process
            time_estimates (dict, optional): Time estimates for remaining models
        """
        import time

        # Calculate progress percentage and determine color
        percent = (current_model / total_models) * 100
        color = self._get_progress_color(percent)

        # Calculate elapsed time
        elapsed = time.time() - process_start_time
        elapsed_str = self._format_time_duration(elapsed)

        # Format the global progress bar with fixed width
        progress_bar = f"[{current_model:2d}/{total_models:2d}] ({percent:6.2f}%)"
        completed_bar = f"Completed: {models_completed:2d}/{total_models:2d}"

        # Use a fixed-width separator for global progress
        self._root_logger.info("")
        self._root_logger.info(f"{Fore.CYAN}▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ GLOBAL PROGRESS SUMMARY ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓")

        # Add the main progress information
        progress_line = f"{color}  ▶ Progress: {progress_bar} {completed_bar} | Elapsed: {elapsed_str}"
        self._root_logger.info(progress_line)

        # Add time estimates if available
        if time_estimates:
            self._add_time_estimates_to_global_progress(time_estimates, color)

        # End with a fixed-width separator
        self._root_logger.info(f"{Fore.CYAN}▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓")
        self._root_logger.info("")

    def _get_progress_color(self, percent):
        """Get the appropriate color based on progress percentage."""
        if percent < 25:
            return Fore.RED
        elif percent < 75:
            return Fore.YELLOW
        else:
            return Fore.GREEN

    def _box_line(self, content, color=Fore.CYAN, content_color=None):
        """
        Create a line in the box with proper alignment.

        Args:
            content (str): Content to display in the box
            color (str): Color for the box outline
            content_color (str, optional): Color for the content. If None, uses the box color.

        Returns:
            str: Formatted box line
        """
        box_width = self._get_terminal_width()
        if content_color is None:
            content_color = color

        # Get the true content length without ANSI codes
        content_length = len(self._strip_ansi(content))

        # If content is too long for the box, truncate it
        if content_length > box_width - 5:  # Leave some space for "..." and borders
            # Find a good place to truncate
            max_content_length = box_width - 7  # 2 for borders, 3 for "...", 2 for safety
            truncated_content = content[:max_content_length] + "..."
            content = truncated_content
            content_length = len(self._strip_ansi(content))

        # Calculate padding to ensure the box is properly aligned
        padding = box_width - 2 - content_length

        return f"{color}│{content_color}{content}{' ' * padding}{color}│"

    def _strip_ansi(self, text):
        """
        Strip ANSI color codes from text to get the true length.

        Args:
            text (str): Text with possible ANSI color codes

        Returns:
            str: Text without ANSI color codes
        """
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def _get_terminal_width(self):
        """
        Get the current terminal width.

        Returns:
            int: Width of the terminal in characters, defaults to 80 if can't be determined
        """
        try:
            import shutil
            terminal_width = shutil.get_terminal_size().columns
            # Ensure a reasonable minimum width
            return max(terminal_width, 80)
        except Exception:
            # Default to 80 if we can't determine the terminal width
            return 80

    def _start_box(self, title, color=Fore.CYAN):
        """
        Start a box with a title.

        Args:
            title (str): Title to display in the box header
            color (str): Color for the box
        """
        box_width = self._get_terminal_width()
        padding = (box_width - 2 - len(title)) // 2

        self._root_logger.info("")
        self._root_logger.info(f"{color}┌{'─' * (box_width - 2)}┐")
        self._root_logger.info(f"{color}│{' ' * padding}{title}{' ' * (box_width - 2 - padding - len(title))}│")
        self._root_logger.info(f"{color}├{'─' * (box_width - 2)}┤")

    def _end_box(self, color=Fore.CYAN):
        """
        End a box.

        Args:
            color (str): Color for the box
        """
        box_width = self._get_terminal_width()
        self._root_logger.info(f"{color}└{'─' * (box_width - 2)}┘")
        self._root_logger.info("")

    def _add_time_estimates_to_global_progress(self, time_estimates, color):
        """Add time estimates to the global progress summary."""
        from datetime import datetime

        # Get remaining time and completion time
        remaining = time_estimates.get('estimated_remaining_time', 0)
        completion_time = time_estimates.get('estimated_completion_time')
        avg_model_time = time_estimates.get('avg_model_time', 0)
        total_completed_time = time_estimates.get('total_completed_time', 0)

        # Format the remaining time
        remaining_str = self._format_time_duration(remaining)

        # Format the completion time
        completion_time = self._format_completion_time(completion_time)

        # Format the total completed time
        completed_time_str = self._format_time_duration(total_completed_time)

        # Create a visually distinct section for global time estimates
        self._root_logger.info(f"{color}▓▓▓▓▓▓▓▓▓▓▓▓▓▓ GLOBAL TIME ESTIMATES ▓▓▓▓▓▓▓▓▓▓▓▓▓▓")

        # Format the average model time if available
        if avg_model_time > 0:
            avg_time_str = self._format_time_duration(avg_model_time)
            self._root_logger.info(f"{color}  ⏱ Avg. time per model: {avg_time_str}")

        # Log the time estimates with consistent indentation
        self._root_logger.info(f"{color}  ⏱ Time spent on completed models: {completed_time_str}")
        self._root_logger.info(f"{color}  ⏱ Remaining: {remaining_str} | Estimated completion: {completion_time}")

        # Show completed models if available
        if 'completed_models' in time_estimates:
            self.add_completed_models_to_global_progress(time_estimates.get('completed_models', {}))

        # If we have model-specific estimates, show them
        if 'model_estimates' in time_estimates:
            self._add_model_estimates_to_global_progress(time_estimates['model_estimates'], color)

    def _format_completion_time(self, completion_time):
        """Format the completion time from ISO format to readable format."""
        if isinstance(completion_time, str) and 'T' in completion_time:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(completion_time)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        return completion_time

    def _add_model_estimates_to_global_progress(self, model_estimates, color):
        """Add model-specific estimates to the global progress summary."""
        if not model_estimates:
            return

        # Add a visual separator with fixed width
        self._root_logger.info(f"{color}  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓")
        self._root_logger.info(f"{color}  📋 Models remaining:")

        # Show at most 5 models to avoid cluttering
        models_to_show = list(model_estimates.items())[:5]
        for i, (model_name, estimate) in enumerate(models_to_show, 1):
            est_str = self._format_time_duration(estimate)
            model_info = f"    {i}. {model_name}: {est_str}"
            self._root_logger.info(f"{color}{model_info}")

        # If there are more models, show a summary
        if len(model_estimates) > 5:
            more_info = f"    ... and {len(model_estimates) - 5} more models"
            self._root_logger.info(f"{color}{more_info}")

    def add_completed_models_to_global_progress(self, completed_models):
        """Add completed models to the global progress summary."""
        if not completed_models:
            return

        # Add a visual separator with fixed width
        self._root_logger.info(f"{Fore.GREEN}  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓")
        self._root_logger.info(f"{Fore.GREEN}  ✓ Completed models:")

        # Show at most 5 models to avoid cluttering
        models_to_show = list(completed_models.items())[:5]
        for i, (model_name, data) in enumerate(models_to_show, 1):
            time_str = self._format_time_duration(data.get('processing_time', 0))
            entries = data.get('entry_count', 0)
            model_info = f"    {i}. {model_name}: {time_str} ({entries} entries)"
            self._root_logger.info(f"{Fore.GREEN}{model_info}")

        # If there are more models, show a summary
        if len(completed_models) > 5:
            more_info = f"    ... and {len(completed_models) - 5} more models completed"
            self._root_logger.info(f"{Fore.GREEN}{more_info}")

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
