"""
Data handling utilities for vulnerability function localization.

This module handles loading, saving, and processing data files.

"""

import os
import json
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


def write_to_json(new_entry, model_name, result_dir):
    """
    Writes a new JSON object to a file based on the model name.
    Uses an efficient append method that doesn't read the entire file into memory.

    Args:
        new_entry (dict): The new JSON object to write.
        model_name (str): Model name, used to determine the filename.
        result_dir (str): Directory to save results
    """
    entry_id = new_entry.get('id', 'Unknown')
    sub_id = new_entry.get('sub_id', 'Unknown')
    code_id = new_entry.get('code_id', 'Unknown')

    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
        logger.info(f"Created directory {result_dir}")

    filename = sanitize_model_name(model_name) + '.json'
    filepath = os.path.join(result_dir, filename)

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

        logger.info(f"Appended data for {model_name} - ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}")
    except Exception as e:
        logger.error(f"Error writing data for {model_name} - ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}: {e}")
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


def save_resume_point(model_name, entry, index, total, log_dir, time_estimates=None, failed_entries=None):
    """
    Saves the current processing point to a dedicated JSON file.

    Args:
        model_name (str): Name of the model
        entry (dict): The current entry being processed
        index (int): Current index in the dataset
        total (int): Total number of entries in the dataset
        log_dir (str): Directory for log files
        time_estimates (dict, optional): Time estimation data
        failed_entries (list, optional): List of entries that failed processing
    """
    resume_file = get_resume_point_file_path(model_name, log_dir)

    # Try to load existing resume data to preserve failed entries
    existing_failed_entries = []
    try:
        if os.path.exists(resume_file) and os.path.getsize(resume_file) > 0:
            with open(resume_file, 'r') as file:
                existing_data = json.load(file)
                if "failed_entries" in existing_data:
                    existing_failed_entries = existing_data["failed_entries"]
    except Exception:
        # If we can't read the file, just continue with empty failed entries
        pass

    # If we have new failed entries, add them to the existing ones
    if failed_entries:
        # Create a set of unique failed entries based on id, sub_id, and code_id
        unique_entries = {(entry.get('id'), entry.get('sub_id'), entry.get('code_id')): entry
                         for entry in existing_failed_entries}

        for failed_entry in failed_entries:
            key = (failed_entry.get('id'), failed_entry.get('sub_id'), failed_entry.get('code_id'))
            if key in unique_entries:
                # Update retry count if entry already exists
                existing_entry = unique_entries[key]
                retry_count = existing_entry.get('retry_count', 0) + 1
                existing_entry['retry_count'] = retry_count
                existing_entry['last_retry'] = datetime.now().isoformat()
            else:
                # Add new failed entry with retry count of 1
                failed_entry['retry_count'] = 1
                failed_entry['last_retry'] = datetime.now().isoformat()
                unique_entries[key] = failed_entry

        # Convert back to list
        existing_failed_entries = list(unique_entries.values())

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
        "timestamp": datetime.now().isoformat(),
        "failed_entries": existing_failed_entries,
        "failed_count": len(existing_failed_entries)
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


def is_model_completed(model_name, _ori_json_data, result_dir, log_dir=None):
    """
    Checks if a model has completed processing all entries.
    Only checks the dedicated resume point file.

    A model is considered completed if:
    1. The "completed" flag is True in the resume file
    2. There are no failed entries, or all failed entries have been retried the maximum number of times

    Args:
        model_name (str): Name of the model to check
        _ori_json_data (list): Original JSON data (unused, kept for API compatibility)
        result_dir (str): Directory containing result files
        log_dir (str, optional): Directory for log files

    Returns:
        tuple: (bool, dict) - (True if model has completed processing all entries, status info)
    """
    status_info = {
        "completed": False,
        "failed_entries_count": 0,
        "max_retries_reached": 0,
        "retryable_entries": 0
    }

    # Only check the resume point file if log_dir is provided
    if log_dir:
        resume_data = get_resume_data(model_name, log_dir)
        if resume_data:
            # Check if marked as completed
            if "completed" in resume_data:
                status_info["completed"] = resume_data["completed"]

            # Check failed entries
            failed_entries = resume_data.get("failed_entries", [])
            status_info["failed_entries_count"] = len(failed_entries)

            # Count entries that have reached max retries
            max_retries = 3  # Default max retries
            max_retries_reached = 0
            retryable_entries = 0

            for entry in failed_entries:
                retry_count = entry.get("retry_count", 0)
                if retry_count >= max_retries:
                    max_retries_reached += 1
                else:
                    retryable_entries += 1

            status_info["max_retries_reached"] = max_retries_reached
            status_info["retryable_entries"] = retryable_entries

            # A model is truly completed if it's marked as completed and all failed entries
            # have been retried the maximum number of times (or there are no failed entries)
            if status_info["completed"] and retryable_entries == 0:
                logger.info(f"Model {model_name} is marked as completed in resume file")
                if max_retries_reached > 0:
                    logger.warning(f"Model {model_name} has {max_retries_reached} entries that failed after maximum retries")
                return True, status_info

            # If there are retryable entries, the model is not truly completed
            if retryable_entries > 0:
                logger.warning(f"Model {model_name} has {retryable_entries} entries that can be retried")
                return False, status_info

            # If marked as completed and no retryable entries (all either succeeded or max retries reached)
            if status_info["completed"]:
                logger.info(f"Model {model_name} is marked as completed in resume file")
                if max_retries_reached > 0:
                    logger.warning(f"Model {model_name} has {max_retries_reached} entries that failed after maximum retries")
                return True, status_info
        else:
            # No resume data found, check if result file exists
            if result_dir:
                filename = sanitize_model_name(model_name) + '.json'
                filepath = os.path.join(result_dir, filename)

                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    # Result file exists but no resume point - this indicates an inconsistency
                    logger.warning(f"Result file exists for {model_name} but no resume point found. "
                                  f"Model will be treated as incomplete and reprocessed.")

    # No resume data or not completed
    return False, status_info


