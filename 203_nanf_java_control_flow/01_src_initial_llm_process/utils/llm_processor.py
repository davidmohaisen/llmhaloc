"""
LLM processing utilities for vulnerability function localization.

This module handles interactions with LLMs, including prompt generation,
API calls, and response processing.

"""

import re
import json
import ollama

from .logger import Logger

# Initialize logger
logger = Logger()


def sanitize_model_name(model_name):
    """
    Sanitizes model names for use in filenames.

    Args:
        model_name (str): Original model name with potential special characters

    Returns:
        str: Sanitized name safe for filesystem use
    """
    return re.sub(r'[^a-zA-Z0-9]', '_', model_name)


def ns_to_seconds(ns):
    """
    Convert nanoseconds to seconds.

    Args:
        ns (int/float): Time in nanoseconds

    Returns:
        float: Time in seconds, rounded to 3 decimal places
    """
    return round(ns / 1e9, 3)


def get_language_from_filename(filename):
    """
    Determines programming language from file extension.

    Args:
        filename (str): Name of the source file

    Returns:
        str: Programming language name for syntax highlighting
    """
    if not filename:
        return "text"

    extension = filename.lower().split('.')[-1]
    language_map = {
        'java': 'java',
        'c': 'c',
        'cpp': 'cpp',
        'cc': 'cpp',
        'cxx': 'cpp',
        'h': 'c',
        'hpp': 'cpp',
        'py': 'python',
        'js': 'javascript',
        # Add more mappings as needed
    }
    return language_map.get(extension, 'text')


# This section previously contained AST-related extraction functions
# These have been removed as we're now using control flow information instead

# C/C++ related code has been removed as per requirements

def extract_control_flow_structure(control_flow_info, filename):
    """
    Process control flow information for code analysis.

    Args:
        control_flow_info (dict): Control flow information extracted from the code
        filename (str): Name of the source file

    Returns:
        dict: Structure information with control flow details
    """
    # If control_flow_info is None, create an empty structure
    if control_flow_info is None:
        control_flow_info = {
            "conditionals": [],
            "loops": [],
            "try_catch": [],
            "switch_statements": [],
            "analysis_status": "not_available",
            "statistics": {
                "conditional_count": 0,
                "loop_count": 0,
                "try_catch_count": 0,
                "switch_count": 0
            }
        }

    # Create the full structure with file path and control_flow_info
    structure = {
        "file_path": filename,
        "control_flow_info": control_flow_info
    }

    return structure

def extract_code_structure(code, filename, control_flow_info=None):
    """
    Extracts the code structure from the source code.
    If control_flow_info is provided, it will be used instead of generating a new one.

    Args:
        code (str): The source code to analyze
        filename (str): Name of the source file
        control_flow_info (dict, optional): Pre-extracted control flow information

    Returns:
        dict: A structured representation of the code with control flow information
    """
    # Process the control flow information
    return extract_control_flow_structure(control_flow_info, filename)

def generate_prompt(code, filename, control_flow_info=None):
    """
    Generates a markdown prompt template for analyzing code vulnerabilities.
    Includes control flow information to assist with vulnerability detection and localization.
    If control_flow_info is provided, it will be used instead of generating a new one.

    Args:
        code (str): The source code to analyze
        filename (str): Source file name to determine language
        control_flow_info (dict, optional): Pre-extracted control flow information

    Returns:
        str: A markdown formatted prompt template.
    """
    language = get_language_from_filename(filename)

    # Extract code structure using the provided control flow info if available
    structure = extract_code_structure(code, filename, control_flow_info)

    # Extract the control flow info for the prompt
    control_flow_info = structure.get("control_flow_info", {})

    # Convert to JSON string with indentation for readability
    control_flow_json = json.dumps(control_flow_info, indent=2)

    template = f"""Now, analyze the following {language} code:

### 1. Control Flow Analysis
```json
{control_flow_json}
```

### 2. Full Source Code
```{language}
{code}
```
"""
    return template


