"""
Data handling utilities for vulnerability function localization.

This module handles loading, saving, and processing data files.
It supports both single file and directory-based processing.

"""

import os
import json
import glob
from datetime import datetime
from .logger import Logger

# Initialize logger
logger = Logger()


def _validate_json_array(file_path, file):
    """
    Validate that a file contains a JSON array.

    Args:
        file_path (str): Path to the file
        file: File object

    Raises:
        ValueError: If the file does not contain a JSON array
    """
    # Read the first character to verify it's an array
    first_char = file.read(1)
    if first_char != '[':
        raise ValueError(f"JSON file {file_path} is not an array (doesn't start with '[')")

    # Reset file position
    file.seek(0)


def _prepare_json_content(file):
    """
    Prepare JSON content for streaming by skipping the opening bracket.

    Args:
        file: File object

    Returns:
        str: JSON content without the opening bracket
    """
    # Read the entire file content
    content = file.read()

    # Skip the opening bracket and any whitespace
    idx = content.find('[') + 1
    return content[idx:].lstrip()


def _decode_next_json_object(content, decoder):
    """
    Decode the next JSON object from the content.

    Args:
        content (str): JSON content
        decoder (json.JSONDecoder): JSON decoder

    Returns:
        tuple: (object, new_content, success)
            - object: Decoded JSON object or None if failed
            - new_content: Remaining content after decoding
            - success: True if decoding was successful, False otherwise
    """
    try:
        # Decode one object at a time
        obj, idx = decoder.raw_decode(content)

        # Move past the object and any whitespace/comma
        new_content = content[idx:].lstrip()
        if new_content.startswith(','):
            new_content = new_content[1:].lstrip()

        return obj, new_content, True
    except json.JSONDecodeError as e:
        # If we can't decode any more objects, we're done
        if "Expecting value" in str(e) and content.strip().startswith(']'):
            return None, "", False
        raise


