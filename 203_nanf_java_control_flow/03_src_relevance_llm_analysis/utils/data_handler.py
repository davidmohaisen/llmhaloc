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
from .llm_processor import sanitize_model_name

# Initialize logger
logger = Logger()


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
            # Read the first character to verify it's an array
            first_char = file.read(1)
            if first_char != '[':
                raise ValueError(f"JSON file {file_path} is not an array (doesn't start with '[')")

            # Reset file position
            file.seek(0)

            # Create a JSON decoder
            decoder = json.JSONDecoder()

            # Skip the opening bracket and any whitespace
            content = file.read()
            idx = content.find('[') + 1
            content = content[idx:].lstrip()

            # Keep track of objects yielded
            count = 0

            # Parse objects until we reach the end of the array
            while content:
                try:
                    # Decode one object at a time
                    obj, idx = decoder.raw_decode(content)
                    yield obj
                    count += 1

                    # Move past the object and any whitespace/comma
                    content = content[idx:].lstrip()
                    if content.startswith(','):
                        content = content[1:].lstrip()

                    # If we've reached the end of the array, break
                    if content.startswith(']'):
                        break
                except json.JSONDecodeError as e:
                    # If we can't decode any more objects, we're done
                    if "Expecting value" in str(e) and content.strip().startswith(']'):
                        break
                    raise

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


def write_to_json(new_entry, model_name, result_dir, input_file):
    """
    Writes a new JSON object to a file based on the model name and input file.
    Uses an efficient append method that doesn't read the entire file into memory.

    Args:
        new_entry (dict): The new JSON object to write.
        model_name (str): Model name, used to determine the filename.
        result_dir (str): Directory to save results.
        input_file (str): Path to the input file.
    """
    entry_id = new_entry.get('id', 'Unknown')
    sub_id = new_entry.get('sub_id', 'Unknown')
    code_id = new_entry.get('code_id', 'Unknown')

    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
        logger.info(f"Created directory {result_dir}")

    # Generate output filename based on input file and model
    filepath = get_output_filename(input_file, model_name, result_dir)

    try:
        # Convert the new entry to a JSON string
        entry_json = json.dumps(new_entry, indent=4)

        # If file doesn't exist or is empty, create it with a new JSON array
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            with open(filepath, 'w') as file:
                file.write('[\n')
                file.write(entry_json)
                file.write('\n]')
        else:
            # File exists and has content, append to the JSON array
            with open(filepath, 'r+') as file:
                # Move to the second-to-last character (before the closing bracket)
                file.seek(0, os.SEEK_END)
                position = file.tell() - 1

                # Make sure we're at the closing bracket
                file.seek(position)
                if file.read(1) != ']':
                    raise ValueError(f"Invalid JSON array format in {filepath}")

                # Move back to before the closing bracket
                file.seek(position)

                # Check if we need to add a comma by looking for content between [ and ]
                file.seek(0)
                first_char = file.read(1)
                if first_char != '[':
                    raise ValueError(f"Invalid JSON array format in {filepath} - should start with '['")

                # Go back to position before the closing bracket and read backwards to find content
                file.seek(position - 1)
                char = file.read(1)
                # If the character before ] is not [, then the array has content and needs a comma
                needs_comma = char != '['

                # Move back to position before closing bracket
                file.seek(position)

                # Write comma if needed, then the new entry, then the closing bracket
                if needs_comma:
                    file.write(',\n')
                else:
                    file.write('\n')
                file.write(entry_json)
                file.write('\n]')

                # Truncate the file at the current position
                file.truncate()

        # Log with file information
        logger.info(f"Appended data for {model_name} - File: {os.path.basename(input_file)} - ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}")
    except Exception as e:
        logger.error(f"Error writing data for {model_name} - File: {os.path.basename(input_file)} - ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}: {e}")
        raise


def get_resume_point_file_path(model_name, log_dir):
    """
    Gets the path to the resume point file for a given model.

    Args:
        model_name (str): Name of the model
        log_dir (str): Directory for log files

    Returns:
        str: Path to the resume point file
    """
    resume_dir = os.path.join(log_dir, "resume_points")
    if not os.path.exists(resume_dir):
        os.makedirs(resume_dir)
        logger.info(f"Created resume points directory: {resume_dir}")

    filename = f"{sanitize_model_name(model_name)}_resume.json"
    return os.path.join(resume_dir, filename)


def save_resume_point(model_name, entry, index, total, log_dir, time_estimates=None):
    """
    Saves the current processing point to a dedicated JSON file.

    Args:
        model_name (str): Name of the model
        entry (dict): The current entry being processed
        index (int): Current index in the dataset
        total (int): Total number of entries in the dataset
        log_dir (str): Directory for log files
        time_estimates (dict, optional): Time estimation data
    """
    resume_file = get_resume_point_file_path(model_name, log_dir)

    # Create resume point data
    resume_data = {
        "model_name": model_name,
        "last_processed": {
            "id": entry.get('id'),
            "sub_id": entry.get('sub_id'),
            "code_id": entry.get('code_id')
        },
        "index": index,
        "total": total,
        "progress_percentage": round((index / total) * 100, 2),
        "completed": (index >= total),
        "timestamp": datetime.now().isoformat()
    }

    # Add time estimates if provided
    if time_estimates:
        resume_data["time_estimates"] = time_estimates

    try:
        with open(resume_file, 'w') as file:
            json.dump(resume_data, file, indent=2)
        logger.debug(f"Saved resume point for {model_name} at index {index}/{total}")
    except Exception as e:
        logger.error(f"Error saving resume point for {model_name}: {e}")


