"""
Time estimation utilities for LLM vulnerability function localization.

This module provides a class for estimating the time required to process
entries with LLMs, tracking processing times, and providing estimates
for completion.

"""

import time
import json
import os
from datetime import datetime, timedelta
from statistics import mean, median, stdev
from colorama import Fore

from .logger import Logger

# Initialize logger
logger = Logger()


class TimeEstimator:
    """
    A class for estimating processing times for LLM operations.
    
    This class tracks the time taken to process individual entries and
    provides estimates for the time required to complete the remaining
    entries in a dataset.
    """
    
    def __init__(self, model_name, total_entries, log_dir, resume_index=0):
        """
        Initialize the time estimator.
        
        Args:
            model_name (str): Name of the model being processed
            total_entries (int): Total number of entries to process
            log_dir (str): Directory for log files
            resume_index (int, optional): Index to resume from. Defaults to 0.
        """
        self.model_name = model_name
        self.total_entries = total_entries
        self.log_dir = log_dir
        self.current_index = resume_index
        self.remaining_entries = total_entries - resume_index
        
        # Time tracking
        self.start_time = time.time()
        self.processing_times = []
        self.last_entry_start_time = None
        
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
                    logger.info(f"Loaded {len(self.processing_times)} previous processing times for {self.model_name}")
            except Exception as e:
                logger.warning(f"Error loading processing times for {self.model_name}: {e}")
    
    def _get_times_file_path(self):
        """
        Get the path to the processing times file.
        
        Returns:
            str: Path to the processing times file
        """
        times_dir = os.path.join(self.log_dir, "processing_times")
        if not os.path.exists(times_dir):
            os.makedirs(times_dir)
        
        from .llm_processor import sanitize_model_name
        filename = f"{sanitize_model_name(self.model_name)}_times.json"
        return os.path.join(times_dir, filename)
    
    def start_entry(self):
        """
        Mark the start time of processing an entry.
        """
        self.last_entry_start_time = time.time()
    
    def end_entry(self):
        """
        Mark the end time of processing an entry and update estimates.
        
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
        
        # Save processing times
        self._save_processing_times()
        
        # Return time statistics and estimates
        return self.get_estimates()
    
    def _save_processing_times(self):
        """
        Save processing times to a file.
        """
        times_file = self._get_times_file_path()
        try:
            data = {
                'model_name': self.model_name,
                'processing_times': self.processing_times,
                'last_updated': datetime.now().isoformat()
            }
            with open(times_file, 'w') as file:
                json.dump(data, file, indent=2)
        except Exception as e:
            logger.warning(f"Error saving processing times for {self.model_name}: {e}")
    
    def get_estimates(self):
        """
        Calculate time estimates based on processing times.
        
        Returns:
            dict: Dictionary with time statistics and estimates
        """
        if not self.processing_times:
            return {
                'avg_time_per_entry': 0,
                'median_time_per_entry': 0,
                'std_dev': 0,
                'elapsed_time': 0,
                'estimated_remaining_time': 0,
                'estimated_total_time': 0,
                'estimated_completion_time': None,
                'progress_percentage': self._calculate_progress_percentage()
            }
        
        # Calculate statistics
        avg_time = mean(self.processing_times)
        median_time = median(self.processing_times)
        std_dev = stdev(self.processing_times) if len(self.processing_times) > 1 else 0
        
        # Calculate elapsed and estimated times
        elapsed_time = time.time() - self.start_time
        estimated_remaining_time = avg_time * self.remaining_entries
        estimated_total_time = elapsed_time + estimated_remaining_time
        
        # Calculate estimated completion time
        completion_time = datetime.now() + timedelta(seconds=estimated_remaining_time)
        
        return {
            'avg_time_per_entry': avg_time,
            'median_time_per_entry': median_time,
            'std_dev': std_dev,
            'elapsed_time': elapsed_time,
            'estimated_remaining_time': estimated_remaining_time,
            'estimated_total_time': estimated_total_time,
            'estimated_completion_time': completion_time.isoformat(),
            'progress_percentage': self._calculate_progress_percentage()
        }
    
    def _calculate_progress_percentage(self):
        """
        Calculate the current progress percentage.
        
        Returns:
            float: Progress percentage (0-100)
        """
        return round((self.current_index / self.total_entries) * 100, 2)
    
    def _log_initial_estimate(self):
        """
        Log initial time estimate based on available data.
        """
        if not self.processing_times:
            logger.info(f"No previous processing times available for {self.model_name}")
            return
        
        estimates = self.get_estimates()
        avg_time = estimates['avg_time_per_entry']
        remaining_time = estimates['estimated_remaining_time']
        completion_time = estimates['estimated_completion_time']
        
        logger.info(f"Based on {len(self.processing_times)} previous entries:")
        logger.info(f"Average processing time: {avg_time:.2f} seconds per entry")
        logger.info(f"Estimated time to complete {self.remaining_entries} remaining entries: "
                   f"{self._format_time_duration(remaining_time)}")
        logger.info(f"Estimated completion time: {self._format_datetime(completion_time)}")
    
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