def call_ollama_chat(model_name, custom_prompt, system_prompt, config):
    """
    Helper function to encapsulate the ollama.chat call with appropriate parameters.

    Args:
        model_name (str): Name of the model to use
        custom_prompt (str): The prompt to send to the model
        system_prompt (str): System prompt to use
        config (dict): Configuration parameters

    Returns:
        dict: Response from the Ollama API

    Raises:
        Exception: If the API call fails
    """
    # Get context window size for this model
    models = config['models']
    num_ctx = models.get(model_name, 0)
    if num_ctx == 0:
        logger.warning(f"Model {model_name} has no context window defined, using default value 0")

    # Get Ollama options from config
    ollama_options = config['ollama_options']

    # Combine common options with model-specific context window
    options = {
        "num_ctx": num_ctx,
        **ollama_options
    }

    # Log prompts in verbose mode
    if config.get('verbose', False):
        logger.separator("=", 80)
        logger.info("VERBOSE MODE: Displaying detailed prompt information")
        logger.separator("-", 80)
        logger.info("SYSTEM PROMPT:")
        logger.info(f"\n{system_prompt}")
        logger.separator("-", 80)
        logger.info("USER PROMPT:")
        logger.info(f"\n{custom_prompt}")
        logger.separator("-", 80)
        logger.info(f"MODEL OPTIONS: {options}")
        logger.separator("=", 80)

    try:
        return ollama.chat(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": custom_prompt
                }
            ],
            options=options,
            keep_alive=0,
            stream=False
        )
    except Exception as e:
        logger.error(f"Error calling Ollama API with model {model_name}: {e}")
        raise


def extract_fields(entry):
    """
    Extracts fields from a single JSON object.

    Args:
        entry (dict): A dictionary representing a single CVE entry.

    Returns:
        tuple: A tuple containing the code, filename, identification fields, and control flow info.
    """
    code = entry.get('code', '')
    filename = entry.get('filename', '')
    entry_id = entry.get('id', 'Unknown')
    sub_id = entry.get('sub_id', 'Unknown')
    code_id = entry.get('code_id', 'Unknown')
    control_flow_info = entry.get('control_flow_info', None)
    return code, filename, entry_id, sub_id, code_id, control_flow_info


def interact_with_llm(entry, custom_prompt, model_name, config):
    """
    Interacts with an LLM based on provided prompts and model name.
    Logs warnings for missing fields and uses default values.

    Args:
        entry (dict): The data entry containing identification information
        custom_prompt (str): The prompt to send to the model
        model_name (str): Name of the model to use
        config (dict): Configuration parameters

    Returns:
        dict: A new entry with the model's response and performance metrics

    Raises:
        Exception: If the interaction fails
    """
    entry_id = entry.get('id', 'Unknown')
    sub_id = entry.get('sub_id', 'Unknown')
    code_id = entry.get('code_id', 'Unknown')

    try:
        logger.info(f"Processing with {model_name} - ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}")

        response = call_ollama_chat(model_name, custom_prompt, config['system_prompt'], config)
        logger.info(f"Got response from {model_name} - ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}")

        # Log response in verbose mode
        if config.get('verbose', False):
            logger.separator("=", 80)
            logger.info("VERBOSE MODE: Displaying model response")
            logger.separator("-", 80)
            logger.info("RESPONSE CONTENT:")
            logger.info(f"\n{response['message']['content']}")
            logger.separator("=", 80)

        # Check for missing fields and log warnings
        expected_fields = ['total_duration', 'load_duration', 'prompt_eval_count',
                         'prompt_eval_duration', 'eval_count', 'eval_duration']
        for field in expected_fields:
            if field not in response:
                logger.warning(f"Missing {field} in response for {model_name} - ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}")

        new_entry = {
            'id': entry_id,
            'sub_id': sub_id,
            'code_id': code_id,
            'response': response['message']['content'],
            'total_duration': ns_to_seconds(response.get('total_duration', 0)),
            'load_duration': ns_to_seconds(response.get('load_duration', 0)),
            'prompt_eval_count': response.get('prompt_eval_count', 0),
            'prompt_eval_duration': ns_to_seconds(response.get('prompt_eval_duration', 0)),
            'eval_count': response.get('eval_count', 0),
            'eval_duration': ns_to_seconds(response.get('eval_duration', 0))
        }
        return new_entry
    except Exception as e:
        logger.error(f"Error with {model_name} - ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}: {e}")
        raise
