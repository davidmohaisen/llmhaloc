#!/usr/bin/env python3
"""
LLMVUL: LLM Vulnerability Function Localization
Main driver script for processing code samples with LLMs

This script processes code samples with various LLMs to identify vulnerable functions.
It uses YAML configuration files to define machine-specific settings and model lists.


Usage:
    python main.py [--machine MACHINE_NAME] [--verbose]

Arguments:
    --machine MACHINE_NAME    Specify which machine configuration to use (mac, studio)
                             If not provided, will attempt to detect from hostname
    --verbose                Enable verbose mode to display detailed information about
                             system prompts and user prompts being fed into the LLM
"""

import os
import sys
import json
import argparse
from datetime import datetime
from colorama import Fore

# Import utility modules
from utils.config_loader import load_config
from utils.logger import Logger
from utils.data_handler import (
    load_json_data, stream_json_data, ensure_directories, is_model_completed,
    find_resume_point, write_to_json, save_resume_point, add_failed_entry,
    clear_failed_entries, reset_resume_point, get_failed_entries,
    update_incomplete_models_summary
)
from utils.llm_processor import (
    extract_fields, generate_prompt, interact_with_llm, sanitize_model_name
)
from utils.time_estimator import TimeEstimator
from utils.global_time_tracker import GlobalTimeTracker