def get_last_processed_entry(model_name, _result_dir, log_dir=None):
    """
    Gets the last successfully processed entry for a given model.
    Only checks the dedicated resume point file, no fallback to results file.

    Args:
        model_name (str): Name of the model to check
        _result_dir (str): Directory containing result files (unused, kept for API compatibility)
        log_dir (str, optional): Directory for log files. If None, will return None.

    Returns:
        tuple: (id, sub_id, code_id) of last processed entry, or None if no file exists
    """
    # Only try to get from resume point file if log_dir is provided
    if log_dir:
        resume_file = get_resume_point_file_path(model_name, log_dir)
        try:
            if os.path.exists(resume_file) and os.path.getsize(resume_file) > 0:
                with open(resume_file, 'r') as file:
                    resume_data = json.load(file)
                    last_processed = resume_data.get('last_processed', {})
                    if all(key in last_processed for key in ['id', 'sub_id', 'code_id']):
                        logger.info(f"Found resume point for {model_name} in dedicated file")
                        return (
                            last_processed.get('id'),
                            last_processed.get('sub_id'),
                            last_processed.get('code_id')
                        )
        except Exception as e:
            logger.warning(f"Error reading resume point file for {model_name}: {e}")

    # No fallback to results file anymore
    logger.info(f"No resume point found for {model_name}, starting from beginning")
    return None


def get_resume_data(model_name, log_dir):
    """
    Gets the resume data for a model from the dedicated resume point file.

    Args:
        model_name (str): Name of the model
        log_dir (str): Directory for log files

    Returns:
        dict: Resume data or None if not found
    """
    resume_file = get_resume_point_file_path(model_name, log_dir)
    try:
        if os.path.exists(resume_file) and os.path.getsize(resume_file) > 0:
            with open(resume_file, 'r') as file:
                return json.load(file)
    except Exception as e:
        logger.warning(f"Error reading resume data for {model_name}: {e}")

    return None


def is_model_completed(model_name, _ori_json_data, _result_dir, log_dir=None):
    """
    Checks if a model has completed processing all entries.
    Only checks the dedicated resume point file.

    Args:
        model_name (str): Name of the model to check
        _ori_json_data (list): Original JSON data (unused, kept for API compatibility)
        _result_dir (str): Directory containing result files (unused, kept for API compatibility)
        log_dir (str, optional): Directory for log files

    Returns:
        bool: True if model has completed processing all entries
    """
    # Only check the resume point file if log_dir is provided
    if log_dir:
        resume_data = get_resume_data(model_name, log_dir)
        if resume_data and "completed" in resume_data:
            completed = resume_data["completed"]
            if completed:
                logger.info(f"Model {model_name} is marked as completed in resume file")
            return completed

    # No fallback to checking the last processed entry
    return False


def find_resume_point(model_name, ori_json_data, _result_dir, log_dir=None):
    """
    Finds the index to resume processing from.
    Only checks the dedicated resume point file.

    Args:
        model_name (str): Name of the model
        ori_json_data (list): Original JSON data (used only for length validation)
        _result_dir (str): Directory containing result files (unused, kept for API compatibility)
        log_dir (str, optional): Directory for log files

    Returns:
        int: Index to resume from, or 0 if starting fresh
    """
    # Only check the resume point file if log_dir is provided
    if log_dir:
        resume_data = get_resume_data(model_name, log_dir)
        if resume_data and "index" in resume_data:
            index = resume_data["index"]
            # Ensure the index is valid
            if 0 <= index <= len(ori_json_data):
                logger.info(f"Resuming {model_name} from index {index} based on resume file")
                return index

    # No fallback to searching based on the last processed entry
    logger.info(f"No valid resume point found for {model_name}, starting from beginning")
    return 0


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


def get_output_filename(input_file, model_name, output_dir):
    """
    Generate an output filename based on the input file.
    Uses the exact same filename as the input file.

    Args:
        input_file (str): Path to the input file
        model_name (str): Name of the model (not used, kept for API compatibility)
        output_dir (str): Directory to save output

    Returns:
        str: Path to the output file
    """
    # Extract just the filename without the path
    filename = os.path.basename(input_file)

    # Use the exact same filename as the input file
    return os.path.join(output_dir, filename)


