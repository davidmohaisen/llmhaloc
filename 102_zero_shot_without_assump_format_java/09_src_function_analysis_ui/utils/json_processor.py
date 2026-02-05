"""
JSON processor for the LLM Vulnerability Function Localization Web Processing.
"""

import json
import os
import re
import threading
import time
from typing import Dict, Any, List, Optional, Union

from .config_manager import config
from .logging_manager import logger
from .ui_manager import update_progress


class JSONProcessor:
    """
    Processor for JSON files containing LLM responses for vulnerability function localization.
    """

    def __init__(self):
        """
        Initialize the JSON processor.
        """
        self.current_object = None
        self.user_decision = None
        self.current_filename = None
        self.processed_objects = []  # List to track processed objects
        self.processed_files = []    # List to track completed files
        self.processing_paused = threading.Event()
        self.is_processing = False
        self.decision_stage = None
        self.auto_decision = None
        self.awaiting_user_decision = False
        self.show_auto_analysis = False

    def reset_processing_state(self):
        """
        Reset all processing state variables.
        """
        self.current_object = None
        self.user_decision = None
        self.current_filename = None
        self.processed_objects = []
        self.processed_files = []
        self.is_processing = False
        self.decision_stage = None
        self.auto_decision = None
        self.awaiting_user_decision = False
        self.show_auto_analysis = False
        logger.info("Processing state reset")

    def get_current_object(self) -> Optional[Dict[str, Any]]:
        """
        Get the current object being processed.

        Returns:
            The current object or None if no object is being processed.
        """
        return self.current_object

    def get_current_filename(self) -> Optional[str]:
        """
        Get the name of the file currently being processed.

        Returns:
            The current filename or None if no file is being processed.
        """
        return self.current_filename

    def set_user_decision(self, decision: Union[int, bool]):
        """
        Set the user's decision for the current object.

        Args:
            decision: The user's decision (1/True for vulnerable, 0/False for not vulnerable).
        """
        self.user_decision = decision
        self.awaiting_user_decision = False
        self.processing_paused.set()  # Resume processing
        logger.info(f"User decision set: {decision}")

    def get_decision_context(self) -> Dict[str, Any]:
        """
        Get the current decision context for the UI.

        Returns:
            Dictionary with decision stage and visibility hints.
        """
        return {
            "decision_stage": self.decision_stage,
            "auto_decision": self.auto_decision,
            "awaiting_user_decision": self.awaiting_user_decision,
            "show_auto_analysis": self.show_auto_analysis,
        }

    def _clear_decision_context(self):
        """
        Clear decision-specific state after finalizing an object.
        """
        self.current_object = None
        self.user_decision = None
        self.decision_stage = None
        self.auto_decision = None
        self.awaiting_user_decision = False
        self.show_auto_analysis = False

    def _await_user_decision(
        self,
        obj: Dict[str, Any],
        auto_decision: Optional[int],
        stage: int,
    ) -> Union[int, bool]:
        """
        Pause processing and wait for a user decision.

        Args:
            obj: The current object being reviewed.
            auto_decision: Parsed automatic decision, if available.
            stage: Review stage (1 or 2).

        Returns:
            The user's decision.
        """
        self.current_object = obj
        self.user_decision = None
        self.decision_stage = stage
        self.auto_decision = auto_decision
        self.show_auto_analysis = stage == 2
        self.awaiting_user_decision = True
        self.processing_paused.clear()

        logger.info(
            f"Waiting for user decision (stage {stage}) on object ID: {obj.get('id', 'unknown')}"
        )
        self.processing_paused.wait()

        self.awaiting_user_decision = False
        return self.user_decision

    def get_processed_status(self) -> List[Dict[str, str]]:
        """
        Get the list of processed files.

        Returns:
            A list of dictionaries, each with a 'filename' key containing the filename (no paths).
            Always returns a valid list, even if empty.
        """
        try:
            # Create a clean list of unique filenames without paths
            unique_filenames = set()
            clean_files = []

            # Ensure processed_files is initialized
            if not hasattr(self, 'processed_files') or self.processed_files is None:
                self.processed_files = []
                logger.warning("processed_files was not initialized, creating empty list")

            # Ensure it's a list
            if not isinstance(self.processed_files, list):
                logger.warning(f"processed_files is not a list: {type(self.processed_files)}, creating empty list")
                self.processed_files = []

            for item in self.processed_files:
                if isinstance(item, str):
                    # Extract just the filename without the path
                    filename = item.split('/')[-1]
                    if filename not in unique_filenames:
                        unique_filenames.add(filename)
                        clean_files.append(filename)
                else:
                    logger.warning(f"Found non-string item in processed_files: {item}, removing it")

            # Update processed_files to the clean list
            self.processed_files = clean_files

            # Return as list of dicts with 'filename' key
            result = [{"filename": filename} for filename in self.processed_files]

            # Debug outputs
            logger.debug(f"Clean processed files list: {clean_files}")
            logger.debug(f"Returning processed files: {result}")

            # Return the result without printing to console
            return result
        except Exception as e:
            # If anything goes wrong, log it and return an empty list
            logger.error(f"Error in get_processed_status: {str(e)}")
            return []

    def process_json_files(self, input_dir: str, output_dir: str):
        """
        Process JSON files containing LLM responses.

        Args:
            input_dir: Directory containing the input JSON files.
            output_dir: Directory to write the processed JSON files.
        """
        # Set processing flag to true
        self.is_processing = True

        # Clear processed_objects list to ensure it's empty
        self.processed_objects.clear()

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        json_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.json')])
        total_files = len(json_files)
        logger.info(f"Found {total_files} JSON files to process")

        # Count total objects across all files
        total_objects_all_files = 0
        objects_per_file = []
        for filename in json_files:
            input_path = os.path.join(input_dir, filename)
            with open(input_path, 'r') as f:
                data = json.load(f)
            objects_per_file.append(len(data))
            total_objects_all_files += len(data)

        logger.info(f"Total objects across all files: {total_objects_all_files}")

        # Track processed objects count
        processed_objects_count = 0

        for file_index, filename in enumerate(json_files, 1):
            self.current_filename = filename
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)

            logger.info(f"Processing file {file_index}/{total_files}: {filename}")

            with open(input_path, 'r') as f:
                data = json.load(f)

            file_objects = len(data)
            logger.info(f"File contains {file_objects} objects")

            with open(output_path, 'w') as out_f:
                out_f.write('[\n')
                for obj_index, obj in enumerate(data, 1):
                    # Update progress
                    update_progress(
                        file_index,
                        total_files,
                        obj_index,
                        file_objects,
                        processed_objects_count,
                        total_objects_all_files,
                    )

                    # Process function decisions based on relevance_label
                    relevance_label = obj.get('relevance_label')
                    if relevance_label in (-1, 0):
                        # If not relevant or not vulnerable, set function_label to 0
                        obj['function_label'] = 0
                    else:
                        function_analysis = obj.get('function_analysis')
                        auto_decision = (
                            self.extract_function_vulnerability(function_analysis)
                            if function_analysis
                            else None
                        )
                        first_decision = self._await_user_decision(obj, auto_decision, stage=1)

                        if auto_decision is not None and first_decision == auto_decision:
                            obj['function_label'] = first_decision
                            logger.info(
                                f"Consensus reached (stage 1) for object ID: {obj.get('id', 'unknown')}"
                            )
                        else:
                            if auto_decision is None:
                                logger.info(
                                    "Automatic analysis could not be parsed; requesting second review for "
                                    f"object ID: {obj.get('id', 'unknown')}"
                                )
                            else:
                                logger.info(
                                    "Automatic analysis disagrees with user decision; requesting second review for "
                                    f"object ID: {obj.get('id', 'unknown')}"
                                )

                            second_decision = self._await_user_decision(obj, auto_decision, stage=2)
                            obj['function_label'] = second_decision
                            logger.info(
                                f"Applied final user decision: {second_decision} to object ID: {obj.get('id', 'unknown')}"
                            )

                        self._clear_decision_context()

                    # Add to processed objects
                    self.processed_objects.append(obj)
                    processed_objects_count += 1

                    # Write the processed object immediately
                    output_obj = dict(obj)
                    output_obj.pop('function_analysis', None)
                    if obj_index > 1:
                        out_f.write(',\n')
                    json_blob = json.dumps(output_obj, indent=2)
                    indented_blob = '\n'.join(f"  {line}" for line in json_blob.splitlines())
                    out_f.write(indented_blob)
                    out_f.flush()

                    # Update progress with total objects across all files
                    update_progress(
                        file_index,
                        total_files,
                        obj_index,
                        file_objects,
                        processed_objects_count,
                        total_objects_all_files,
                    )

                out_f.write('\n]\n')

            # Update progress to show 100% completion for the current file
            update_progress(file_index, total_files, file_objects, file_objects, processed_objects_count, total_objects_all_files)

            # Add the filename to the processed_files list
            logger.debug(f"Current processed_files before adding: {self.processed_files}")

            # Use just the filename (no path) to ensure consistency
            simple_filename = filename  # Just the filename without the path

            # Ensure we're only adding a string (filename) to the processed_files list
            if not isinstance(simple_filename, str):
                logger.warning(f"Attempted to add non-string item to processed_files: {simple_filename}, converting to string")
                simple_filename = str(simple_filename)

            # Check if the file is already in the processed_files list
            if simple_filename not in self.processed_files:
                # Add the file to the processed_files list
                self.processed_files.append(simple_filename)
                logger.info(f"Added {simple_filename} to processed files list")
            else:
                logger.debug(f"File {simple_filename} already in processed_files list")

            # Log the current processed_files list at debug level only
            logger.debug(f"Current processed_files after adding: {self.processed_files}")
            logger.info(f"Completed processing file {filename}")

        # Make sure progress shows 100% when completed
        if total_files > 0:
            update_progress(total_files, total_files, 1, 1, total_objects_all_files, total_objects_all_files)

        # Set processing flag to false when done
        self.is_processing = False
        logger.info("All files processed successfully")

    def extract_function_vulnerability(self, function_analysis_text: Union[str, Dict[str, Any]]) -> Optional[int]:
        """
        Extract function vulnerability decision from function_analysis JSON.

        Args:
            function_analysis_text: The function analysis text or JSON object.

        Returns:
            1 if vulnerable, 0 if not vulnerable, None if unclear/needs manual decision.
        """
        # Handle None or empty input
        if not function_analysis_text:
            logger.warning("Empty function_analysis_text provided")
            return None

        # Only use JSON parsing for automatic vulnerability detection
        return self._extract_from_json(function_analysis_text)

    def _extract_from_json(self, function_analysis_text: Union[str, Dict[str, Any]]) -> Optional[int]:
        """
        Extract vulnerability decision from JSON object or string.

        Args:
            function_analysis_text: The function analysis text or JSON object.

        Returns:
            1 if vulnerable, 0 if not vulnerable, None if unclear or not JSON.
        """
        # If it's already a dictionary
        if isinstance(function_analysis_text, dict):
            try:
                # Direct check for boolean values
                if 'is_function_vulnerable' in function_analysis_text:
                    value = function_analysis_text['is_function_vulnerable']

                    # Handle boolean values directly
                    if isinstance(value, bool):
                        return 1 if value else 0

                    # Handle string values
                    if isinstance(value, str):
                        value_lower = value.lower()
                        if value_lower == 'true' or value_lower == 'yes' or value_lower == 'vulnerable':
                            return 1  # Return 1 for vulnerable
                        elif (value_lower == 'false' or value_lower == 'no' or
                              'not vulnerable' in value_lower or 'not_vulnerable' in value_lower):
                            return 0  # Return 0 for not vulnerable

                    # Handle numeric values
                    if isinstance(value, (int, float)):
                        return 1 if value > 0 else 0

                    # If we get here, the value exists but is in an unclear format
                    logger.warning(f"Unclear vulnerability state in JSON dict: '{value}', requiring manual analysis")
            except Exception as e:
                logger.warning(f"Error processing function_analysis dict: {e}")

        # If it's a string, try to parse as JSON
        elif isinstance(function_analysis_text, str):
            try:
                # First try direct JSON parsing
                try:
                    analysis_data = json.loads(function_analysis_text)
                    return self._extract_from_json(analysis_data)
                except json.JSONDecodeError:
                    # If direct parsing fails, try with fixes
                    pass

                # Try to fix common JSON formatting issues before parsing
                fixed_text = self._fix_json_formatting(function_analysis_text)

                # Try to parse the fixed JSON
                analysis_data = json.loads(fixed_text)

                # Recursively call with the parsed dictionary
                return self._extract_from_json(analysis_data)
            except json.JSONDecodeError as e:
                # If JSON parsing fails, try one more approach with escaped characters
                try:
                    # Handle escaped newlines and other special characters
                    # This is specifically for cases like: "{\n  \"is_function_vulnerable\": \"not vulnerable\",\n  ...}"
                    cleaned_text = function_analysis_text.replace('\\n', ' ').replace('\\t', ' ')
                    analysis_data = json.loads(cleaned_text)
                    return self._extract_from_json(analysis_data)
                except json.JSONDecodeError:
                    # If all JSON parsing attempts fail, require manual analysis
                    logger.warning(f"JSON parsing failed for: {function_analysis_text[:100]}..., requiring manual analysis")
            except Exception as e:
                # Log other errors and require manual analysis
                logger.warning(f"Error processing function_analysis JSON string: {e}, requiring manual analysis")

        # If we couldn't extract from JSON, return None to require manual decision
        return None

    def _fix_json_formatting(self, json_text: str) -> str:
        """
        Fix common JSON formatting issues.

        Args:
            json_text: The JSON text to fix.

        Returns:
            Fixed JSON text.
        """
        # Replace single quotes with double quotes
        fixed_text = json_text.replace("'", '"')

        # Fix trailing commas in objects and arrays
        fixed_text = re.sub(r',\s*}', '}', fixed_text)
        fixed_text = re.sub(r',\s*\]', ']', fixed_text)

        # Fix missing quotes around keys
        fixed_text = re.sub(r'([{,])\s*(\w+)\s*:', r'\1"\2":', fixed_text)

        # Handle escaped newlines and other special characters
        fixed_text = fixed_text.replace('\\n', ' ').replace('\\t', ' ')

        return fixed_text


# Create a singleton instance
json_processor = JSONProcessor()

# Create aliases for commonly used methods
process_json_files = json_processor.process_json_files
get_current_object = json_processor.get_current_object
set_user_decision = json_processor.set_user_decision
get_current_filename = json_processor.get_current_filename
get_processed_status = json_processor.get_processed_status
reset_processing_state = json_processor.reset_processing_state
get_decision_context = json_processor.get_decision_context
