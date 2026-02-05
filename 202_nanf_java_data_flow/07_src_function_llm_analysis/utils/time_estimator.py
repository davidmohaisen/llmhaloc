"""
Time estimation utilities for LLM vulnerability function localization.

This module provides classes for estimating the time required to process
entries with LLMs, tracking processing times, and providing estimates
for completion at both function and file levels.

"""

import time
import json
import os
from datetime import datetime, timedelta
from statistics import mean, median, stdev
from colorama import Fore

from .logger import Logger
from .resume_manager import ResumeState

# Initialize logger
logger = Logger()


class GlobalTimeEstimator:
    """
    A class for estimating processing times at the global (all files) level.

    This class tracks the time taken to process individual files and
    provides estimates for the time required to complete all files.
    """

    def __init__(self, total_files, log_dir):
        """
        Initialize the global time estimator.

        Args:
            total_files (int): Total number of files to process
            log_dir (str): Directory for log files
        """
        self.total_files = total_files
        self.log_dir = log_dir
        self.start_time = time.time()
        self.file_processing_times = []
        self.current_file_start_time = None
        self.current_file_index = 0
        self.completed_files = 0

        # Load previous processing times if available
        self._load_processing_times()

    def _get_times_file_path(self):
        """
        Get the path to the global processing times file.

        Returns:
            str: Path to the global processing times file
        """
        times_dir = os.path.join(self.log_dir, "processing_times")
        if not os.path.exists(times_dir):
            os.makedirs(times_dir)

        return os.path.join(times_dir, "global_times.json")

    def _load_processing_times(self):
        """
        Load global processing times from a previous run if available.
        """
        times_file = self._get_times_file_path()
        if os.path.exists(times_file) and os.path.getsize(times_file) > 0:
            try:
                with open(times_file, 'r') as file:
                    data = json.load(file)
                    self.file_processing_times = data.get('file_processing_times', [])
                    logger.info(f"Loaded {len(self.file_processing_times)} previous file processing times")
            except Exception as e:
                logger.warning(f"Error loading global processing times: {e}")

    def _save_processing_times(self):
        """
        Save global processing times to a file.
        """
        times_file = self._get_times_file_path()
        try:
            data = {
                'file_processing_times': self.file_processing_times,
                'last_updated': datetime.now().isoformat()
            }
            with open(times_file, 'w') as file:
                json.dump(data, file, indent=2)
        except Exception as e:
            logger.warning(f"Error saving global processing times: {e}")

    def start_file(self, file_index):
        """
        Mark the start time of processing a file.

        Args:
            file_index (int): Index of the file being processed (0-based)
        """
        self.current_file_start_time = time.time()
        self.current_file_index = file_index

    def end_file(self, success=True):
        """
        Mark the end time of processing a file and update estimates.

        Args:
            success (bool, optional): Whether the file was processed successfully

        Returns:
            dict: Dictionary with time statistics and estimates
        """
        if self.current_file_start_time is None:
            logger.warning("end_file() called without start_file()")
            return {}

        # Calculate processing time for this file
        processing_time = time.time() - self.current_file_start_time

        if success:
            self.file_processing_times.append(processing_time)
            self.completed_files += 1

        # Save processing times
        self._save_processing_times()

        # Get time estimates
        return self.get_estimates()

    def get_estimates(self):
        """
        Calculate time estimates based on file processing times.

        Returns:
            dict: Dictionary with time statistics and estimates
        """
        if not self.file_processing_times:
            return self._get_empty_estimates()

        # Calculate average time per file
        avg_time = mean(self.file_processing_times)

        # Calculate weighted average giving more weight to recent times
        if len(self.file_processing_times) > 3:
            # Use the most recent 3 times with higher weights
            recent_times = self.file_processing_times[-3:]
            weights = [0.2, 0.3, 0.5]  # Increasing weights for more recent times
            weighted_avg_time = sum(t * w for t, w in zip(recent_times, weights))
        else:
            weighted_avg_time = avg_time

        # Calculate time estimates
        elapsed_time = time.time() - self.start_time
        remaining_files = self.total_files - self.completed_files
        estimated_remaining_time = weighted_avg_time * remaining_files
        estimated_total_time = elapsed_time + estimated_remaining_time
        completion_time = datetime.now() + timedelta(seconds=estimated_remaining_time)

        # Calculate files per hour
        if elapsed_time > 0:
            files_per_hour = (self.completed_files / elapsed_time) * 3600
        else:
            files_per_hour = 0

        return {
            'avg_time_per_file': avg_time,
            'weighted_avg_time': weighted_avg_time,
            'elapsed_time': elapsed_time,
            'estimated_remaining_time': estimated_remaining_time,
            'estimated_total_time': estimated_total_time,
            'estimated_completion_time': completion_time.isoformat(),
            'progress_percentage': (self.completed_files / self.total_files) * 100 if self.total_files > 0 else 0,
            'files_completed': self.completed_files,
            'files_total': self.total_files,
            'files_remaining': remaining_files,
            'files_per_hour': files_per_hour
        }

    def _get_empty_estimates(self):
        """
        Get empty time estimates when no processing times are available.

        Returns:
            dict: Dictionary with empty time statistics and estimates
        """
        return {
            'avg_time_per_file': 0,
            'weighted_avg_time': 0,
            'elapsed_time': 0,
            'estimated_remaining_time': 0,
            'estimated_total_time': 0,
            'estimated_completion_time': None,
            'progress_percentage': (self.completed_files / self.total_files) * 100 if self.total_files > 0 else 0,
            'files_completed': self.completed_files,
            'files_total': self.total_files,
            'files_remaining': self.total_files - self.completed_files,
            'files_per_hour': 0
        }


