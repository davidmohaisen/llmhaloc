"""
Logging setup for LLM vulnerability function localization.

This module handles setting up logging with custom formatters and handlers.

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


def setup_logging(config):
    """
    Set up logging with custom formatter and handlers.
    Creates log directory if it doesn't exist.
    
    Args:
        config (dict): Configuration dictionary containing logging settings
    """
    machine_name = config['machine']['name']
    log_dir = config['output']['log_dir']
    
    # Ensure log directory exists
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        print(f"{Fore.GREEN}Created logs directory: {log_dir}")
    
    # Create machine-specific log file name
    log_file_name = f"{machine_name}.log"
    log_file_path = os.path.join(log_dir, log_file_name)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Create file handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', "%Y-%m-%d %H:%M:%S"))
    
    # Create console handler with custom formatter
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(CustomFormatter())
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logging.info(f"Logging initialized to {log_file_path}")
    
    return log_file_path