class LLMVulProcessor:
    """
    Main processor class for LLM vulnerability function localization.

    This class orchestrates the entire process of loading configuration,
    setting up logging, loading data, and processing models.
    """

    def __init__(self, machine_name=None, verbose=False):
        """
        Initialize the processor with the specified machine configuration.

        Args:
            machine_name (str, optional): Name of the machine configuration to use.
                                         If None, will attempt to detect from hostname.
            verbose (bool, optional): Whether to enable verbose mode for detailed logging.
                                     Defaults to False.
        """
        # Load configuration
        self.config = load_config(machine_name)

        # Store verbose flag
        self.verbose = verbose
        self.config['verbose'] = verbose

        # No setup needed here, logger will handle it

        # Ensure log directory exists
        log_dir = self.config['output']['log_dir']
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            print(f"Created logs directory: {log_dir}")

        # Initialize logger
        self.logger = Logger(self.config)

        # Ensure other directories exist
        ensure_directories(self.config)

        # Initialize data
        self.data = None
        self.models = self.config['models']
        self.result_dir = self.config['output']['result_dir']

        # Initialize global time tracker
        self.global_time_tracker = None

        if verbose:
            self.logger.info("Verbose mode enabled - detailed prompt information will be displayed")

    def load_data(self):
        """
        Load the dataset from the configured location.

        Note: This method still loads the entire dataset into memory for backward compatibility.
        For streaming processing, use process_model_streaming instead of process_model.
        """
        dataset_path = os.path.join(
            self.config['data']['base_dir'],
            self.config['data']['dataset_file']
        )
        self.logger.info(f"Loading dataset from {dataset_path}")
        self.data = load_json_data(dataset_path)
        self.logger.info(f"Loaded {len(self.data)} entries from dataset")

    def get_dataset_path(self):
        """Get the path to the dataset file."""
        return os.path.join(
            self.config['data']['base_dir'],
            self.config['data']['dataset_file']
        )

    # process_model method removed as it's not used - we use process_model_streaming instead
    def _get_model_time_estimate(self, model_name):
        """
        Get time estimate for a single model based on previous runs.

        Args:
            model_name (str): Name of the model

        Returns:
            tuple: (model_estimate, avg_time, has_data, weighted_avg_time)
        """
        from utils.llm_processor import sanitize_model_name

        total_entries = len(self.data)
        log_dir = self.config['output']['log_dir']

        # Check if we have timing data for this model
        times_dir = os.path.join(log_dir, "processing_times")
        if not os.path.exists(times_dir):
            return 0, 0, False, 0

        times_file = os.path.join(times_dir, f"{sanitize_model_name(model_name)}_times.json")
        if not os.path.exists(times_file) or os.path.getsize(times_file) == 0:
            return 0, 0, False, 0

        try:
            with open(times_file, 'r') as file:
                data = json.load(file)
                times = data.get('processing_times', [])
                if not times:
                    return 0, 0, False, 0

                # Calculate average time
                avg_time = sum(times) / len(times)

                # Calculate weighted average (recent entries have more weight)
                weighted_avg = 0
                if len(times) > 0:
                    # Get the most recent entries (up to 10)
                    recent_times = times[-min(10, len(times)):]
                    # Assign weights (more recent entries have higher weights)
                    weights = [i+1 for i in range(len(recent_times))]
                    total_weight = sum(weights)
                    # Calculate weighted average
                    weighted_sum = sum(t * w for t, w in zip(recent_times, weights))
                    weighted_avg = weighted_sum / total_weight if total_weight > 0 else 0

                # Use weighted average if available, otherwise use regular average
                time_per_entry = weighted_avg if weighted_avg > 0 else avg_time

                # If model is not completed, estimate remaining time
                completed, _ = is_model_completed(model_name, self.data, self.result_dir, log_dir)
                if not completed:
                    start_idx = find_resume_point(model_name, self.data, self.result_dir, log_dir)
                    remaining = total_entries - start_idx
                    model_estimate = time_per_entry * remaining
                else:
                    # For completed models, return the actual total processing time
                    model_estimate = sum(times)  # Use the sum of all processing times

                return model_estimate, avg_time, True, weighted_avg
        except Exception as e:
            self.logger.warning(f"Error reading timing data for {model_name}: {e}")
            return 0, 0, False, 0

    def _estimate_initial_processing_time(self):
        """
        Estimate the total processing time based on previous runs.

        Returns:
            dict: Time estimates including total time, completion time, and model-specific estimates
        """
        # Try to estimate total time based on previous runs
        total_time_estimate = 0
        models_with_data = 0

        # Track models that still need processing
        remaining_models = {}

        # First pass: collect data about models
        total_time_estimate, models_with_data = self._collect_model_time_estimates(
            remaining_models, total_time_estimate, models_with_data)

        # If we have timing data for at least one model, estimate total time
        time_estimates = {
            'estimated_total_time': 0,
            'estimated_completion_time': None,
            'models_with_data': models_with_data,
            'model_estimates': remaining_models
        }

        # Second pass: calculate total time estimate
        if models_with_data > 0:
            self._calculate_total_time_estimate(
                time_estimates, total_time_estimate, models_with_data, remaining_models)
        else:
            self.logger.info("No previous timing data available for estimation")

        return time_estimates

    def _collect_model_time_estimates(self, remaining_models, total_time_estimate, models_with_data):
        """
        Collect time estimates for each model.

        Args:
            remaining_models (dict): Dictionary to store model estimates
            total_time_estimate (float): Running total of time estimates
            models_with_data (int): Count of models with timing data

        Returns:
            tuple: (total_time_estimate, models_with_data)
        """
        log_dir = self.config['output']['log_dir']

        for model_name in self.models.keys():
            # Check if model is already completed
            completed, _ = is_model_completed(model_name, self.data, self.result_dir, log_dir)
            if completed:
                # Get time estimate for this model (will return actual processing time for completed models)
                model_estimate, avg_time, has_data, weighted_avg = self._get_model_time_estimate(model_name)

                if has_data:
                    self.logger.info(f"Model {model_name}: Already completed - Total processing time: {self.logger._format_time_duration(model_estimate)}")
                else:
                    self.logger.info(f"Model {model_name}: Already completed")
                continue

            # Get time estimate for this model
            model_estimate, avg_time, has_data, weighted_avg = self._get_model_time_estimate(model_name)

            if has_data:
                # Add to total estimate
                total_time_estimate += model_estimate
                models_with_data += 1

                # Store model-specific estimate
                remaining_models[model_name] = model_estimate

                # Log model-specific information
                time_info = f"Average {avg_time:.2f}s per entry"
                if weighted_avg > 0:
                    time_info += f", Weighted {weighted_avg:.2f}s"
                self.logger.info(f"Model {model_name}: {time_info}")

        return total_time_estimate, models_with_data

    def _calculate_total_time_estimate(self, time_estimates, total_time_estimate, models_with_data, remaining_models):
        """
        Calculate the total time estimate based on collected model data.

        Args:
            time_estimates (dict): Dictionary to store time estimates
            total_time_estimate (float): Running total of time estimates
            models_with_data (int): Count of models with timing data
            remaining_models (dict): Dictionary of model estimates
        """
        from datetime import datetime, timedelta

        # For models without timing data, use the average of models with data
        if models_with_data < len(remaining_models):
            avg_model_time = total_time_estimate / models_with_data

            # Add estimates for models without data
            for model_name in remaining_models:
                if model_name not in remaining_models:
                    remaining_models[model_name] = avg_model_time
                    total_time_estimate += avg_model_time

        # Format and display the estimate
        time_str = self.logger._format_time_duration(total_time_estimate)
        completion_time = datetime.now() + timedelta(seconds=total_time_estimate)
        completion_str = completion_time.strftime("%Y-%m-%d %H:%M:%S")

        self.logger.info(f"Estimated total processing time: {time_str}")
        self.logger.info(f"Estimated completion time: {completion_str}")

        # Store in time estimates
        time_estimates['estimated_total_time'] = total_time_estimate
        time_estimates['estimated_completion_time'] = completion_time.isoformat()
        time_estimates['estimated_remaining_time'] = total_time_estimate

    def _format_datetime(self, iso_datetime):
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
            from datetime import datetime
            dt = datetime.fromisoformat(iso_datetime)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return iso_datetime

    def _estimate_remaining_time(self, current_model_idx, total_models, process_start_time, completed_models):
        """
        Estimate remaining time for all models based on current progress.

        Args:
            current_model_idx (int): Current model index (1-based)
            total_models (int): Total number of models
            process_start_time (float): Start time of the entire process
            completed_models (int): Number of models completed

        Returns:
            dict: Time estimates including remaining time and completion time
        """
        import time
        from datetime import datetime, timedelta

        # Calculate elapsed time
        process_elapsed = time.time() - process_start_time

        # Initialize time estimates
        time_estimates = {
            'elapsed_time': process_elapsed,
            'estimated_remaining_time': 0,
            'estimated_completion_time': None,
            'model_estimates': {}
        }

        # If we're just starting, use initial estimates
        if current_model_idx <= 1:
            return self._estimate_initial_processing_time()

        # If we've completed at least one model, use that to estimate remaining time
        if completed_models > 0 and current_model_idx > 1:
            # Calculate average time per model based on completed models
            avg_time_per_model = process_elapsed / completed_models

            # Get remaining models
            remaining_models = total_models - current_model_idx + 1

            # Estimate remaining time
            estimated_remaining = avg_time_per_model * remaining_models

            # Calculate completion time
            completion_time = datetime.now() + timedelta(seconds=estimated_remaining)

            # Store in time estimates
            time_estimates['estimated_remaining_time'] = estimated_remaining
            time_estimates['estimated_completion_time'] = completion_time.isoformat()

            # Get model-specific estimates for remaining models
            model_estimates = {}
            remaining_model_names = list(self.models.keys())[current_model_idx-1:]

            for model_name in remaining_model_names:
                # Check if model is already completed (we don't need the result since we get the time either way)
                _, _ = is_model_completed(model_name, self.data, self.result_dir, self.config['output']['log_dir'])

                # Get time estimate for this model (will return actual processing time for completed models)
                model_estimate, _, has_data, _ = self._get_model_time_estimate(model_name)

                # If we have data for this model, use it
                if has_data:
                    model_estimates[model_name] = model_estimate
                else:
                    # Otherwise use the average time per model
                    model_estimates[model_name] = avg_time_per_model

            # Store model estimates
            time_estimates['model_estimates'] = model_estimates

        return time_estimates

    def _log_overall_progress(self, i, total_models, process_start_time, completed_models):
        """
        Log the overall progress and time estimates.

        Args:
            i (int): Current model index (1-based)
            total_models (int): Total number of models
            process_start_time (float): Start time of the entire process
            completed_models (int): Number of models completed

        Returns:
            dict: Time estimates for use in subsequent calls
        """
        # Get time estimates
        time_estimates = self._estimate_remaining_time(i, total_models, process_start_time, completed_models)

        # Log global progress using the enhanced logger method
        self.logger.global_progress(i, total_models, completed_models, process_start_time, time_estimates)

        return time_estimates

    def _check_model_completion(self, model_name, total_entries):
        """
        Check if a model has already completed processing.

        Args:
            model_name (str): Name of the model to check
            total_entries (int): Total number of entries in the dataset

        Returns:
            bool: True if model has completed processing, False otherwise
        """
        log_dir = self.config['output']['log_dir']
        completed, status_info = is_model_completed(model_name, self.data, self.result_dir, log_dir)

        if completed:
            if status_info["max_retries_reached"] > 0:
                self.logger.warning(
                    f"Skipping {model_name} - completed with {status_info['max_retries_reached']} "
                    f"entries that failed after maximum retries"
                )
            else:
                self.logger.success(f"Skipping {model_name} - already completed all {total_entries} entries")
            return True
        return False

    def _process_entry_attempt(self, model_name, entry, idx, total_entries, time_estimator, log_dir, retry_count, max_retries, error_file):
        """
        Process a single entry attempt.

        Args:
            model_name (str): Name of the model to use
            entry (dict): The entry to process
            idx (int): Index of the entry
            total_entries (int): Total number of entries
            time_estimator (TimeEstimator): Time estimator instance
            log_dir (str): Log directory path
            retry_count (int): Current retry count
            max_retries (int): Maximum number of retry attempts
            error_file (str): Path to the error file

        Returns:
            tuple: (success, entry_id, sub_id, code_id) - Success status and entry identifiers
        """
        # Extract entry information
        entry_id = entry.get('id', 'Unknown')
        sub_id = entry.get('sub_id', 'Unknown')
        code_id = entry.get('code_id', 'Unknown')

        # Start timing this entry
        time_estimator.start_entry()

        # Display clear entry start message
        self.logger.separator("-", 60)
        if retry_count > 0:
            self.logger.info(f"{Fore.CYAN}▶ RETRYING: {model_name} - Entry {idx+1}/{total_entries} (Attempt {retry_count+1}/{max_retries})")
        else:
            self.logger.info(f"{Fore.CYAN}▶ PROCESSING: {model_name} - Entry {idx+1}/{total_entries}")
        self.logger.info(f"{Fore.CYAN}  ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}")

        # Extract fields and process the entry
        code, filename, entry_id, sub_id, code_id, cross_script_info = extract_fields(entry)

        # Generate prompt and interact with LLM
        custom_prompt = generate_prompt(code, filename, cross_script_info)
        new_entry = interact_with_llm(entry, custom_prompt, model_name, self.config)
        write_to_json(new_entry, model_name, self.result_dir)

        # End timing and get estimates
        time_estimates = time_estimator.end_entry()

        # Save resume point with time estimates
        save_resume_point(model_name, entry, idx+1, total_entries, log_dir, time_estimates)

        # If this was a retry and succeeded, delete the error file
        if os.path.exists(error_file):
            try:
                os.remove(error_file)
                self.logger.info(f"Deleted error file after successful retry: {error_file}")
            except Exception as del_e:
                self.logger.warning(f"Could not delete error file: {del_e}")

        # Detailed progress and time logging
        self.logger.separator("-", 60)
        if retry_count > 0:
            self.logger.success(f"✓ RETRY SUCCEEDED: {model_name} - Entry {idx+1}/{total_entries}")
        else:
            self.logger.success(f"✓ COMPLETED: {model_name} - Entry {idx+1}/{total_entries}")
        self.logger.progress(
            idx+1, total_entries,
            f"- ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}"
        )
        self.logger.time_estimate(idx+1, total_entries, time_estimates)

        return True, entry_id, sub_id, code_id

    def _handle_entry_error(self, model_name, entry, idx, total_entries, log_dir, error_file, error_msg, retry_count, max_retries):
        """
        Handle an error that occurred during entry processing.
        If max retries is reached, creates an entry with empty response.

        Args:
            model_name (str): Name of the model
            entry (dict): The entry being processed
            idx (int): Index of the entry
            total_entries (int): Total number of entries
            log_dir (str): Log directory path
            error_file (str): Path to the error file
            error_msg (str): Error message
            retry_count (int): Current retry count
            max_retries (int): Maximum number of retry attempts

        Returns:
            bool: Always returns True to continue processing
        """
        entry_id = entry.get('id', 'Unknown')
        sub_id = entry.get('sub_id', 'Unknown')
        code_id = entry.get('code_id', 'Unknown')

        self.logger.separator("-", 60)
        self.logger.error(
            f"✗ FAILED: {model_name} - Index: {idx+1}/{total_entries} "
            f"- ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}: {error_msg}"
        )

        # Create or update the error file
        error_data = {
            'model_name': model_name,
            'entry_id': entry_id,
            'sub_id': sub_id,
            'code_id': code_id,
            'error': error_msg,
            'retry_count': retry_count,
            'timestamp': datetime.now().isoformat()
        }

        try:
            with open(error_file, 'w') as f:
                json.dump(error_data, f, indent=2)

            self.logger.warning(
                f"Created error file for {model_name} - ID: {entry_id}, "
                f"Sub_ID: {sub_id}, Code_ID: {code_id} "
                f"(Retry {retry_count}/{max_retries})"
            )
        except Exception as write_e:
            self.logger.error(f"Error creating error file: {write_e}")

        # Also add to failed entries for backward compatibility
        add_failed_entry(model_name, entry, log_dir, error_msg)

        # If we've reached the maximum retries, create an empty response entry
        if retry_count >= max_retries:
            self.logger.warning(
                f"Maximum retries ({max_retries}) reached for {model_name} - "
                f"ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}. "
                f"Creating entry with empty response."
            )

            # Create a new entry with empty response
            new_entry = {
                'id': entry_id,
                'sub_id': sub_id,
                'code_id': code_id,
                'response': "",  # Empty response when max retries reached
                'total_duration': 0,
                'load_duration': 0,
                'prompt_eval_count': 0,
                'prompt_eval_duration': 0,
                'eval_count': 0,
                'eval_duration': 0
            }

            # Write the empty response to the result file
            write_to_json(new_entry, model_name, self.result_dir)

            # Return True to continue processing the next entry
            return True

        # Otherwise, we'll retry immediately in the next iteration of the while loop
        self.logger.warning(
            f"Retrying immediately: {model_name} - Entry {idx+1}/{total_entries} "
            f"(Attempt {retry_count+1}/{max_retries})"
        )
        return True

    def _process_entry(self, model_name, entry, idx, total_entries, time_estimator, log_dir, max_retries):
        """
        Process a single entry with retry mechanism.
        If max retries is reached, creates an entry with empty response.

        Args:
            model_name (str): Name of the model to use
            entry (dict): The entry to process
            idx (int): Index of the entry
            total_entries (int): Total number of entries
            time_estimator (TimeEstimator): Time estimator instance
            log_dir (str): Log directory path
            max_retries (int): Maximum number of retry attempts

        Returns:
            bool: True if processing succeeded (including with empty response)
        """
        # Extract entry information
        entry_id = entry.get('id', 'Unknown')
        sub_id = entry.get('sub_id', 'Unknown')
        code_id = entry.get('code_id', 'Unknown')

        # Create a unique error file path for this entry
        error_dir = os.path.join(log_dir, "errors", sanitize_model_name(model_name))
        os.makedirs(error_dir, exist_ok=True)
        error_file = os.path.join(error_dir, f"{entry_id}_{sub_id}_{code_id}.error")

        # Process this entry with immediate retries
        retry_count = 0
        success = False

        while retry_count <= max_retries and not success:
            try:
                success, entry_id, sub_id, code_id = self._process_entry_attempt(
                    model_name, entry, idx, total_entries, time_estimator,
                    log_dir, retry_count, max_retries, error_file
                )
            except Exception as e:
                error_msg = str(e)
                retry_count += 1

                # Handle the error - this will now always return True since we handle max retries
                # by creating an empty response entry
                self._handle_entry_error(
                    model_name, entry, idx, total_entries, log_dir,
                    error_file, error_msg, retry_count, max_retries
                )

                # If we've reached max retries, consider this entry as "successful" with empty response
                if retry_count >= max_retries:
                    success = True

        return success

    def _report_completion_status(self, model_name, log_dir):
        """
        Report the completion status of a model.

        Args:
            model_name (str): Name of the model
            log_dir (str): Log directory path

        Returns:
            bool: True if model completed successfully, False otherwise
        """
        # Check if we've completed all entries
        completed, status_info = is_model_completed(model_name, self.data, self.result_dir, log_dir)

        # Get failed entries for detailed reporting
        failed_entries = get_failed_entries(model_name, log_dir)
        failed_count = len(failed_entries)
        max_retries_reached = status_info["max_retries_reached"]
        retryable_entries = status_info["retryable_entries"]

        if completed:
            if max_retries_reached > 0:
                self.logger.warning(
                    f"Completed processing {model_name} with {max_retries_reached} entries "
                    f"that failed after maximum retries"
                )
                # List the failed entries
                self._list_failed_entries(model_name, failed_entries)
            else:
                self.logger.success(f"Completed processing all entries for {model_name} successfully")
            return True
        else:
            if failed_count > 0:
                self.logger.warning(
                    f"Processing for {model_name} is incomplete with {failed_count} failed entries "
                    f"({retryable_entries} can be retried, {max_retries_reached} reached max retries)"
                )
                # List the retryable entries
                self._list_retryable_entries(model_name, failed_entries)
            else:
                self.logger.warning(f"Processing for {model_name} is incomplete. Run again to continue.")
            return False

    def _list_failed_entries(self, model_name, failed_entries):
        """
        List failed entries for a model.

        Args:
            model_name (str): Name of the model
            failed_entries (list): List of failed entries
        """
        self.logger.warning(f"Failed entries for {model_name}:")
        for i, entry in enumerate(failed_entries, 1):
            entry_id = entry.get('id', 'Unknown')
            sub_id = entry.get('sub_id', 'Unknown')
            code_id = entry.get('code_id', 'Unknown')
            retry_count = entry.get('retry_count', 0)
            error = entry.get('error', 'Unknown error')
            self.logger.warning(
                f"  {i}. ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id} "
                f"(Retries: {retry_count}) - Error: {error[:100]}..."
            )

    def _list_retryable_entries(self, model_name, failed_entries):
        """
        List retryable entries for a model.

        Args:
            model_name (str): Name of the model
            failed_entries (list): List of failed entries
        """
        self.logger.warning(f"Retryable entries for {model_name}:")
        retryable_count = 0
        for entry in failed_entries:
            retry_count = entry.get('retry_count', 0)
            if retry_count < 3:  # Default max retries
                retryable_count += 1
                if retryable_count <= 5:  # Show at most 5 entries to avoid cluttering the log
                    entry_id = entry.get('id', 'Unknown')
                    sub_id = entry.get('sub_id', 'Unknown')
                    code_id = entry.get('code_id', 'Unknown')
                    self.logger.warning(
                        f"  {retryable_count}. ID: {entry_id}, Sub_ID: {sub_id}, "
                        f"Code_ID: {code_id} (Retries: {retry_count})"
                    )
        if retryable_count > 5:
            self.logger.warning(f"  ... and {retryable_count - 5} more retryable entries")

    def process_model_streaming(self, model_name):
        """
        Process all entries for a specific model using streaming approach.
        This method doesn't load the entire dataset into memory.
        Entries that fail after max retries will have empty responses.

        Args:
            model_name (str): Name of the model to process

        Returns:
            bool: True if processing completed successfully
        """
        # Get dataset path
        dataset_path = self.get_dataset_path()
        log_dir = self.config['output']['log_dir']

        # Count total entries (we need this for progress tracking)
        # This is a one-time operation that still reads the whole file, but doesn't keep it in memory
        if self.data is None:
            self.load_data()  # This is inefficient but needed for compatibility with other methods
        total_entries = len(self.data)

        # Skip if model has completed all entries
        if self._check_model_completion(model_name, total_entries):
            return True

        # Find resume point
        start_idx = find_resume_point(model_name, self.data, self.result_dir, log_dir)
        remaining = total_entries - start_idx

        self.logger.info(f"Resuming {model_name} from index {start_idx}/{total_entries} "
                    f"({remaining} entries remaining)")

        # Initialize time estimator
        time_estimator = TimeEstimator(model_name, total_entries, log_dir, start_idx)

        # Process remaining entries without progress bar
        self.logger.section(f"Processing {model_name} - {remaining} entries remaining")

        # Get the maximum retry count from config
        max_retries = self.config.get('processing', {}).get('max_retries', 3)

        # Stream the JSON data
        for idx, entry in enumerate(stream_json_data(dataset_path)):
            # Skip entries before the resume point
            if idx < start_idx:
                continue

            # Process this entry with retry mechanism
            # We always continue to the next entry, even if this one fails
            # since we now handle max retries by creating an empty response
            self._process_entry(model_name, entry, idx, total_entries, time_estimator, log_dir, max_retries)

        # Report completion status
        return self._report_completion_status(model_name, log_dir)

    def _initialize_time_tracking(self):
        """
        Initialize time tracking for all models.

        Returns:
            tuple: (process_start_time, global_estimates) - Start time and initial estimates
        """
        import time
        process_start_time = time.time()

        # Initialize global time tracker
        log_dir = self.config['output']['log_dir']
        self.global_time_tracker = GlobalTimeTracker(self.models, log_dir)

        # Ensure the global time tracker has accurate data for all completed models
        for model_name in self.models.keys():
            completed, _ = is_model_completed(model_name, self.data, self.result_dir, log_dir)
            if completed:
                model_estimate, _, has_data, _ = self._get_model_time_estimate(model_name)
                if has_data:
                    # Update the global time tracker with the actual processing time
                    self.global_time_tracker.update_model_estimate(model_name, model_estimate)

        # Calculate and display initial time estimate for all models
        initial_estimates = self._estimate_initial_processing_time()

        # Update global estimates with model-specific estimates
        for model_name, estimate in initial_estimates.get('model_estimates', {}).items():
            self.global_time_tracker.update_model_estimate(model_name, estimate)

        # Get updated global estimates for display
        global_estimates = self.global_time_tracker.get_time_estimates()

        return process_start_time, global_estimates

    def _process_single_model(self, model_name, i, total_models, completed_models, process_start_time):
        """
        Process a single model and update time tracking.

        Args:
            model_name (str): Name of the model to process
            i (int): Current model index (1-based)
            total_models (int): Total number of models
            completed_models (int): Number of models completed so far
            process_start_time (float): Start time of the entire process

        Returns:
            tuple: (completed_models, global_estimates) - Updated counts and estimates
        """
        import time

        self.logger.separator("-", 60)
        self.logger.section(f"Processing model {i}/{total_models}: {model_name}")

        # Log global progress before processing this model
        current_estimates = self.global_time_tracker.get_time_estimates()
        self.logger.global_progress(i, total_models, completed_models, process_start_time, current_estimates)

        model_start_time = time.time()

        # Use the streaming version for memory efficiency
        if self.process_model_streaming(model_name):
            completed_models += 1

        # Record model completion time
        model_elapsed = time.time() - model_start_time
        time_str = self.logger._format_time_duration(model_elapsed)
        self.logger.success(f"Model {model_name} processing time: {time_str}")

        # Update global time tracker with actual processing time
        global_estimates = self._update_time_tracker(model_name, model_elapsed, completed_models)

        # Log overall progress with updated estimates
        self.logger.global_progress(i+1, total_models, completed_models, process_start_time, global_estimates)

        return completed_models, global_estimates

    def _update_time_tracker(self, model_name, model_elapsed, completed_models):
        """
        Update the global time tracker with the actual processing time.

        Args:
            model_name (str): Name of the model
            model_elapsed (float): Elapsed time for the model
            completed_models (int): Number of models completed

        Returns:
            dict: Updated global estimates
        """
        # For completed models, we want to use the sum of all processing times
        if completed_models > 0:
            # Get the actual total processing time from the time estimator
            model_estimate, _, has_data, _ = self._get_model_time_estimate(model_name)
            if has_data:
                # Use the actual total processing time from the time estimator
                return self.global_time_tracker.record_model_completion(model_name, model_estimate)
            else:
                # Fall back to the elapsed time if we don't have detailed timing data
                return self.global_time_tracker.record_model_completion(model_name, model_elapsed)
        else:
            # For the first model, use the elapsed time
            return self.global_time_tracker.record_model_completion(model_name, model_elapsed)

    def _report_final_status(self, process_start_time):
        """
        Report the final status of all models.

        Args:
            process_start_time (float): Start time of the entire process
        """
        import time
        log_dir = self.config['output']['log_dir']

        # Final timing information
        process_elapsed = time.time() - process_start_time
        time_str = self.logger._format_time_duration(process_elapsed)
        self.logger.success(f"Total processing time: {time_str}")

        # Update incomplete models summary
        summary = update_incomplete_models_summary(self.models, log_dir, self.result_dir)

        # Print summary of incomplete models
        if summary["incomplete_count"] > 0:
            self.logger.warning(f"There are {summary['incomplete_count']} incomplete models with "
                              f"{summary['failed_entries_total']} failed entries")
            self.logger.warning(f"See {os.path.join(log_dir, 'incomplete_models.json')} for details")

    def process_all_models(self):
        """
        Process all models defined in the configuration.

        Returns:
            int: Number of completed models
        """
        if self.data is None:
            self.load_data()

        total_models = len(self.models)
        completed_models = 0

        # Initialize time tracking
        process_start_time, global_estimates = self._initialize_time_tracking()

        self.logger.separator()
        self.logger.section(f"Starting processing of {total_models} models")
        self.logger.separator()

        # Display initial global progress with estimates
        self.logger.global_progress(1, total_models, 0, process_start_time, global_estimates)

        self.logger.separator()

        # Process each model
        for i, model_name in enumerate(self.models.keys(), 1):
            completed_models, global_estimates = self._process_single_model(
                model_name, i, total_models, completed_models, process_start_time
            )

        # Report final status
        self._report_final_status(process_start_time)

        return completed_models
    def run(self):
        """
        Run the entire processing pipeline.

        Returns:
            int: Exit code (0 for success, 1 for error)
        """
        try:
            # Print startup banner
            self.logger.separator()
            self.logger.section("LLMVUL: Starting vulnerability function localization processing")
            self.logger.section(f"Using machine configuration: {self.config['machine']['name']}")
            if self.verbose:
                self.logger.section("Verbose mode enabled - detailed prompt information will be displayed")
            self.logger.separator()

            # Load data
            self.load_data()

            # Process all models
            completed_models = self.process_all_models()
            total_models = len(self.models)

            # Print completion summary
            self.logger.separator()
            self.logger.success(f"Processing complete: {completed_models}/{total_models} models fully processed")
            self.logger.separator()

            return 0

        except Exception as e:
            self.logger.critical(f"An unhandled error occurred: {e}", exc_info=True)
            return 1


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Process code samples with LLMs for vulnerability function localization'
    )
    parser.add_argument(
        '--machine',
        type=str,
        help='Machine configuration to use (mac or studio)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose mode to display detailed information about prompts and LLM interactions'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset all resume points and start processing from the beginning'
    )
    parser.add_argument(
        '--reset-model',
        type=str,
        help='Reset resume point for a specific model and start processing from the beginning'
    )
    parser.add_argument(
        '--clear-failed',
        action='store_true',
        help='Clear all failed entries for all models'
    )
    parser.add_argument(
        '--clear-failed-model',
        type=str,
        help='Clear failed entries for a specific model'
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum number of retry attempts for failed entries (default: 3)'
    )
    return parser.parse_args()


