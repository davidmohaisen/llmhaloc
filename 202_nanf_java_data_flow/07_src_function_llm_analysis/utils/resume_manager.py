"""
Resume point management utilities for vulnerability function localization.

This module handles saving, loading, and updating resume points for processing.
Resume points are stored as JSON files in the 00_logs/resume_points directory.

"""

import os
import json
from datetime import datetime
from .logger import Logger

# Initialize logger
logger = Logger()


def _ensure_resume_directory(log_dir):
    """
    Ensure the resume points directory exists.

    Args:
        log_dir (str): Base log directory

    Returns:
        str: Path to the resume points directory
    """
    resume_dir = os.path.join(log_dir, "resume_points")
    if not os.path.exists(resume_dir):
        os.makedirs(resume_dir)
        logger.info(f"Created resume points directory: {resume_dir}")
    return resume_dir


def _get_resume_file_path(log_dir, file_name):
    """
    Get the path to the resume point file for a file.

    Args:
        log_dir (str): Base log directory
        file_name (str): Name of the file being processed

    Returns:
        str: Path to the resume point file
    """
    resume_dir = _ensure_resume_directory(log_dir)
    # Remove .json extension if present
    base_name = file_name.replace('.json', '')
    filename = f"{base_name}_resume.json"
    return os.path.join(resume_dir, filename)