class TimeEstimator:
    """
    A class for estimating processing times for LLM operations.

    This class tracks the time taken to process individual entries and
    provides estimates for the time required to complete the remaining
    entries in a dataset.
    """

    def __init__(self, file_name, total_entries, log_dir, resume_index=0):
        """
        Initialize the time estimator.

        Args:
            file_name (str): Name of the file being processed
            total_entries (int): Total number of entries to process
            log_dir (str): Directory for log files
            resume_index (int, optional): Index to resume from. Defaults to 0.
        """
        self.file_name = file_name
        self.total_entries = total_entries
        self.log_dir = log_dir
        self.current_index = resume_index
        self.remaining_entries = total_entries - resume_index

        # Time tracking
        self.start_time = time.time()
        self.processing_times = []
        self.last_entry_start_time = None
        self.current_entry = None
        self.failed_entries = []

        # Load previous processing times if available
        self.load_processing_times()

        # Log initial estimate
        self._log_initial_estimate()

    def load_processing_times(self):
        """
        Load processing times from a previous run if available.
        """
        times_file = self._get_times_file_path()
        if os.path.exists(times_file) and os.path.getsize(times_file) > 0:
            try:
                with open(times_file, 'r') as file:
                    data = json.load(file)
                    self.processing_times = data.get('processing_times', [])
                    logger.info(f"Loaded {len(self.processing_times)} previous processing times for {self.file_name}")
            except Exception as e:
                logger.warning(f"Error loading processing times for {self.file_name}: {e}")

    def _get_times_file_path(self):
        """
        Get the path to the processing times file.

        Returns:
            str: Path to the processing times file
        """
        times_dir = os.path.join(self.log_dir, "processing_times")
        if not os.path.exists(times_dir):
            os.makedirs(times_dir)

        # Remove .json extension if present
        base_name = self.file_name.replace('.json', '')
        filename = f"{base_name}_times.json"
        return os.path.join(times_dir, filename)

    def start_entry(self, entry=None):
        """
        Mark the start time of processing an entry.

        Args:
            entry (dict, optional): The entry being processed
        """
        self.last_entry_start_time = time.time()
        self.current_entry = entry

    def end_entry(self, success=True):
        """
        Mark the end time of processing an entry and update estimates.

        Args:
            success (bool, optional): Whether the entry was processed successfully

        Returns:
            dict: Dictionary with time statistics and estimates
        """
        if self.last_entry_start_time is None:
            logger.warning("end_entry() called without start_entry()")
            return {}

        # Calculate processing time for this entry
        processing_time = time.time() - self.last_entry_start_time
        self.processing_times.append(processing_time)
        self.current_index += 1
        self.remaining_entries -= 1

        # Track failed entries
        if not success and self.current_entry:
            entry_id = (
                self.current_entry.get('id', 'Unknown'),
                self.current_entry.get('sub_id', 'Unknown'),
                self.current_entry.get('code_id', 'Unknown'),
                self.current_entry.get('function_id', 'Unknown')
            )
            self.failed_entries.append(entry_id)

        # Save processing times
        self._save_processing_times()

        # Get time estimates
        estimates = self.get_estimates()

        # Update resume state if we have a current entry
        if self.current_entry:
            completed = self.current_index >= self.total_entries
            resume_state = ResumeState(self.log_dir)
            resume_state.load_state(self.file_name)  # Try to load existing state

            # Add any failed entries
            for entry_id in self.failed_entries:
                if hasattr(entry_id, '__iter__'):  # Check if it's an iterable (tuple)
                    failed_entry = {
                        'id': entry_id[0] if len(entry_id) > 0 else None,
                        'sub_id': entry_id[1] if len(entry_id) > 1 else None,
                        'code_id': entry_id[2] if len(entry_id) > 2 else None,
                        'function_id': entry_id[3] if len(entry_id) > 3 else None
                    }
                    resume_state.add_failed_entry(failed_entry)

            # Save the updated state
            resume_state.save_state(
                self.file_name,
                self.current_entry,
                self.current_index,
                self.total_entries,
                estimates,
                completed
            )

        return estimates

    def _save_processing_times(self):
        """
        Save processing times to a file.
        """
        times_file = self._get_times_file_path()
        try:
            data = {
                'file_name': self.file_name,
                'processing_times': self.processing_times,
                'last_updated': datetime.now().isoformat()
            }
            with open(times_file, 'w') as file:
                json.dump(data, file, indent=2)
        except Exception as e:
            logger.warning(f"Error saving processing times for {self.file_name}: {e}")

    def _get_empty_estimates(self):
        """
        Get empty time estimates when no processing times are available.

        Returns:
            dict: Dictionary with empty time statistics and estimates
        """
        return {
            'avg_time_per_entry': 0,
            'median_time_per_entry': 0,
            'weighted_avg_time': 0,
            'std_dev': 0,
            'elapsed_time': 0,
            'estimated_remaining_time': 0,
            'estimated_total_time': 0,
            'estimated_completion_time': None,
            'progress_percentage': self._calculate_progress_percentage(),
            'entries_completed': self.current_index,
            'entries_total': self.total_entries,
            'entries_remaining': self.remaining_entries,
            'entries_per_minute': 0
        }

    def _calculate_time_statistics(self):
        """
        Calculate basic time statistics from processing times.

        Returns:
            tuple: (avg_time, median_time, weighted_avg_time, std_dev)
        """
        avg_time = mean(self.processing_times)
        median_time = median(self.processing_times)

        # Calculate weighted average giving more weight to recent times
        if len(self.processing_times) > 5:
            # Use the most recent 5 times with higher weights
            recent_times = self.processing_times[-5:]
            weights = [0.1, 0.15, 0.2, 0.25, 0.3]  # Increasing weights for more recent times
            weighted_avg_time = sum(t * w for t, w in zip(recent_times, weights))
        else:
            weighted_avg_time = avg_time

        std_dev = stdev(self.processing_times) if len(self.processing_times) > 1 else 0
        return avg_time, median_time, weighted_avg_time, std_dev

    def _calculate_time_estimates(self, weighted_avg_time):
        """
        Calculate time estimates based on weighted average processing time.

        Args:
            weighted_avg_time (float): Weighted average time per entry

        Returns:
            tuple: (elapsed_time, estimated_remaining_time, estimated_total_time, completion_time, entries_per_minute)
        """
        elapsed_time = time.time() - self.start_time
        estimated_remaining_time = weighted_avg_time * self.remaining_entries
        estimated_total_time = elapsed_time + estimated_remaining_time
        completion_time = datetime.now() + timedelta(seconds=estimated_remaining_time)

        # Calculate entries per minute
        if elapsed_time > 0:
            entries_per_minute = (self.current_index / elapsed_time) * 60
        else:
            entries_per_minute = 0

        return elapsed_time, estimated_remaining_time, estimated_total_time, completion_time, entries_per_minute

    def get_estimates(self):
        """
        Calculate time estimates based on processing times.

        Returns:
            dict: Dictionary with time statistics and estimates
        """
        if not self.processing_times:
            return self._get_empty_estimates()

        # Calculate statistics
        avg_time, median_time, weighted_avg_time, std_dev = self._calculate_time_statistics()

        # Calculate time estimates
        elapsed_time, estimated_remaining_time, estimated_total_time, completion_time, entries_per_minute = self._calculate_time_estimates(weighted_avg_time)

        return {
            'avg_time_per_entry': avg_time,
            'median_time_per_entry': median_time,
            'weighted_avg_time': weighted_avg_time,
            'std_dev': std_dev,
            'elapsed_time': elapsed_time,
            'estimated_remaining_time': estimated_remaining_time,
            'estimated_total_time': estimated_total_time,
            'estimated_completion_time': completion_time.isoformat(),
            'progress_percentage': self._calculate_progress_percentage(),
            'entries_completed': self.current_index,
            'entries_total': self.total_entries,
            'entries_remaining': self.remaining_entries,
            'entries_per_minute': entries_per_minute
        }

    def _calculate_progress_percentage(self):
        """
        Calculate the current progress percentage.

        Returns:
            float: Progress percentage (0-100)
        """
        return round((self.current_index / self.total_entries) * 100, 2)

    def _extract_estimate_values(self, estimates):
        """
        Extract key values from time estimates.

        Args:
            estimates (dict): Time estimates dictionary

        Returns:
            tuple: (avg_time, remaining_time, completion_time, entries_per_minute)
        """
        avg_time = estimates['avg_time_per_entry']
        remaining_time = estimates['estimated_remaining_time']
        completion_time = estimates['estimated_completion_time']
        entries_per_minute = estimates.get('entries_per_minute', 0)
        return avg_time, remaining_time, completion_time, entries_per_minute

    def _log_estimate_details(self, avg_time, remaining_time, completion_time, entries_per_minute):
        """
        Log detailed time estimate information.

        Args:
            avg_time (float): Average time per entry
            remaining_time (float): Estimated remaining time
            completion_time (str): Estimated completion time
            entries_per_minute (float): Entries processed per minute
        """
        logger.info(f"Based on {len(self.processing_times)} previous entries:")
        logger.info(f"Average processing time: {avg_time:.2f} seconds per entry")
        logger.info(f"Processing rate: {entries_per_minute:.2f} entries per minute")
        logger.info(f"Estimated time to complete {self.remaining_entries} remaining entries: "
                   f"{self._format_time_duration(remaining_time)}")
        logger.info(f"Estimated completion time: {self._format_datetime(completion_time)}")

    def _log_initial_estimate(self):
        """
        Log initial time estimate based on available data.
        """
        if not self.processing_times:
            logger.info(f"No previous processing times available for {self.file_name}")
            return

        # Get time estimates
        estimates = self.get_estimates()

        # Extract key values
        avg_time, remaining_time, completion_time, entries_per_minute = self._extract_estimate_values(estimates)

        # Log detailed information
        self._log_estimate_details(avg_time, remaining_time, completion_time, entries_per_minute)

    @staticmethod
    def _format_time_duration(seconds):
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

    @staticmethod
    def _format_datetime(iso_datetime):
        """
        Format an ISO datetime string to a human-readable string.

        Args:
            iso_datetime (str): ISO format datetime string

        Returns:
            str: Formatted datetime string
        """
        if not iso_datetime:
            return "Unknown"

        try:
            dt = datetime.fromisoformat(iso_datetime)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return iso_datetime