def find_resume_point(model_name, ori_json_data, result_dir, log_dir=None):
    """
    Finds the index to resume processing from.
    Only checks the dedicated resume point file.

    Args:
        model_name (str): Name of the model
        ori_json_data (list): Original JSON data (used only for length validation)
        result_dir (str): Directory containing result files
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

    # No resume point found, check if we need to clear existing result file
    if result_dir:
        filename = sanitize_model_name(model_name) + '.json'
        filepath = os.path.join(result_dir, filename)

        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            # Result file exists but no resume point - this indicates an inconsistency
            # We should clear the result file to avoid partial/inconsistent results
            try:
                # Create an empty JSON array in the file
                with open(filepath, 'w') as file:
                    file.write('[\n]')
                logger.warning(f"No resume point found for {model_name} but result file exists. "
                              f"Cleared result file {filepath} to avoid inconsistencies.")
            except Exception as e:
                logger.error(f"Error clearing result file for {model_name}: {e}")

    # No valid resume point found, start from beginning
    logger.info(f"No valid resume point found for {model_name}, starting from beginning")
    return 0


def get_failed_entries(model_name, log_dir):
    """
    Gets the list of failed entries for a model from the resume point file.

    Args:
        model_name (str): Name of the model
        log_dir (str): Directory for log files

    Returns:
        list: List of failed entries or empty list if none found
    """
    resume_data = get_resume_data(model_name, log_dir)
    if resume_data and "failed_entries" in resume_data:
        return resume_data["failed_entries"]
    return []


def add_failed_entry(model_name, entry, log_dir, error_message=None):
    """
    Adds an entry to the failed entries list for a model.

    Args:
        model_name (str): Name of the model
        entry (dict): The entry that failed processing
        log_dir (str): Directory for log files
        error_message (str, optional): Error message to include

    Returns:
        bool: True if the entry was added successfully, False otherwise
    """
    # Create a copy of the entry with only the identification fields
    failed_entry = {
        "id": entry.get('id'),
        "sub_id": entry.get('sub_id'),
        "code_id": entry.get('code_id'),
        "error": error_message,
        "timestamp": datetime.now().isoformat()
    }

    # Get the current resume data
    resume_file = get_resume_point_file_path(model_name, log_dir)
    resume_data = None

    try:
        if os.path.exists(resume_file) and os.path.getsize(resume_file) > 0:
            with open(resume_file, 'r') as file:
                resume_data = json.load(file)

        if resume_data is None:
            # If no resume data exists, create a minimal structure
            resume_data = {
                "model_name": model_name,
                "failed_entries": [failed_entry],
                "failed_count": 1,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Add to existing failed entries or create the list
            failed_entries = resume_data.get("failed_entries", [])

            # Check if this entry already exists
            entry_exists = False
            for existing in failed_entries:
                if (existing.get('id') == failed_entry['id'] and
                    existing.get('sub_id') == failed_entry['sub_id'] and
                    existing.get('code_id') == failed_entry['code_id']):
                    # Update retry count
                    existing['retry_count'] = existing.get('retry_count', 0) + 1
                    existing['last_retry'] = datetime.now().isoformat()
                    existing['error'] = error_message
                    entry_exists = True
                    break

            if not entry_exists:
                failed_entry['retry_count'] = 1
                failed_entries.append(failed_entry)

            resume_data["failed_entries"] = failed_entries
            resume_data["failed_count"] = len(failed_entries)
            resume_data["timestamp"] = datetime.now().isoformat()

        # Write updated resume data
        with open(resume_file, 'w') as file:
            json.dump(resume_data, file, indent=2)

        logger.warning(f"Added failed entry for {model_name} - ID: {failed_entry['id']}, "
                      f"Sub_ID: {failed_entry['sub_id']}, Code_ID: {failed_entry['code_id']}")
        return True

    except Exception as e:
        logger.error(f"Error adding failed entry for {model_name}: {e}")
        return False


def should_retry_entry(model_name, entry, log_dir, max_retries=3):
    """
    Determines if an entry should be retried based on its retry count.

    Args:
        model_name (str): Name of the model
        entry (dict): The entry to check
        log_dir (str): Directory for log files
        max_retries (int, optional): Maximum number of retry attempts. Defaults to 3.

    Returns:
        bool: True if the entry should be retried, False otherwise
    """
    failed_entries = get_failed_entries(model_name, log_dir)

    # Find this entry in the failed entries list
    for failed_entry in failed_entries:
        if (failed_entry.get('id') == entry.get('id') and
            failed_entry.get('sub_id') == entry.get('sub_id') and
            failed_entry.get('code_id') == entry.get('code_id')):

            # Check retry count
            retry_count = failed_entry.get('retry_count', 0)
            return retry_count < max_retries

    # If not found in failed entries, it's the first attempt
    return True


def clear_failed_entries(model_name, log_dir):
    """
    Clears the failed entries list for a model.

    Args:
        model_name (str): Name of the model
        log_dir (str): Directory for log files

    Returns:
        bool: True if successful, False otherwise
    """
    resume_file = get_resume_point_file_path(model_name, log_dir)

    try:
        if os.path.exists(resume_file) and os.path.getsize(resume_file) > 0:
            with open(resume_file, 'r') as file:
                resume_data = json.load(file)

            # Clear failed entries
            resume_data["failed_entries"] = []
            resume_data["failed_count"] = 0
            resume_data["timestamp"] = datetime.now().isoformat()

            # Write updated resume data
            with open(resume_file, 'w') as file:
                json.dump(resume_data, file, indent=2)

            logger.info(f"Cleared failed entries for {model_name}")
            return True

    except Exception as e:
        logger.error(f"Error clearing failed entries for {model_name}: {e}")

    return False


def reset_resume_point(model_name, log_dir):
    """
    Resets the resume point for a model, forcing it to start from the beginning.

    Args:
        model_name (str): Name of the model
        log_dir (str): Directory for log files

    Returns:
        bool: True if successful, False otherwise
    """
    resume_file = get_resume_point_file_path(model_name, log_dir)

    try:
        # Check if file exists before attempting to remove
        if os.path.exists(resume_file):
            os.remove(resume_file)
            logger.warning(f"Reset resume point for {model_name} - will start from beginning")
            return True
        else:
            logger.info(f"No resume point file found for {model_name}")
            return True

    except Exception as e:
        logger.error(f"Error resetting resume point for {model_name}: {e}")
        return False


def update_incomplete_models_summary(models, log_dir, result_dir=None):
    """
    Updates a summary file of incomplete models and their status.

    Args:
        models (dict): Dictionary of models to check
        log_dir (str): Directory for log files
        result_dir (str, optional): Directory containing result files

    Returns:
        dict: Summary of incomplete models
    """
    summary_file = os.path.join(log_dir, "incomplete_models.json")
    summary = {
        "timestamp": datetime.now().isoformat(),
        "incomplete_models": {},
        "total_models": len(models),
        "incomplete_count": 0,
        "failed_entries_total": 0
    }

    # Check each model
    for model_name in models.keys():
        completed, status_info = is_model_completed(model_name, None, result_dir, log_dir)

        if not completed:
            # Add to incomplete models
            summary["incomplete_models"][model_name] = {
                "status": status_info,
                "failed_entries": get_failed_entries(model_name, log_dir)
            }
            summary["incomplete_count"] += 1
            summary["failed_entries_total"] += status_info["failed_entries_count"]

    # Write summary to file
    try:
        with open(summary_file, 'w') as file:
            json.dump(summary, file, indent=2)
        logger.info(f"Updated incomplete models summary: {summary['incomplete_count']} incomplete models")
    except Exception as e:
        logger.error(f"Error updating incomplete models summary: {e}")

    return summary


def get_retry_file_path(model_name, entry, log_dir):
    """
    Get the path to the retry file for a specific entry.

    Args:
        model_name (str): Name of the model
        entry (dict): The entry that failed processing
        log_dir (str): Directory for log files

    Returns:
        str: Path to the retry file
    """
    # Create a retry directory if it doesn't exist
    retry_dir = os.path.join(log_dir, "retries")
    if not os.path.exists(retry_dir):
        os.makedirs(retry_dir)

    # Create a unique identifier for this entry
    entry_id = entry.get('id', 'unknown')
    sub_id = entry.get('sub_id', 'unknown')
    code_id = entry.get('code_id', 'unknown')
    entry_identifier = f"{entry_id}_{sub_id}_{code_id}"

    # Create a model-specific directory
    model_dir = os.path.join(retry_dir, sanitize_model_name(model_name))
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    # Return the path to the retry file
    return os.path.join(model_dir, f"{entry_identifier}.retry")


def create_retry_file(model_name, entry, log_dir, error_message):
    """
    Create a retry file for a failed entry.

    Args:
        model_name (str): Name of the model
        entry (dict): The entry that failed processing
        log_dir (str): Directory for log files
        error_message (str): Error message to include

    Returns:
        tuple: (bool, int) - (Success status, current retry count)
    """
    retry_file = get_retry_file_path(model_name, entry, log_dir)

    # Check if the retry file already exists
    retry_count = 1
    if os.path.exists(retry_file):
        try:
            with open(retry_file, 'r') as f:
                retry_data = json.load(f)
                retry_count = retry_data.get('retry_count', 0) + 1
        except Exception:
            # If we can't read the file, assume it's the first retry
            retry_count = 1

    # Create the retry data
    retry_data = {
        'model_name': model_name,
        'entry_id': entry.get('id'),
        'sub_id': entry.get('sub_id'),
        'code_id': entry.get('code_id'),
        'error': error_message,
        'retry_count': retry_count,
        'timestamp': datetime.now().isoformat()
    }

    try:
        with open(retry_file, 'w') as f:
            json.dump(retry_data, f, indent=2)
        logger.warning(f"Created retry file for {model_name} - ID: {entry.get('id')}, "
                      f"Sub_ID: {entry.get('sub_id')}, Code_ID: {entry.get('code_id')} "
                      f"(Retry {retry_count})")
        return True, retry_count
    except Exception as e:
        logger.error(f"Error creating retry file: {e}")
        return False, retry_count


def check_retry_status(model_name, entry, log_dir, max_retries=3):
    """
    Check if an entry should be retried and its current retry count.

    Args:
        model_name (str): Name of the model
        entry (dict): The entry to check
        log_dir (str): Directory for log files
        max_retries (int, optional): Maximum number of retry attempts. Defaults to 3.

    Returns:
        tuple: (bool, int) - (Should retry, current retry count)
    """
    retry_file = get_retry_file_path(model_name, entry, log_dir)

    if not os.path.exists(retry_file):
        # No retry file means this is the first attempt
        return True, 0

    try:
        with open(retry_file, 'r') as f:
            retry_data = json.load(f)
            retry_count = retry_data.get('retry_count', 0)

            # Check if we've reached the maximum retries
            if retry_count >= max_retries:
                logger.warning(f"Maximum retries ({max_retries}) reached for {model_name} - "
                              f"ID: {entry.get('id')}, Sub_ID: {entry.get('sub_id')}, "
                              f"Code_ID: {entry.get('code_id')}")
                return False, retry_count

            return True, retry_count
    except Exception as e:
        logger.error(f"Error checking retry status: {e}")
        # If we can't read the file, assume it's safe to retry
        return True, 0


def delete_retry_file(model_name, entry, log_dir):
    """
    Delete the retry file for a successful entry.

    Args:
        model_name (str): Name of the model
        entry (dict): The entry that was processed successfully
        log_dir (str): Directory for log files

    Returns:
        bool: True if successful, False otherwise
    """
    retry_file = get_retry_file_path(model_name, entry, log_dir)

    if not os.path.exists(retry_file):
        # No retry file to delete
        return True

    try:
        os.remove(retry_file)
        logger.info(f"Deleted retry file for {model_name} - ID: {entry.get('id')}, "
                   f"Sub_ID: {entry.get('sub_id')}, Code_ID: {entry.get('code_id')}")
        return True
    except Exception as e:
        logger.error(f"Error deleting retry file: {e}")
        return False


def ensure_directories(config):
    """
    Ensure all required directories exist.

    Args:
        config (dict): Configuration dictionary containing directory paths
    """
    directories = [
        config['output']['log_dir'],
        config['output']['result_dir']
    ]

    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")