class ResumeState:
    """
    Class for managing resume state for vulnerability function localization.

    This class provides a more efficient way to track and manage resume points
    by maintaining a persistent record of the last processed file and function.
    It handles the hierarchical relationship between files and functions.
    """

    def __init__(self, log_dir):
        """
        Initialize the resume state manager.

        Args:
            log_dir (str): Base log directory for storing resume state
        """
        self.log_dir = log_dir
        self.current_file = None
        self.current_file_name = None
        self.last_processed = None
        self.index = 0
        self.total = 0
        self.progress_percentage = 0
        self.completed = False
        self.timestamp = None
        self.failed_entries = []
        self.time_estimates = None

    def load_state(self, file_name):
        """
        Load resume state for a specific file.

        Args:
            file_name (str): Name of the file to load state for

        Returns:
            bool: True if state was loaded successfully, False otherwise
        """
        try:
            resume_file = _get_resume_file_path(self.log_dir, file_name)
            if not os.path.exists(resume_file):
                logger.info(f"No resume point found for {file_name}")
                return False

            with open(resume_file, 'r') as f:
                resume_data = json.load(f)

            self.current_file_name = file_name
            self.last_processed = resume_data.get('last_processed', {})
            self.index = resume_data.get('index', 0)
            self.total = resume_data.get('total', 0)
            self.progress_percentage = resume_data.get('progress_percentage', 0)
            self.completed = resume_data.get('completed', False)
            self.timestamp = resume_data.get('timestamp')
            self.failed_entries = resume_data.get('failed_entries', [])
            self.time_estimates = resume_data.get('time_estimates')

            logger.info(f"Loaded resume state for {file_name}: "
                       f"ID:{self.last_processed.get('id')}, "
                       f"Sub_ID:{self.last_processed.get('sub_id')}, "
                       f"Code_ID:{self.last_processed.get('code_id')}, "
                       f"Function_ID:{self.last_processed.get('function_id')}, "
                       f"Progress: {self.progress_percentage:.2f}%")
            return True

        except Exception as e:
            logger.error(f"Error loading resume state for {file_name}: {e}")
            return False

    def save_state(self, file_name, entry, index, total, time_estimates=None, completed=False):
        """
        Save the current resume state for a file.

        Args:
            file_name (str): Name of the file being processed
            entry (dict): The last processed entry
            index (int): Current processing index
            total (int): Total number of entries
            time_estimates (dict, optional): Time estimates dictionary
            completed (bool, optional): Whether processing is completed

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update internal state
            self.current_file_name = file_name
            self.last_processed = {
                "id": entry.get('id'),
                "sub_id": entry.get('sub_id'),
                "code_id": entry.get('code_id'),
                "function_id": entry.get('function_id')
            }
            self.index = index
            self.total = total
            self.progress_percentage = round((index / total) * 100, 2) if total > 0 else 0
            self.completed = completed
            self.timestamp = datetime.now().isoformat()
            self.time_estimates = time_estimates

            # Create resume point data structure
            resume_data = {
                "file_name": file_name,
                "last_processed": self.last_processed,
                "index": self.index,
                "total": self.total,
                "progress_percentage": self.progress_percentage,
                "completed": self.completed,
                "timestamp": self.timestamp,
                "failed_entries": self.failed_entries,
                "failed_count": len(self.failed_entries)
            }

            # Add time estimates if provided
            if time_estimates:
                resume_data["time_estimates"] = time_estimates

            # Save to file
            resume_file = _get_resume_file_path(self.log_dir, file_name)
            with open(resume_file, 'w') as f:
                json.dump(resume_data, f, indent=2)

            logger.info(f"Saved resume state for {file_name} at index {index}/{total} ({self.progress_percentage:.2f}%)")
            return True

        except Exception as e:
            logger.error(f"Error saving resume state for {file_name}: {e}")
            return False

    def add_failed_entry(self, entry):
        """
        Add a failed entry to the resume state.

        Args:
            entry (dict): The failed entry to add

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            entry_id = (
                entry.get('id'),
                entry.get('sub_id'),
                entry.get('code_id'),
                entry.get('function_id')
            )

            if entry_id not in self.failed_entries:
                self.failed_entries.append(entry_id)
                logger.info(f"Added failed entry to resume state: ID:{entry_id[0]}, "
                           f"Sub_ID:{entry_id[1]}, Code_ID:{entry_id[2]}, Function_ID:{entry_id[3]}")
            return True
        except Exception as e:
            logger.error(f"Error adding failed entry to resume state: {e}")
            return False

    def clear_state(self, file_name=None):
        """
        Clear the resume state for a file.

        Args:
            file_name (str, optional): Name of the file to clear state for.
                                      If None, uses the current file name.

        Returns:
            bool: True if successful, False otherwise
        """
        file_to_clear = file_name or self.current_file_name
        if not file_to_clear:
            logger.warning("No file specified for clearing resume state")
            return False

        try:
            resume_file = _get_resume_file_path(self.log_dir, file_to_clear)
            if os.path.exists(resume_file):
                os.remove(resume_file)
                logger.info(f"Cleared resume point for {file_to_clear}")

                # Reset internal state if clearing the current file
                if file_to_clear == self.current_file_name:
                    self.current_file_name = None
                    self.last_processed = None
                    self.index = 0
                    self.total = 0
                    self.progress_percentage = 0
                    self.completed = False
                    self.timestamp = None
                    self.failed_entries = []
                    self.time_estimates = None
                return True
            return True
        except Exception as e:
            logger.error(f"Error clearing resume state for {file_to_clear}: {e}")
            return False

    def find_resume_index(self, ground_truth_data):
        """
        Find the index in ground truth data to resume from based on current state.

        Args:
            ground_truth_data (list): List of ground truth entries

        Returns:
            int: Index to resume from (0 if not found)
        """
        if not self.last_processed:
            return 0

        # Find the index of the last processed entry
        for idx, entry in enumerate(ground_truth_data):
            if (entry.get('id') == self.last_processed.get('id') and
                entry.get('sub_id') == self.last_processed.get('sub_id') and
                entry.get('code_id') == self.last_processed.get('code_id') and
                entry.get('function_id') == self.last_processed.get('function_id')):
                return idx + 1  # Resume from the next entry

        return 0  # Start from the beginning if not found

    def is_file_completed(self, file_name=None):
        """
        Check if a file is marked as completed in the resume state.

        Args:
            file_name (str, optional): Name of the file to check.
                                      If None, uses the current file name.

        Returns:
            bool: True if the file is completed, False otherwise
        """
        file_to_check = file_name or self.current_file_name
        if not file_to_check:
            return False

        # If we're checking the current file and it's loaded in memory
        if file_to_check == self.current_file_name:
            return self.completed

        # Otherwise, load the resume point and check
        try:
            resume_data = load_resume_point(self.log_dir, file_to_check)
            if resume_data:
                return resume_data.get('completed', False)
            return False
        except Exception as e:
            logger.error(f"Error checking if file {file_to_check} is completed: {e}")
            return False



