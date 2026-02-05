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
    --verbose                Enable verbose mode to display system and user prompts
"""

import os
import sys
import json
import argparse
from tqdm import tqdm

# Import utility modules
from utils.config_loader import load_config
from utils.logger import Logger
from utils.data_handler import (
    load_json_data, stream_json_data, ensure_directories, is_model_completed,
    find_resume_point, write_to_json, save_resume_point
)
from utils.llm_processor import (
    extract_fields, generate_prompt, interact_with_llm
)
from utils.time_estimator import TimeEstimator


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
            verbose (bool, optional): Whether to enable verbose mode to display prompts.
                                     Default is False.
        """
        # Load configuration
        self.config = load_config(machine_name)

        # Store verbose flag
        self.verbose = verbose

        # Add verbose flag to config for access by other modules
        self.config['verbose'] = verbose

        # Initialize logger
        self.logger = Logger(self.config)

        # Ensure directories exist
        ensure_directories(self.config)

        # Initialize data
        self.data = None
        self.models = self.config['models']
        self.result_dir = self.config['output']['result_dir']

        # Log verbose mode status
        if self.verbose:
            self.logger.info("Verbose mode enabled - system and user prompts will be displayed")

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

    def process_model(self, model_name):
        """
        Process all entries for a specific model.

        Args:
            model_name (str): Name of the model to process

        Returns:
            bool: True if processing completed successfully
        """
        if self.data is None:
            self.load_data()

        total_entries = len(self.data)
        log_dir = self.config['output']['log_dir']

        # Skip if model has completed all entries
        if is_model_completed(model_name, self.data, self.result_dir, log_dir):
            self.logger.success(f"Skipping {model_name} - already completed all {total_entries} entries")
            return True

        # Find resume point
        start_idx = find_resume_point(model_name, self.data, self.result_dir, log_dir)
        remaining = total_entries - start_idx

        self.logger.info(f"Resuming {model_name} from index {start_idx}/{total_entries} "
                    f"({remaining} entries remaining)")

        # Initialize time estimator
        time_estimator = TimeEstimator(model_name, total_entries, log_dir, start_idx)

        # Process remaining entries with progress bar
        with tqdm(total=remaining, desc=f"Processing {model_name}",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:

            for idx, entry in enumerate(self.data[start_idx:], start=start_idx):
                try:
                    # Start timing this entry
                    time_estimator.start_entry()

                    code, filename, entry_id, sub_id, code_id, ast_info = extract_fields(entry)

                    # Generate prompt and interact with LLM
                    custom_prompt = generate_prompt(code, filename, ast_info)
                    new_entry = interact_with_llm(entry, custom_prompt, model_name, self.config)
                    write_to_json(new_entry, model_name, self.result_dir)

                    # End timing and get estimates
                    time_estimates = time_estimator.end_entry()

                    # Save resume point with time estimates
                    save_resume_point(model_name, entry, idx+1, total_entries, log_dir, time_estimates)

                    # Detailed progress and time logging
                    self.logger.separator("-", 60)
                    self.logger.progress(
                        idx+1, total_entries,
                        f"- ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}"
                    )
                    self.logger.time_estimate(idx+1, total_entries, time_estimates)

                    # Update progress bar
                    pbar.update(1)

                except Exception as e:
                    self.logger.error(
                        f"Failed processing {model_name} - Index: {idx+1}/{total_entries} "
                        f"- ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}: {e}"
                    )
                    continue

        # Check if we've completed all entries
        if is_model_completed(model_name, self.data, self.result_dir, log_dir):
            self.logger.success(f"Completed processing all entries for {model_name}")
            return True
        else:
            self.logger.warning(f"Processing for {model_name} is incomplete. Run again to continue.")
            return False

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

    def _get_model_time_estimate(self, model_name):
        """
        Get time estimate for a single model based on previous runs.

        Args:
            model_name (str): Name of the model

        Returns:
            tuple: (model_estimate, avg_time, has_data)
        """
        from utils.llm_processor import sanitize_model_name

        total_entries = len(self.data)
        log_dir = self.config['output']['log_dir']

        # Check if we have timing data for this model
        times_dir = os.path.join(log_dir, "processing_times")
        if not os.path.exists(times_dir):
            return 0, 0, False

        times_file = os.path.join(times_dir, f"{sanitize_model_name(model_name)}_times.json")
        if not os.path.exists(times_file) or os.path.getsize(times_file) == 0:
            return 0, 0, False

        try:
            with open(times_file, 'r') as file:
                data = json.load(file)
                times = data.get('processing_times', [])
                if not times:
                    return 0, 0, False

                avg_time = sum(times) / len(times)

                # If model is not completed, estimate remaining time
                if not is_model_completed(model_name, self.data, self.result_dir, log_dir):
                    start_idx = find_resume_point(model_name, self.data, self.result_dir, log_dir)
                    remaining = total_entries - start_idx
                    model_estimate = avg_time * remaining
                else:
                    model_estimate = 0  # Model is already completed

                return model_estimate, avg_time, True
        except Exception as e:
            self.logger.warning(f"Error reading timing data for {model_name}: {e}")
            return 0, 0, False

    def _estimate_initial_processing_time(self):
        """
        Estimate the total processing time based on previous runs.

        Returns:
            tuple: (total_time_estimate, models_with_data)
        """
        from datetime import datetime, timedelta

        total_models = len(self.models)

        # Try to estimate total time based on previous runs
        total_time_estimate = 0
        models_with_data = 0

        for model_name in self.models.keys():
            model_estimate, avg_time, has_data = self._get_model_time_estimate(model_name)

            if has_data:
                total_time_estimate += model_estimate
                models_with_data += 1
                self.logger.info(f"Model {model_name}: Average {avg_time:.2f}s per entry")

        # If we have timing data for at least one model, estimate total time
        if models_with_data > 0:
            # For models without timing data, use the average of models with data
            avg_model_time = total_time_estimate / models_with_data
            models_without_data = total_models - models_with_data
            total_time_estimate += avg_model_time * models_without_data

            # Format and display the estimate
            time_str = self._format_time_duration(total_time_estimate)
            completion_time = datetime.now() + timedelta(seconds=total_time_estimate)
            completion_str = completion_time.strftime("%Y-%m-%d %H:%M:%S")

            self.logger.info(f"Estimated total processing time: {time_str}")
            self.logger.info(f"Estimated completion time: {completion_str}")
        else:
            self.logger.info("No previous timing data available for estimation")

        return total_time_estimate, models_with_data

    def _log_overall_progress(self, i, total_models, process_start_time):
        """
        Log the overall progress and time estimates.

        Args:
            i (int): Current model index
            total_models (int): Total number of models
            process_start_time (float): Start time of the entire process
        """
        import time
        from datetime import datetime, timedelta

        # Update overall progress and time estimate
        process_elapsed = time.time() - process_start_time
        process_percent = (i / total_models) * 100

        # Only estimate if we're not done
        if i < total_models:
            # Calculate estimated time
            estimated_total = process_elapsed * (total_models / i)
            estimated_remaining = estimated_total - process_elapsed

            # Format times
            elapsed_str = self._format_time_duration(process_elapsed)
            remaining_str = self._format_time_duration(estimated_remaining)

            # Calculate completion time
            completion_time = datetime.now() + timedelta(seconds=estimated_remaining)
            completion_str = completion_time.strftime("%Y-%m-%d %H:%M:%S")

            # Log progress
            self.logger.info(f"Overall progress: [{i}/{total_models}] ({process_percent:.2f}%)")
            self.logger.info(f"Elapsed: {elapsed_str} | Remaining: {remaining_str}")
            self.logger.info(f"Estimated completion: {completion_str}")

    def process_model_streaming(self, model_name):
        """
        Process all entries for a specific model using streaming approach.
        This method doesn't load the entire dataset into memory.

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
        if is_model_completed(model_name, self.data, self.result_dir, log_dir):
            self.logger.success(f"Skipping {model_name} - already completed all {total_entries} entries")
            return True

        # Find resume point
        start_idx = find_resume_point(model_name, self.data, self.result_dir, log_dir)
        remaining = total_entries - start_idx

        self.logger.info(f"Resuming {model_name} from index {start_idx}/{total_entries} "
                    f"({remaining} entries remaining)")

        # Initialize time estimator
        time_estimator = TimeEstimator(model_name, total_entries, log_dir, start_idx)

        # Process remaining entries with progress bar
        with tqdm(total=remaining, desc=f"Processing {model_name}",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:

            # Stream the JSON data
            for idx, entry in enumerate(stream_json_data(dataset_path)):
                # Skip entries before the resume point
                if idx < start_idx:
                    continue

                try:
                    # Start timing this entry
                    time_estimator.start_entry()

                    code, filename, entry_id, sub_id, code_id, ast_info = extract_fields(entry)

                    # Generate prompt and interact with LLM
                    custom_prompt = generate_prompt(code, filename, ast_info)
                    new_entry = interact_with_llm(entry, custom_prompt, model_name, self.config)
                    write_to_json(new_entry, model_name, self.result_dir)

                    # End timing and get estimates
                    time_estimates = time_estimator.end_entry()

                    # Save resume point with time estimates
                    save_resume_point(model_name, entry, idx+1, total_entries, log_dir, time_estimates)

                    # Detailed progress and time logging
                    self.logger.separator("-", 60)
                    self.logger.progress(
                        idx+1, total_entries,
                        f"- ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}"
                    )
                    self.logger.time_estimate(idx+1, total_entries, time_estimates)

                    # Update progress bar
                    pbar.update(1)

                except Exception as e:
                    self.logger.error(
                        f"Failed processing {model_name} - Index: {idx+1}/{total_entries} "
                        f"- ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}: {e}"
                    )
                    continue

        # Check if we've completed all entries
        if is_model_completed(model_name, self.data, self.result_dir, log_dir):
            self.logger.success(f"Completed processing all entries for {model_name}")
            return True
        else:
            self.logger.warning(f"Processing for {model_name} is incomplete. Run again to continue.")
            return False

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

        # Start timing the entire process
        import time
        process_start_time = time.time()

        self.logger.separator()
        self.logger.section(f"Starting processing of {total_models} models")
        self.logger.separator()

        # Calculate and display initial time estimate for all models
        self._estimate_initial_processing_time()
        self.logger.separator()

        # Process each model
        for i, model_name in enumerate(self.models.keys(), 1):
            self.logger.separator("-", 60)
            self.logger.section(f"Processing model {i}/{total_models}: {model_name}")

            model_start_time = time.time()

            # Use the streaming version for memory efficiency
            if self.process_model_streaming(model_name):
                completed_models += 1

            model_elapsed = time.time() - model_start_time
            time_str = self._format_time_duration(model_elapsed)
            self.logger.success(f"Model {model_name} processing time: {time_str}")

            # Log overall progress
            self._log_overall_progress(i, total_models, process_start_time)

        # Final timing information
        process_elapsed = time.time() - process_start_time
        time_str = self._format_time_duration(process_elapsed)
        self.logger.success(f"Total processing time: {time_str}")

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
        help='Enable verbose mode to display system and user prompts'
    )
    return parser.parse_args()


def main():
    """
    Main entry point for the application.

    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    # Parse command line arguments
    args = parse_arguments()

    # Create and run the processor
    processor = LLMVulProcessor(args.machine, verbose=args.verbose)
    return processor.run()


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
