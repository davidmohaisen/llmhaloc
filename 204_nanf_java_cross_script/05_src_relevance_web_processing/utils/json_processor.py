"""
JSON Processing Utility for the LLM Vulnerability Function Localization Web Processing System.

"""

import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Union

from utils.config_manager import config


class JsonProcessor:
    """
    Class to handle JSON file processing operations.
    """

    def __init__(self):
        self.current_object = None
        self.user_decision = None
        self.current_filename = None
        self.processed_objects = []
        self.processing_paused = threading.Event()
        self.stop_processing = threading.Event()
        self.is_processing = False
        self.logger = logging.getLogger(__name__)

        # Create output directory if it doesn't exist
        output_dir = config.get_output_dir()
        os.makedirs(output_dir, exist_ok=True)

    def _normalize_decision(self, decision: Union[int, bool, str]) -> Union[int, str]:
        """
        Normalize a decision value to an integer when possible.

        Args:
            decision: The user's decision (True/False/-1/1/0)

        Returns:
            Normalized decision value
        """
        if decision is True:
            return 1
        if decision is False:
            return 0
        try:
            return int(decision)
        except (TypeError, ValueError):
            return decision

    def get_current_object(self) -> Optional[Dict[str, Any]]:
        """
        Get the current object being processed.

        Returns:
            The current JSON object or None
        """
        # No logging here to reduce noise
        return self.current_object

    def get_current_filename(self) -> Optional[str]:
        """
        Get the current filename being processed.

        Returns:
            The current filename or None
        """
        # No logging here to reduce noise
        return self.current_filename

    def set_user_decision(self, decision: Union[int, bool, str]) -> None:
        """
        Set the user's decision for the current object.

        Args:
            decision: The user's decision (True/False/-1)
        """
        # Get current object identifiers for better logging context
        obj = self.current_object
        if obj:
            obj_id = obj.get("id", "unknown")
            sub_id = obj.get("sub_id", "unknown")
            code_id = obj.get("code_id", "unknown")
            id_info = f"ID={obj_id}, Sub ID={sub_id}, Code ID={code_id}"
            stage = obj.get("review_stage", 1)
        else:
            id_info = "unknown object"
            stage = "unknown"

        normalized_decision = self._normalize_decision(decision)
        if isinstance(normalized_decision, (int, bool)):
            decision_str = self._get_result_description(normalized_decision)
        else:
            decision_str = str(normalized_decision)

        self.logger.info(
            f"Setting user decision for {id_info} (stage {stage}) to: {decision_str}"
        )
        self.user_decision = normalized_decision
        self.processing_paused.set()  # Resume processing
        self.logger.info(f"User decision set successfully for {id_info}")

    def get_processed_status(self) -> List[Dict[str, Any]]:
        """
        Get the status of recently processed objects.

        Returns:
            List of processed object IDs with all identifiers
        """
        max_history = config.get_max_displayed_history()
        processed_info = []

        # Get the most recent objects up to max_history
        recent_objects = (
            self.processed_objects[-max_history:] if self.processed_objects else []
        )

        for obj in recent_objects:
            # Ensure all identifiers are included
            processed_info.append(
                {
                    "id": obj.get("id", "unknown"),
                    "sub_id": obj.get("sub_id", "unknown"),
                    "code_id": obj.get("code_id", "unknown"),
                }
            )

        self.logger.debug(
            f"Returning status for {len(processed_info)} recently processed objects"
        )
        return processed_info

    def process_json_files(self, input_dir: str, output_dir: str) -> None:
        """
        Process all JSON files in the input directory.

        Args:
            input_dir: Path to the input directory
            output_dir: Path to the output directory
        """
        self.logger.info(f"Starting to process JSON files from {input_dir}")

        # Reset stop flag and set processing flag
        self.stop_processing.clear()
        self.is_processing = True

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        json_files = sorted([f for f in os.listdir(input_dir) if f.endswith(".json")])
        total_files = len(json_files)
        self.logger.info(f"Found {total_files} JSON files to process")

        for file_index, filename in enumerate(json_files, 1):
            # Check if processing should stop
            if self.stop_processing.is_set():
                self.logger.info("Processing stopped by user request")
                self.is_processing = False
                return

            self.current_filename = filename
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)

            self.logger.info(f"Processing file {file_index}/{total_files}: {filename}")

            try:
                with open(input_path, "r") as f:
                    data = json.load(f)

                total_objects = len(data)
                for obj_index, obj in enumerate(data, 1):
                    # Check if processing should stop
                    if self.stop_processing.is_set():
                        self.logger.info("Processing stopped by user request")
                        self.is_processing = False
                        return

                    self.current_object = obj
                    # Get all identifiers
                    obj_id = obj.get("id", "unknown")
                    sub_id = obj.get("sub_id", "unknown")
                    code_id = obj.get("code_id", "unknown")

                    # Log with all identifiers
                    self.logger.debug(
                        f"Processing object {obj_index}/{total_objects} from file {filename} - ID={obj_id}, Sub ID={sub_id}, Code ID={code_id}"
                    )
                    self._process_json_object(obj)

                    # Get all identifiers for consistent logging
                    obj_id = obj.get("id", "unknown")
                    sub_id = obj.get("sub_id", "unknown")
                    code_id = obj.get("code_id", "unknown")
                    id_info = f"ID={obj_id}, Sub ID={sub_id}, Code ID={code_id}"

                    while obj.get("relevance_label") is None:
                        stage = obj.get("review_stage", 1)
                        if self.user_decision is None:
                            self.processing_paused.clear()  # Pause processing
                            self.logger.info(
                                f"Waiting for user decision (stage {stage}) on object: {id_info}"
                            )

                            while not self.processing_paused.is_set():
                                # Check for stop signal while waiting
                                if self.stop_processing.is_set():
                                    self.logger.info(
                                        f"Processing stopped while waiting for user decision on object: {id_info}"
                                    )
                                    self.is_processing = False
                                    return
                                time.sleep(0.1)  # Wait for user decision
                        else:
                            self.logger.info(
                                f"Using queued decision (stage {stage}) for object: {id_info}"
                            )
                            self.processing_paused.clear()

                        decision_value = self.user_decision
                        self.user_decision = None
                        if decision_value is None:
                            self.logger.warning(
                                f"Received empty decision for object {id_info}; waiting again"
                            )
                            continue

                        self._apply_user_decision(obj, decision_value, id_info)

                    self.processed_objects.append(
                        {
                            "id": obj["id"],
                            "sub_id": obj.get("sub_id", ""),
                            "code_id": obj.get("code_id", ""),
                        }
                    )

                    # Remove internal fields before writing to output
                    self._strip_internal_fields(obj)

                    # Persist progress after each processed object
                    self._write_output_snapshot(data, output_path, id_info)

                    # Notify progress listeners
                    self._notify_progress(
                        file_index, total_files, obj_index, total_objects
                    )

                with open(output_path, "w") as f:
                    json.dump(data, f, indent=2)

                self.logger.info(f"Completed processing file {filename}")

            except Exception as e:
                self.logger.error(f"Error processing file {filename}: {str(e)}")

        # Processing completed successfully
        self.is_processing = False
        self.logger.info("All files processed successfully")

    def _process_json_object(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single JSON object.

        Args:
            obj: The JSON object to process

        Returns:
            The processed JSON object
        """
        # Get all identifiers for consistent logging
        obj_id = obj.get("id", "unknown")
        sub_id = obj.get("sub_id", "unknown")
        code_id = obj.get("code_id", "unknown")
        id_info = f"ID={obj_id}, Sub ID={sub_id}, Code ID={code_id}"

        self.logger.debug(f"Processing object with {id_info}")

        result = self._extract_result(obj.get("relevance_analysis", ""))
        obj["analysis_label"] = result
        obj["analysis_label_parsed"] = result is not None
        obj["review_stage"] = 1
        obj["review_reason"] = None
        obj["relevance_label"] = None
        obj["user_decision_round1"] = None
        obj["user_decision_round2"] = None

        if result is not None:
            result_str = self._get_result_description(result)
            self.logger.info(f"Parsed relevance analysis for {id_info}: {result_str}")
        else:
            self.logger.info(
                f"Relevance analysis could not be parsed for {id_info}; double review required"
            )

        return obj

    def _apply_user_decision(
        self, obj: Dict[str, Any], decision: Union[int, bool, str], id_info: str
    ) -> None:
        """
        Apply a user decision to the current object and advance review state.

        Args:
            obj: The current JSON object
            decision: The user's decision
            id_info: Identifier information string for logging
        """
        decision_value = self._normalize_decision(decision)
        decision_str = (
            self._get_result_description(decision_value)
            if isinstance(decision_value, (int, bool))
            else str(decision_value)
        )
        stage = obj.get("review_stage", 1)
        analysis_label = obj.get("analysis_label")

        if stage == 1:
            obj["user_decision_round1"] = decision_value
            if analysis_label is not None and decision_value == analysis_label:
                obj["relevance_label"] = decision_value
                obj["review_stage"] = None
                obj["review_reason"] = None
                self.logger.info(f"Consensus reached for {id_info}: {decision_str}")
            else:
                obj["review_stage"] = 2
                obj["review_reason"] = (
                    "mismatch" if analysis_label is not None else "unparsed"
                )
                reason_str = (
                    "mismatch with relevance analysis"
                    if analysis_label is not None
                    else "unparsed relevance analysis"
                )
                self.logger.info(
                    f"Second review required for {id_info} due to {reason_str}"
                )
        else:
            obj["user_decision_round2"] = decision_value
            obj["relevance_label"] = decision_value
            obj["review_stage"] = None
            obj["review_reason"] = None
            self.logger.info(f"Final decision recorded for {id_info}: {decision_str}")

    def _strip_internal_fields(self, obj: Dict[str, Any]) -> None:
        """
        Remove internal fields before writing output.

        Args:
            obj: The JSON object to clean
        """
        fields_to_remove = [
            "relevance_analysis",
            "analysis_label",
            "analysis_label_parsed",
            "review_stage",
            "review_reason",
            "user_decision_round1",
            "user_decision_round2",
        ]
        for field in fields_to_remove:
            obj.pop(field, None)

    def _write_output_snapshot(
        self, data: List[Dict[str, Any]], output_path: str, id_info: str
    ) -> None:
        """
        Write the current output snapshot to disk.

        Args:
            data: The full JSON data list
            output_path: Destination output file path
            id_info: Identifier information string for logging
        """
        temp_path = f"{output_path}.tmp"
        try:
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_path, output_path)
            self.logger.debug(f"Wrote output snapshot after {id_info} to {output_path}")
        except Exception as e:
            self.logger.error(
                f"Failed to write output snapshot after {id_info}: {str(e)}"
            )

    def _get_result_description(self, result: Union[int, bool]) -> str:
        """
        Convert a numeric result to a descriptive string.

        Args:
            result: The numeric result (1, 0, -1, True, False)

        Returns:
            A descriptive string of the result
        """
        if result == 1 or result is True:
            return "vulnerable"
        elif result == 0 or result is False:
            return "not vulnerable"
        elif result == -1:
            return "not relevant"
        else:
            return f"unknown ({result})"

    def _extract_result(self, text: str) -> Optional[Union[bool, int]]:
        """
        Extract the result from the relevance analysis text.

        Args:
            text: The relevance analysis text

        Returns:
            1 for vulnerable, 0 for not vulnerable, -1 for not relevant, None if undetermined
        """
        # Get current object identifiers for better logging context
        obj = self.current_object
        if obj:
            obj_id = obj.get("id", "unknown")
            sub_id = obj.get("sub_id", "unknown")
            code_id = obj.get("code_id", "unknown")
            id_info = f"ID={obj_id}, Sub ID={sub_id}, Code ID={code_id}"
        else:
            id_info = "unknown object"

        if not text:
            self.logger.debug(
                f"Empty text provided for result extraction for {id_info}"
            )
            return None

        # Try JSON parsing only - we prioritize proper JSON parsing
        # and fall back to manual analysis if it fails
        json_result = self._try_json_extraction(text, id_info)

        # If we got a valid result, return it
        if json_result is not None:
            result_str = self._get_result_description(json_result)
            self.logger.info(
                f"Successfully extracted result from JSON for {id_info}: {result_str}"
            )
            return json_result

        # If JSON parsing failed, return None to trigger manual analysis
        # We no longer use regex extraction as it's less reliable
        self.logger.info(
            f"JSON parsing failed for {id_info}, requiring manual analysis"
        )
        return None

    def _try_json_extraction(
        self, text: str, id_info: str = "unknown object"
    ) -> Optional[Union[bool, int]]:
        """
        Try to extract the result by parsing the text as JSON.

        Args:
            text: The text to parse as JSON
            id_info: Identifier information string for logging

        Returns:
            Extracted result or None if parsing failed
        """
        try:
            # First, try to parse the text as JSON
            json_data = json.loads(text)

            # Check if the expected fields exist in the parsed JSON
            if "result" in json_data:
                result = json_data["result"].lower()
                self.logger.info(
                    f"Successfully parsed JSON for {id_info} with result: {result}"
                )

                if result == "vulnerable":
                    return 1
                elif result == "not vulnerable":
                    return 0
                elif result == "not relevant":
                    return -1
                else:
                    self.logger.warning(
                        f"Unknown result value in JSON for {id_info}: {result}"
                    )
                    # Return None to trigger manual analysis for unknown values
                    return None
            else:
                self.logger.warning(
                    f"JSON parsed for {id_info} but 'result' field not found"
                )
                # Return None to trigger manual analysis when required field is missing
                return None

        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse text as JSON for {id_info}: {str(e)}")
            # Return None to trigger manual analysis for JSON parsing failures
            return None
        except Exception as e:
            self.logger.error(
                f"Unexpected error during JSON parsing for {id_info}: {str(e)}"
            )
            # Return None to trigger manual analysis for any other errors
            return None

    def is_currently_processing(self) -> bool:
        """
        Check if processing is currently active.

        Returns:
            True if processing is active, False otherwise
        """
        return self.is_processing

    def request_stop_processing(self) -> None:
        """
        Request to stop the processing thread.
        """
        self.logger.info("Stop processing requested")
        self.stop_processing.set()

    def _notify_progress(
        self, file_index: int, total_files: int, obj_index: int, total_objects: int
    ) -> None:
        """
        Notify progress listeners about the current processing progress.
        This method is meant to be overridden by the UI manager.

        Args:
            file_index: Current file index
            total_files: Total number of files
            obj_index: Current object index
            total_objects: Total number of objects in the current file
        """
        # This method is intentionally empty as it will be monkey-patched
        # by the UI manager in main.py to provide progress updates.
        # The parameters are declared but not used in this implementation
        # because they are required by the overriding method.
        # pylint: disable=unused-argument
        pass


# Create a singleton instance
json_processor = JsonProcessor()
