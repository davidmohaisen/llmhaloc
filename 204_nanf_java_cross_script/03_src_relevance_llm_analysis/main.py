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
import time
import argparse
from colorama import Fore

# Import utility modules
from utils.config_loader import load_config
from utils.logger import Logger
from utils.data_handler import (
    load_json_data, ensure_directories, write_to_json,
    list_json_files, is_file_processed, get_file_resume_point,
    save_file_resume_point
)
from utils.llm_processor import interact_with_llm, generate_analysis_prompt
from utils.time_estimator import TimeEstimator


class LLMVulProcessor:
    """
    Main processor class for LLM vulnerability function localization.

    This class orchestrates the entire process of loading configuration,
    setting up logging, loading data, and processing files.
    """

    def __init__(self, verbose=False):
        """
        Initialize the processor.

        Args:
            verbose (bool, optional): Whether to enable verbose mode to display prompts.
                                     Default is False.
        """
        # Load configuration
        self.config = load_config()

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
        self.model_name = self.config['model']['name']
        self.result_dir = self.config['output']['result_dir']

        # Log verbose mode status
        if self.verbose:
            self.logger.info("Verbose mode enabled - system and user prompts will be displayed")

    def load_data(self):
        """
        Load information about available input files.

        This method counts the number of files in the input directory
        and stores basic information about them.
        """
        input_dir = self.config['data']['input_dir']
        json_files = list_json_files(input_dir)
        self.data = {
            'file_count': len(json_files),
            'files': json_files
        }
        self.logger.info(f"Found {len(json_files)} files in {input_dir}")

    def _log_time_estimates(self, time_estimates):
        """
        Log time estimates for entry processing.

        Args:
            time_estimates (dict): Dictionary with time estimates
        """
        if not time_estimates:
            return

        # Extract time estimates
        avg_time = time_estimates.get('avg_time_per_entry', 0)
        remaining_time = time_estimates.get('estimated_remaining_time', 0)
        progress = time_estimates.get('progress_percentage', 0)
        completion_time = time_estimates.get('estimated_completion_time', None)

        # Format completion time
        if completion_time:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(completion_time)
                completion_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                completion_str = completion_time
        else:
            completion_str = "Unknown"

        # Log time estimates
        self.logger.info(f"Average processing time: {avg_time:.2f} seconds per entry")
        self.logger.info(f"Progress: {progress:.2f}% complete")
        self.logger.info(f"Estimated time remaining: {self._format_time_duration(remaining_time)}")
        self.logger.info(f"Estimated completion time: {completion_str}")

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



    def process_directory(self, model_name):
        """
        Process all files in the input directory with the specified model.
        This method closely follows the approach in the archived main script.

        Args:
            model_name (str): Name of the model to process

        Returns:
            bool: True if all files were processed successfully
        """
        input_dir = self.config['data']['input_dir']
        result_dir = self.config['output']['result_dir']

        # Get all JSON files in the input directory
        json_files = list_json_files(input_dir)
        if not json_files:
            self.logger.warning(f"No JSON files found in {input_dir}")
            return False

        total_files = len(json_files)
        processed_files = 0

        self.logger.section(f"Processing {total_files} files with model {model_name}")

        # Process each file
        for idx, file_path in enumerate(json_files):
            file_name = os.path.basename(file_path)
            output_path = os.path.join(result_dir, file_name)

            self.logger.separator("-", 60)
            self.logger.info(f"Processing file {idx+1}/{total_files}: {file_name}")

            # Check if file is already fully processed
            log_dir = self.config['output']['log_dir']
            if os.path.exists(output_path) and is_file_processed(file_path, model_name, result_dir, log_dir):
                self.logger.info(f"File {file_name} is fully processed. Skipping.")
                processed_files += 1
                continue

            try:
                # Load input data
                data = load_json_data(file_path)
                total_entries = len(data)

                self.logger.info(f"Processing {file_name} with {total_entries} entries")

                # Get resume point for this file
                resume_idx = get_file_resume_point(file_path, model_name, log_dir)

                # Initialize time estimator for this file
                time_estimator = TimeEstimator(model_name, total_entries, log_dir, resume_idx)

                if resume_idx > 0:
                    self.logger.info(f"Resuming file {file_name} from entry {resume_idx+1}/{total_entries}")

                # Process each entry in the file
                for entry_idx, entry in enumerate(data):
                    # Skip entries before the resume point
                    if entry_idx < resume_idx:
                        continue
                    entry_id = entry.get('id', 'Unknown')
                    sub_id = entry.get('sub_id', 'Unknown')
                    code_id = entry.get('code_id', 'Unknown')

                    self.logger.info(
                        f"Processing {file_name} - Progress: {entry_idx+1}/{total_entries} "
                        f"({((entry_idx+1)/total_entries*100):.2f}%) "
                        f"- ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}"
                    )

                    try:
                        # Start timing this entry
                        time_estimator.start_entry()

                        # Extract response from entry
                        response = entry.get('response', '')

                        # Generate prompt for analysis
                        custom_prompt = generate_analysis_prompt(response)

                        # Interact with LLM
                        new_entry = interact_with_llm(entry, custom_prompt, model_name, self.config)

                        # Write result to output file
                        write_to_json(new_entry, model_name, result_dir, file_path)

                        # End timing and get estimates
                        time_estimates = time_estimator.end_entry()

                        # Save resume point for this file
                        save_file_resume_point(file_path, model_name, entry_idx+1, total_entries, log_dir)

                        # Display time estimates
                        self.logger.separator("-", 60)
                        self.logger.progress(
                            entry_idx+1, total_entries,
                            f"- File: {file_name} - ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}"
                        )
                        self._log_time_estimates(time_estimates)

                    except Exception as e:
                        self.logger.error(
                            f"Failed processing {file_name} - Entry {entry_idx+1}/{total_entries} "
                            f"- ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}: {e}",
                            exc_info=True
                        )
                        continue

                # Mark file as completed
                save_file_resume_point(file_path, model_name, total_entries, total_entries, log_dir)
                processed_files += 1

            except Exception as e:
                self.logger.error(f"Error processing file {file_name}: {e}", exc_info=True)
                continue

            # Log overall progress
            progress_percent = (idx + 1) / total_files * 100
            self.logger.info(f"Overall progress: {idx+1}/{total_files} files ({progress_percent:.2f}%)")

        self.logger.success(f"Completed processing {processed_files}/{total_files} files with model {model_name}")
        return processed_files == total_files



    def process_all_files(self):
        """
        Process all files with the configured model.

        Returns:
            int: Number of processed files
        """
        if self.data is None:
            self.load_data()

        # Start timing the entire process
        import time
        process_start_time = time.time()

        self.logger.separator()
        self.logger.section(f"Starting processing with model: {self.model_name}")
        self.logger.separator()

        # Process all files with the single model
        processed_files = 0
        if self.process_directory(self.model_name):
            processed_files = self.data['file_count']

        # Final timing information
        process_elapsed = time.time() - process_start_time
        time_str = self._format_time_duration(process_elapsed)
        self.logger.success(f"Total processing time: {time_str}")

        return processed_files

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

            # Display input directory and model
            input_dir = self.config['data'].get('input_dir', 'Unknown')
            self.logger.section(f"Input directory: {input_dir}")
            self.logger.section(f"Using model: {self.model_name}")
            self.logger.section(f"Model context window: {self.config['model']['context_window']}")

            self.logger.separator()

            # Load data
            self.load_data()

            # Process all files with the single model
            processed_files = self.process_all_files()
            total_files = self.data['file_count']

            # Print completion summary
            self.logger.separator()
            self.logger.success(f"Processing complete: {processed_files}/{total_files} files fully processed")
            self.logger.separator()

            return 0

        except Exception as e:
            self.logger.critical(f"An unhandled error occurred: {e}", exc_info=True)
            # Print a message to the console to make sure the user sees it
            print(f"\n{Fore.RED}ERROR: An unhandled error occurred. Check the log file at {self.logger.error_log_path} for details.")
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
    processor = LLMVulProcessor(verbose=args.verbose)
    return processor.run()


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