def get_file_resume_point_path(input_file, model_name, log_dir):
    """
    Get the path to the file resume point file.

    Args:
        input_file (str): Path to the input file
        model_name (str): Name of the model
        log_dir (str): Directory for log files

    Returns:
        str: Path to the file resume point file
    """
    resume_dir = os.path.join(log_dir, "file_resume_points")
    if not os.path.exists(resume_dir):
        os.makedirs(resume_dir)
        logger.info(f"Created file resume points directory: {resume_dir}")

    # Create a unique filename based on the input file and model
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    filename = f"{base_name}_{sanitize_model_name(model_name)}_resume.json"

    return os.path.join(resume_dir, filename)


def save_file_resume_point(input_file, model_name, entry_idx, total_entries, log_dir):
    """
    Save the current processing state for a file.

    Args:
        input_file (str): Path to the input file
        model_name (str): Name of the model
        entry_idx (int): Current entry index
        total_entries (int): Total number of entries in the file
        log_dir (str): Directory for log files

    Returns:
        bool: True if the resume point was saved successfully
    """
    resume_file = get_file_resume_point_path(input_file, model_name, log_dir)

    # Create resume data
    resume_data = {
        "file_path": input_file,
        "file_name": os.path.basename(input_file),
        "model_name": model_name,
        "entry_index": entry_idx,
        "total_entries": total_entries,
        "progress_percentage": round((entry_idx / total_entries) * 100, 2),
        "completed": (entry_idx >= total_entries),
        "timestamp": datetime.now().isoformat()
    }

    try:
        with open(resume_file, 'w') as file:
            json.dump(resume_data, file, indent=2)
        logger.debug(f"Saved resume point for file {os.path.basename(input_file)} at entry {entry_idx}/{total_entries}")
        return True
    except Exception as e:
        logger.error(f"Error saving resume point for file {os.path.basename(input_file)}: {e}")
        return False


def get_file_resume_point(input_file, model_name, log_dir):
    """
    Get the resume point for a file.

    Args:
        input_file (str): Path to the input file
        model_name (str): Name of the model
        log_dir (str): Directory for log files

    Returns:
        int: Entry index to resume from, or 0 if no resume point exists
    """
    resume_file = get_file_resume_point_path(input_file, model_name, log_dir)

    try:
        if os.path.exists(resume_file) and os.path.getsize(resume_file) > 0:
            with open(resume_file, 'r') as file:
                resume_data = json.load(file)
                entry_idx = resume_data.get('entry_index', 0)
                total_entries = resume_data.get('total_entries', 0)

                # Validate the resume point
                if entry_idx > 0 and entry_idx < total_entries:
                    logger.info(f"Found resume point for file {os.path.basename(input_file)} at entry {entry_idx}/{total_entries}")
                    return entry_idx
                elif entry_idx >= total_entries:
                    logger.info(f"File {os.path.basename(input_file)} is already fully processed")
                    return total_entries
    except Exception as e:
        logger.warning(f"Error reading resume point for file {os.path.basename(input_file)}: {e}")

    logger.info(f"No valid resume point found for file {os.path.basename(input_file)}, starting from beginning")
    return 0


def is_file_processed(input_file, model_name, output_dir, log_dir=None):
    """
    Check if a file has already been processed by a model.

    Args:
        input_file (str): Path to the input file
        model_name (str): Name of the model
        output_dir (str): Directory containing output files
        log_dir (str, optional): Directory for log files

    Returns:
        bool: True if the file has been processed
    """
    # First check the resume point if log_dir is provided
    if log_dir:
        resume_file = get_file_resume_point_path(input_file, model_name, log_dir)
        try:
            if os.path.exists(resume_file) and os.path.getsize(resume_file) > 0:
                with open(resume_file, 'r') as file:
                    resume_data = json.load(file)
                    if resume_data.get('completed', False):
                        logger.info(f"File {os.path.basename(input_file)} is marked as completed in resume file")
                        return True
        except Exception as e:
            logger.warning(f"Error checking resume file for {os.path.basename(input_file)}: {e}")

    # Then check the output file (using the same filename as input)
    output_file = get_output_filename(input_file, model_name, output_dir)

    # Check if the output file exists and has content
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        try:
            # Load the output file to check if it's valid JSON
            with open(output_file, 'r') as f:
                data = json.load(f)
                if data:  # If the file has content
                    # Count the entries in the output file
                    if isinstance(data, list) and len(data) > 0:
                        # If we have log_dir, we can compare with the total entries
                        if log_dir:
                            resume_file = get_file_resume_point_path(input_file, model_name, log_dir)
                            if os.path.exists(resume_file) and os.path.getsize(resume_file) > 0:
                                with open(resume_file, 'r') as file:
                                    resume_data = json.load(file)
                                    total_entries = resume_data.get('total_entries', 0)
                                    if total_entries > 0 and len(data) >= total_entries:
                                        logger.info(f"File {os.path.basename(input_file)} has all {total_entries} entries processed")
                                        return True
                        else:
                            # Without log_dir, just check if there's content
                            logger.info(f"File {os.path.basename(input_file)} has been processed by {model_name}")
                            return True
        except Exception as e:
            logger.warning(f"Error checking processed status for {output_file}: {e}")
            return False

    return False


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