def stream_json_data(file_path):
    """
    Stream a JSON array file, yielding one object at a time.
    This is a memory-efficient way to process large JSON arrays.

    Args:
        file_path (str): The path to the JSON file to be streamed.

    Yields:
        dict: One JSON object at a time from the array.

    Raises:
        FileNotFoundError: If the JSON file does not exist at the specified path.
        json.JSONDecodeError: If the file is not a valid JSON.
        ValueError: If the JSON is not an array.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # Validate that the file contains a JSON array
            _validate_json_array(file_path, file)

            # Create a JSON decoder
            decoder = json.JSONDecoder()

            # Prepare content for streaming
            content = _prepare_json_content(file)

            # Keep track of objects yielded
            count = 0

            # Parse objects until we reach the end of the array
            while content:
                # Decode the next object
                obj, content, success = _decode_next_json_object(content, decoder)

                if not success:
                    break

                yield obj
                count += 1

                # If we've reached the end of the array, break
                if content.startswith(']'):
                    break

            logger.info(f"Successfully streamed {count} objects from {file_path}")
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"An error occurred while streaming {file_path}: {e}")
        raise


def load_json_data(file_path):
    """
    Load and parse a JSON file into a Python list.
    This function now uses stream_json_data internally for memory efficiency,
    but still returns the full list for backward compatibility.

    Args:
        file_path (str): The path to the JSON file to be loaded.

    Returns:
        list: A list containing the parsed JSON data.

    Raises:
        FileNotFoundError: If the JSON file does not exist at the specified path.
        json.JSONDecodeError: If the file is not a valid JSON.
    """
    try:
        # Use the streaming function but collect all objects into a list
        data = list(stream_json_data(file_path))
        logger.info(f"Successfully loaded {len(data)} entries from {file_path}")
        return data
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"An error occurred while loading {file_path}: {e}")
        raise


# This function has been removed as it's no longer used in the new system


# This function has been removed as it's no longer used in the new system


# This function has been removed as it's no longer used in the new system


# This function has been removed as it's no longer used in the new system


# This function has been removed as it's no longer used in the new system


# This function has been removed as it's no longer used in the new system


# This function has been removed as it's no longer used in the new system


def list_json_files(directory):
    """
    List all JSON files in a directory.

    Args:
        directory (str): Path to the directory to scan

    Returns:
        list: List of JSON file paths
    """
    if not os.path.exists(directory):
        logger.error(f"Directory not found: {directory}")
        return []

    try:
        # Get all JSON files in the directory
        json_files = glob.glob(os.path.join(directory, "*.json"))
        logger.info(f"Found {len(json_files)} JSON files in {directory}")
        return json_files
    except Exception as e:
        logger.error(f"Error listing JSON files in {directory}: {e}")
        return []


def get_output_filename(input_file, output_dir):
    """
    Generate an output filename based on the input file.
    Uses the exact same filename as the input file.

    Args:
        input_file (str): Path to the input file
        output_dir (str): Directory to save output

    Returns:
        str: Path to the output file
    """
    # Extract just the filename without the path
    filename = os.path.basename(input_file)

    # Use the exact same filename as the input file
    return os.path.join(output_dir, filename)


# This function has been removed as it's no longer used in the new system


# This function has been removed as it's no longer used in the new system


# This function has been removed as it's no longer used in the new system


# This function has been removed as it's no longer used in the new system


def ensure_directories(config):
    """
    Ensure all required directories exist.

    Args:
        config (dict): Configuration dictionary containing directory paths
    """
    directories = [
        config['output']['log_dir'],
        config['output']['result_dir'],
        config['data']['input_dir']
    ]

    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")


def _load_output_data(output_file):
    """
    Load data from an output file.

    Args:
        output_file (str): Path to the output file

    Returns:
        list or None: List of output entries if successful, None otherwise
    """
    try:
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            return None

        with open(output_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading output file {output_file}: {e}")
        return None


def _extract_entry_keys(entries):
    """
    Extract unique identifier keys from a list of entries.

    Args:
        entries (list): List of entries

    Returns:
        set: Set of unique identifier keys
    """
    return {
        (entry['id'], entry['sub_id'], entry['code_id'], entry['function_id'])
        for entry in entries
    }


def _compare_entry_keys(output_keys, ground_truth_keys):
    """
    Compare output keys with ground truth keys.

    Args:
        output_keys (set): Set of output entry keys
        ground_truth_keys (set): Set of ground truth entry keys

    Returns:
        bool: True if the keys match, False otherwise
    """
    return output_keys == ground_truth_keys


def is_fully_processed(output_file, ground_truth_data, log_dir=None, file_name=None):
    """
    Check if output file contains all functions from ground truth.

    This function first checks for a resume point file in the logs directory.
    If found and marked as completed, it returns True. Otherwise, it falls
    back to the legacy method of comparing output data with ground truth.

    Args:
        output_file (str): Path to the output file
        ground_truth_data (list): List of ground truth entries
        log_dir (str, optional): Directory for log files
        file_name (str, optional): Name of the file being processed

    Returns:
        bool: True if the output file contains all functions from ground truth
    """
    # First try to use the resume state if log_dir and file_name are provided
    if log_dir and file_name:
        from .resume_manager import ResumeState
        resume_state = ResumeState(log_dir)
        if resume_state.load_state(file_name) and resume_state.is_file_completed():
            logger.info(f"Resume state for {file_name} indicates processing is complete")
            return True

    # Fall back to legacy method if resume state not found, not marked as completed,
    # or parameters not provided
    logger.info("No completed resume state found, falling back to output file analysis")

    # Load output data
    output_data = _load_output_data(output_file)
    if output_data is None:
        return False

    # Check if the number of entries matches
    if len(output_data) != len(ground_truth_data):
        return False

    # Extract and compare keys
    output_keys = _extract_entry_keys(output_data)
    ground_truth_keys = _extract_entry_keys(ground_truth_data)

    return _compare_entry_keys(output_keys, ground_truth_keys)

def _get_entry_identifier(entry):
    """
    Get a string identifier for an entry.

    Args:
        entry (dict): Entry to get identifier for

    Returns:
        str: String identifier for the entry
    """
    return f"ID:{entry.get('id', 'Unknown')}, Sub_ID:{entry.get('sub_id', 'Unknown')}, " \
           f"Code_ID:{entry.get('code_id', 'Unknown')}, Function_ID:{entry.get('function_id', 'Unknown')}"


def _load_existing_data(output_file):
    """
    Load existing data from an output file.

    Args:
        output_file (str): Path to the output file

    Returns:
        list: List of existing entries, or empty list if file doesn't exist
    """
    data = []
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        try:
            with open(output_file, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {output_file}: {e}")
        except Exception as e:
            logger.error(f"Error loading data from {output_file}: {e}")

    return data


def _write_data_to_file(output_file, data):
    """
    Write data to an output file.

    Args:
        output_file (str): Path to the output file
        data (list): Data to write

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error writing data to {output_file}: {e}")
        return False


def append_to_output(output_file, entry):
    """
    Append a single entry to the output JSON file.
    If file doesn't exist or is empty, create new file with list.
    If exists, load, append, and write back.
    This matches the approach used in the archived main script.

    Args:
        output_file (str): Path to the output file
        entry (dict): Entry to append

    Returns:
        bool: True if the entry was appended successfully
    """
    try:
        # Get entry identifier for logging
        entry_id = _get_entry_identifier(entry)

        # Load existing data
        data = _load_existing_data(output_file)

        # Append new entry
        data.append(entry)

        # Write data back to file
        if _write_data_to_file(output_file, data):
            logger.info(f"Successfully appended entry ({entry_id}) to {output_file}")
            return True
        else:
            logger.error(f"Failed to write data to {output_file} for entry ({entry_id})")
            return False

    except Exception as e:
        # Get entry identifier for logging
        entry_id = _get_entry_identifier(entry)
        logger.error(f"Error appending entry ({entry_id}) to {output_file}: {e}")
        return False