def _handle_reset_options(processor, args):
    """
    Handle reset options from command line arguments.

    Args:
        processor (LLMVulProcessor): The processor instance
        args (argparse.Namespace): Command line arguments

    Returns:
        bool: True if successful, False if error
    """
    log_dir = processor.config['output']['log_dir']

    # Handle reset options
    if args.reset:
        # Reset all resume points
        processor.logger.warning("Resetting all resume points - will start processing from the beginning")
        for model_name in processor.models.keys():
            reset_resume_point(model_name, log_dir)

    if args.reset_model:
        # Reset resume point for a specific model
        model_name = args.reset_model
        if model_name in processor.models:
            reset_resume_point(model_name, log_dir)
            processor.logger.warning(f"Reset resume point for {model_name} - will start processing from the beginning")
        else:
            processor.logger.error(f"Model {model_name} not found in configuration")
            return False

    return True

def _handle_clear_options(processor, args):
    """
    Handle clear options from command line arguments.

    Args:
        processor (LLMVulProcessor): The processor instance
        args (argparse.Namespace): Command line arguments

    Returns:
        bool: True if successful, False if error
    """
    log_dir = processor.config['output']['log_dir']

    # Handle clear failed entries options
    if args.clear_failed:
        # Clear failed entries for all models
        processor.logger.warning("Clearing failed entries for all models")
        for model_name in processor.models.keys():
            clear_failed_entries(model_name, log_dir)

    if args.clear_failed_model:
        # Clear failed entries for a specific model
        model_name = args.clear_failed_model
        if model_name in processor.models:
            clear_failed_entries(model_name, log_dir)
            processor.logger.warning(f"Cleared failed entries for {model_name}")
        else:
            processor.logger.error(f"Model {model_name} not found in configuration")
            return False

    return True

def _set_max_retries(processor, args):
    """
    Set maximum retry attempts in configuration.

    Args:
        processor (LLMVulProcessor): The processor instance
        args (argparse.Namespace): Command line arguments
    """
    # Set max retries in config
    if args.max_retries != 3:  # Only if different from default
        config = processor.config
        if 'processing' not in config:
            config['processing'] = {}
        config['processing']['max_retries'] = args.max_retries
        processor.logger.info(f"Set maximum retry attempts to {args.max_retries}")

def main():
    """
    Main entry point for the application.

    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    # Parse command line arguments
    args = parse_arguments()

    # Create the processor
    processor = LLMVulProcessor(args.machine, args.verbose)

    # Handle reset options
    if not _handle_reset_options(processor, args):
        return 1

    # Handle clear options
    if not _handle_clear_options(processor, args):
        return 1

    # Set max retries in config
    _set_max_retries(processor, args)

    # Run the processor
    return processor.run()


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
