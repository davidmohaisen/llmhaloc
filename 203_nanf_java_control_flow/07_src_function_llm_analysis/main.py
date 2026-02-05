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
    load_json_data, ensure_directories, list_json_files,
    is_fully_processed, append_to_output
)
from utils.llm_processor import process_entry
from utils.time_estimator import TimeEstimator, GlobalTimeEstimator
from utils.resume_manager import ResumeState


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

    def _check_resume_point(self, file_name):
        """
        Check if a resume point exists for the file and log information about it.

        Args:
            file_name (str): Name of the file being processed

        Returns:
            ResumeState: Resume state object if found and loaded, None otherwise
        """
        log_dir = self.config['output']['log_dir']
        resume_state = ResumeState(log_dir)

        if resume_state.load_state(file_name):
            if resume_state.completed:
                self.logger.info(f"Found completed resume point for file {file_name}")
            else:
                self.logger.info(
                    f"Found resume point for file {file_name} at "
                    f"ID:{resume_state.last_processed.get('id')}, "
                    f"Sub_ID:{resume_state.last_processed.get('sub_id')}, "
                    f"Code_ID:{resume_state.last_processed.get('code_id')}, "
                    f"Function_ID:{resume_state.last_processed.get('function_id')} "
                    f"({resume_state.progress_percentage:.2f}% complete)"
                )

                # Log time estimates if available
                if resume_state.time_estimates:
                    self._log_time_estimates(resume_state.time_estimates)

            return resume_state

        return None

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

        # Check for resume points for each file
        for file_path in json_files:
            file_name = os.path.basename(file_path)
            self._check_resume_point(file_name)

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
        Uses the logger's time formatting method for consistency.

        Args:
            seconds (float): Time in seconds

        Returns:
            str: Formatted time string (e.g., "2h 30m 45s")
        """
        # Use the logger's time formatting method for consistency
        return self.logger._format_time_duration(seconds)



    def _load_ground_truth_data(self, ground_truth_path):
        """
        Load ground truth data from the specified path.

        Args:
            ground_truth_path (str): Path to the ground truth file

        Returns:
            list or None: List of ground truth entries if successful, None otherwise
        """
        try:
            ground_truth_data = load_json_data(ground_truth_path)
            self.logger.info(f"Loaded {len(ground_truth_data)} entries from ground truth")
            return ground_truth_data
        except Exception as e:
            self.logger.error(f"Error loading ground truth data: {e}", exc_info=True)
            return None

    def _find_matching_input_entry(self, input_data, ground_truth_entry):
        """
        Find the matching input entry for a ground truth entry.

        Args:
            input_data (list): List of input entries
            ground_truth_entry (dict): Ground truth entry to match

        Returns:
            dict or None: Matching input entry if found, None otherwise
        """
        return next(
            (entry for entry in input_data
             if entry['id'] == ground_truth_entry['id'] and
                entry['sub_id'] == ground_truth_entry['sub_id'] and
                entry['code_id'] == ground_truth_entry['code_id']),
            None
        )

    def _process_single_function(self, input_entry, ground_truth_entry, model_name, output_path, time_estimator):
        """
        Process a single function and append the result to the output file.

        Args:
            input_entry (dict): Input entry to process
            ground_truth_entry (dict): Ground truth entry for the function
            model_name (str): Name of the model to use
            output_path (str): Path to the output file
            time_estimator (TimeEstimator): Time estimator instance

        Returns:
            tuple: (True, time_estimates) if processing was successful

        Raises:
            RuntimeError: If an error occurs during processing, with detailed error information
        """
        try:
            # Start timing this entry with the ground truth entry for resume tracking
            time_estimator.start_entry(ground_truth_entry)

            # Process the entry
            output_entry = process_entry(input_entry, ground_truth_entry, model_name, self.config)

            # Append to output file
            append_to_output(output_path, output_entry)

            # End timing and get estimates
            time_estimates = time_estimator.end_entry(success=True)

            return True, time_estimates
        except Exception as e:
            # Log the error with full traceback
            function_id = (
                f"ID: {ground_truth_entry['id']}, "
                f"Sub_ID: {ground_truth_entry['sub_id']}, "
                f"Code_ID: {ground_truth_entry['code_id']}, "
                f"Function_ID: {ground_truth_entry['function_id']}"
            )

            self.logger.error(f"Failed processing function ({function_id}): {e}", exc_info=True)

            # Record the failure in the time estimator
            if time_estimator.last_entry_start_time is not None:
                time_estimator.end_entry(success=False)

            # Create a detailed error message
            error_message = (
                f"Critical error while processing function {function_id}:\n"
                f"{str(e)}\n\n"
                f"Processing has been halted. Please fix the issue and restart."
            )

            # Re-raise the exception with a more detailed message to be caught by the top-level handler
            raise RuntimeError(error_message) from e

    def _log_function_progress(self, gt_idx, total_gt_entries, ground_truth_entry, time_estimates=None):
        """
        Log progress information for a function using the new file_progress method.

        Args:
            gt_idx (int): Current ground truth entry index
            total_gt_entries (int): Total number of ground truth entries
            ground_truth_entry (dict): Current ground truth entry
            time_estimates (dict, optional): Time estimates to log
        """
        # Use the new file_progress method for better formatting
        self.logger.file_progress(
            gt_idx,
            total_gt_entries,
            ground_truth_entry,
            time_estimates
        )

    def _process_file(self, file_path, file_idx, total_files, ground_truth_data, model_name, result_dir, log_dir):
        """
        Process a single file.

        Args:
            file_path (str): Path to the input file
            file_idx (int): Index of the current file
            total_files (int): Total number of files
            ground_truth_data (list): List of ground truth entries
            model_name (str): Name of the model to use
            result_dir (str): Directory for output files
            log_dir (str): Directory for log files

        Returns:
            bool: True if processing was successful

        Raises:
            RuntimeError: If an error occurs during processing, with detailed error information
        """
        file_name = os.path.basename(file_path)
        output_path = os.path.join(result_dir, file_name)

        self.logger.separator("-", 60)
        self.logger.info(f"Processing file {file_idx+1}/{total_files}: {file_name}")

        # Check if file is already fully processed using resume point
        if os.path.exists(output_path) and is_fully_processed(output_path, ground_truth_data, log_dir, file_name):
            self.logger.info(f"File {file_name} is fully processed. Skipping.")
            return True

        try:
            # Load input data
            input_data = load_json_data(file_path)
            self.logger.info(f"Loaded {len(input_data)} entries from {file_name}")

            # Create a resume state for this file
            resume_state = ResumeState(log_dir)
            resume_idx = 0

            # Try to load existing resume state
            if resume_state.load_state(file_name):
                # Find the index to resume from
                resume_idx = resume_state.find_resume_index(ground_truth_data)
                if resume_idx > 0:
                    self.logger.info(f"Resuming from function {resume_idx + 1}/{len(ground_truth_data)}")
                else:
                    self.logger.info(f"No resume point found for {file_name}, starting from the beginning")

            # Initialize time estimator for this file
            time_estimator = TimeEstimator(file_name, len(ground_truth_data), log_dir, resume_idx)

            # Process each ground truth entry from resume point
            for gt_idx, ground_truth_entry in enumerate(ground_truth_data[resume_idx:], resume_idx + 1):
                # Log initial progress information using the new file_progress method
                self.logger.file_progress(
                    gt_idx,
                    len(ground_truth_data),
                    ground_truth_entry,
                    time_estimator.get_estimates()
                )

                # Find matching input entry
                input_entry = self._find_matching_input_entry(input_data, ground_truth_entry)

                if input_entry:
                    # Process the function
                    success, time_estimates = self._process_single_function(
                        input_entry, ground_truth_entry, model_name, output_path, time_estimator
                    )

                    # Log progress after processing
                    if success:
                        self._log_function_progress(
                            gt_idx, len(ground_truth_data),
                            ground_truth_entry, time_estimates
                        )
                else:
                    self.logger.warning(
                        f"No matching input entry found for ground truth entry "
                        f"(ID: {ground_truth_entry['id']}, "
                        f"Sub_ID: {ground_truth_entry['sub_id']}, "
                        f"Code_ID: {ground_truth_entry['code_id']}, "
                        f"Function_ID: {ground_truth_entry['function_id']})"
                    )

            self.logger.info(f"Completed processing file {file_idx+1}/{total_files}: {file_name}")
            return True

        except Exception as e:
            # Log the error with full traceback
            self.logger.error(f"Error processing file {file_name}: {e}", exc_info=True)

            # Create a detailed error message
            error_message = (
                f"Critical error while processing file {file_name}:\n"
                f"{str(e)}\n\n"
                f"Processing has been halted. Please fix the issue and restart."
            )

            # Re-raise the exception with a more detailed message to be caught by the top-level handler
            raise RuntimeError(error_message) from e

    def _clear_resume_point(self, file_name, log_dir):
        """
        Clear the resume point for a file when processing is complete.

        Args:
            file_name (str): Name of the file being processed
            log_dir (str): Directory for log files

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Clearing resume point for file {file_name}")
            resume_state = ResumeState(log_dir)
            return resume_state.clear_state(file_name)
        except Exception as e:
            self.logger.warning(f"Error clearing resume point for file {file_name}: {e}")
            return False

    def process_directory(self, model_name):
        """
        Process all files in the input directory with the specified model.
        This method follows the approach in the archived main script, processing
        function-level analysis rather than file-level analysis.

        Args:
            model_name (str): Name of the model to process

        Returns:
            bool: True if all files were processed successfully
        """
        input_dir = self.config['data']['input_dir']
        result_dir = self.config['output']['result_dir']
        log_dir = self.config['output']['log_dir']
        ground_truth_path = self.config['data']['ground_truth_path']

        # Load ground truth data
        ground_truth_data = self._load_ground_truth_data(ground_truth_path)
        if ground_truth_data is None:
            return False

        # Get all JSON files in the input directory
        json_files = list_json_files(input_dir)
        if not json_files:
            self.logger.warning(f"No JSON files found in {input_dir}")
            return False

        total_files = len(json_files)
        processed_files = 0

        self.logger.section(f"Processing {total_files} files with model {model_name}")

        # Initialize global time estimator
        global_estimator = GlobalTimeEstimator(total_files, log_dir)

        # Process each file
        for idx, file_path in enumerate(json_files):
            # Start timing this file
            global_estimator.start_file(idx)

            # Get file name for display
            file_name = os.path.basename(file_path)

            # Display global progress before processing the file
            global_time_estimates = global_estimator.get_estimates()
            self.logger.global_progress(idx + 1, total_files, file_name, global_time_estimates)

            # Process the file - this will now raise an exception on error
            # which will be caught by the top-level exception handler
            self._process_file(file_path, idx, total_files, ground_truth_data, model_name, result_dir, log_dir)

            # If we get here, the file was processed successfully
            processed_files += 1
            # Record successful completion
            global_time_estimates = global_estimator.end_file(success=True)

            # Display updated global progress after processing the file
            self.logger.global_progress(idx + 1, total_files, file_name, global_time_estimates)

        # Clear resume points for all processed files
        if processed_files > 0:
            for file_path in json_files:
                file_name = os.path.basename(file_path)
                output_path = os.path.join(result_dir, file_name)
                if os.path.exists(output_path) and is_fully_processed(output_path, ground_truth_data, log_dir, file_name):
                    self._clear_resume_point(file_name, log_dir)

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
        self.logger.section(f"Model context window: {self.config['model']['context_window']}")
        self.logger.separator()

        # Process all files with the single model
        processed_files = 0
        if self.process_directory(self.model_name):
            processed_files = self.data['file_count']

        # Final timing information
        process_elapsed = time.time() - process_start_time
        time_str = self._format_time_duration(process_elapsed)

        # Display final summary with clear formatting
        self.logger.separator("=", 80)
        self.logger.success(f"PROCESSING COMPLETE - {processed_files}/{self.data['file_count']} files processed")
        self.logger.success(f"Total processing time: {time_str}")

        # Calculate and display processing rate
        if process_elapsed > 0:
            files_per_hour = (processed_files / process_elapsed) * 3600
            self.logger.success(f"Processing rate: {files_per_hour:.2f} files per hour")

        self.logger.separator("=", 80)

        return processed_files

    def run(self):
        """
        Run the entire processing pipeline.

        Returns:
            int: Exit code (0 for success, 1 for error)
        """
        try:
            # Print startup banner
            self.logger.separator("=", 80)
            self.logger.section("LLMVUL: VULNERABILITY FUNCTION LOCALIZATION")
            self.logger.separator("-", 80)

            # Display input directory and model
            input_dir = self.config['data'].get('input_dir', 'Unknown')
            self.logger.section(f"Input directory: {input_dir}")
            self.logger.section(f"Using model: {self.model_name}")

            # Display logging configuration
            self.logger.info(f"Error logs will be saved to: {self.logger.error_log_path}")
            self.logger.info(f"Warning logs will be saved to: {self.logger.warning_log_path}")
            self.logger.separator("=", 80)

            # Load data
            self.load_data()

            # Process all files with the single model
            self.process_all_files()

            # Final success message is already printed in process_all_files
            return 0

        except Exception as e:
            # Log the critical error with full traceback
            self.logger.critical(f"An unhandled error occurred: {e}", exc_info=True)

            # Create a prominent error message in the console
            print("\n")
            print(f"{Fore.RED}" + "=" * 80)
            print(f"{Fore.RED}SYSTEM HALTED: CRITICAL ERROR DETECTED")
            print(f"{Fore.RED}" + "=" * 80)
            print(f"{Fore.RED}Error details: {str(e)}")

            # Get the traceback information
            import traceback
            error_traceback = traceback.format_exc()

            # Print the traceback with red color
            print(f"{Fore.RED}Stack trace:")
            for line in error_traceback.split('\n'):
                print(f"{Fore.RED}{line}")

            # Save error details to a timestamped file for easier access
            try:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                error_file = os.path.join(self.config['output']['log_dir'], f"critical_error_{timestamp}.log")

                with open(error_file, 'w') as f:
                    f.write(f"Error occurred at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Error message: {str(e)}\n")
                    f.write(f"Stack trace:\n{error_traceback}\n")

                print(f"{Fore.YELLOW}Detailed error information has been saved to: {error_file}")
            except Exception as save_error:
                print(f"{Fore.RED}Failed to save detailed error information: {save_error}")

            # Provide instructions for the user
            print(f"\n{Fore.YELLOW}INSTRUCTIONS FOR RESOLUTION:")
            print(f"{Fore.YELLOW}1. Review the error details above and in the error log at: {self.logger.error_log_path}")
            print(f"{Fore.YELLOW}2. Fix the identified issue in the code or configuration")
            print(f"{Fore.YELLOW}3. Restart the system by running: python main.py")
            print(f"\n{Fore.RED}The system has been halted and must be manually restarted after the issue is resolved.")

            # Return error code
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
