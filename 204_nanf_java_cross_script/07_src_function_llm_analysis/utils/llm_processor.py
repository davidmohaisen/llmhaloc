"""
LLM processing utilities for vulnerability function localization.

This module handles interactions with LLMs, including prompt generation,
API calls, and response processing.

"""

import json
import ollama

from .logger import Logger

# Initialize logger
logger = Logger()


def generate_custom_prompt(previous_response, ground_truth_entry):
    """
    Generate custom prompt for function analysis.
    This matches the approach used in the archived main script.

    Args:
        previous_response (str): The previous LLM's response to analyze
        ground_truth_entry (dict): The ground truth entry containing function information

    Returns:
        str: A formatted prompt template
    """
    return f"""**Previous LLM's Response**:
{previous_response}

**Function Data**:
Class Name: {ground_truth_entry.get('class_name', 'N/A')}
Subclass Name: {ground_truth_entry.get('subclass_name', 'N/A')}
Function Name: {ground_truth_entry.get('function_name', 'N/A')}
Function Body:
{ground_truth_entry.get('function_body', 'N/A')}
"""


def _get_ollama_options(config, model_name):
    """
    Extract Ollama options from the configuration.

    Args:
        config (dict): Configuration parameters
        model_name (str): Name of the model to use

    Returns:
        tuple: (options, keep_alive, stream, response_format, num_ctx)
    """
    # Get context window size from model config
    num_ctx = config.get('model', {}).get('context_window', 0)
    if num_ctx == 0:
        logger.warning(f"No context window defined for model {model_name}, using default value 0")

    # Get Ollama configuration from config
    ollama_config = config.get('ollama', {})

    # Get Ollama options and add context window
    options = ollama_config.get('options', {}).copy()  # Create a copy to avoid modifying the original
    options['num_ctx'] = num_ctx  # Add context window to options

    # Get API call parameters
    keep_alive = ollama_config.get('keep_alive', 0)
    stream = ollama_config.get('stream', False)
    response_format = ollama_config.get('format', None)

    return options, keep_alive, stream, response_format, num_ctx


def _log_verbose_info(model_name, system_prompt, custom_prompt, num_ctx, keep_alive, stream, response_format, options):
    """
    Log verbose information about the Ollama API call.

    Args:
        model_name (str): Name of the model to use
        system_prompt (str): System prompt to use
        custom_prompt (str): The prompt to send to the model
        num_ctx (int): Context window size
        keep_alive (int): Keep alive parameter
        stream (bool): Stream parameter
        response_format (str): Response format parameter
        options (dict): Ollama options
    """
    logger.separator("=", 80)
    logger.info(f"VERBOSE MODE: Displaying prompts for model {model_name}")
    logger.separator("-", 80)
    logger.info("SYSTEM PROMPT:")
    logger.info(system_prompt)
    logger.separator("-", 80)
    logger.info("USER PROMPT:")
    logger.info(custom_prompt)
    logger.separator("-", 80)
    logger.info("OLLAMA OPTIONS:")
    logger.info(f"Context Window: {num_ctx}")
    logger.info(f"Keep Alive: {keep_alive}")
    logger.info(f"Stream: {stream}")
    logger.info(f"Format: {response_format}")
    logger.info(f"Generation Options: {options}")
    logger.separator("=", 80)


def _build_api_params(model_name, system_prompt, custom_prompt, options, keep_alive, stream, response_format):
    """
    Build the parameters for the Ollama API call.

    Args:
        model_name (str): Name of the model to use
        system_prompt (str): System prompt to use
        custom_prompt (str): The prompt to send to the model
        options (dict): Ollama options
        keep_alive (int): Keep alive parameter
        stream (bool): Stream parameter
        response_format (str): Response format parameter

    Returns:
        dict: API parameters
    """
    api_params = {
        'model': model_name,
        'messages': [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": custom_prompt
            }
        ],
        'options': options,
        'keep_alive': keep_alive,
        'stream': stream
    }

    # Add format parameter if specified
    if response_format:
        api_params['format'] = response_format

    return api_params


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
    # Get Ollama options from config
    options, keep_alive, stream, response_format, num_ctx = _get_ollama_options(config, model_name)

    # Check if verbose mode is enabled
    verbose = config.get('verbose', False)
    if verbose:
        _log_verbose_info(model_name, system_prompt, custom_prompt, num_ctx, keep_alive, stream, response_format, options)

    try:
        # Build the API call parameters
        api_params = _build_api_params(model_name, system_prompt, custom_prompt, options, keep_alive, stream, response_format)

        # Call the Ollama API
        return ollama.chat(**api_params)
    except Exception as e:
        logger.error(f"Error calling Ollama API with model {model_name}: {e}")
        raise


def _create_output_entry_structure(input_entry, ground_truth_entry):
    """
    Create the basic structure for an output entry.

    Args:
        input_entry (dict): The input entry containing the LLM response
        ground_truth_entry (dict): The ground truth entry containing function information

    Returns:
        dict: A new entry with fields from both input and ground truth
    """
    return {
        # Ground truth fields
        'id': ground_truth_entry.get('id'),
        'sub_id': ground_truth_entry.get('sub_id'),
        'code_id': ground_truth_entry.get('code_id'),
        'function_id': ground_truth_entry.get('function_id'),
        'human_patch': ground_truth_entry.get('human_patch'),
        'cve_id': ground_truth_entry.get('cve_id'),
        'cwe_id': ground_truth_entry.get('cwe_id'),
        'filename': ground_truth_entry.get('filename'),
        'is_vulnerable': ground_truth_entry.get('is_vulnerable'),
        'class_name': ground_truth_entry.get('class_name', 'N/A'),
        'subclass_name': ground_truth_entry.get('subclass_name', 'N/A'),
        'function_name': ground_truth_entry.get('function_name', 'N/A'),
        'function_body': ground_truth_entry.get('function_body', 'N/A'),

        # Input fields
        'prompt_eval_count': input_entry.get('prompt_eval_count'),
        'prompt_eval_duration': input_entry.get('prompt_eval_duration'),
        'eval_count': input_entry.get('eval_count'),
        'eval_duration': input_entry.get('eval_duration'),
        'total_duration': input_entry.get('total_duration'),
        'load_duration': input_entry.get('load_duration'),
        'relevance_label': input_entry.get('relevance_label'),
        'response': input_entry.get('response'),
        'function_analysis': ''
    }


def _is_entry_relevant(input_entry):
    """
    Check if an entry is relevant for processing.

    Args:
        input_entry (dict): The input entry to check

    Returns:
        bool: True if the entry is relevant, False otherwise
    """
    return input_entry.get('relevance_label') == 1


def _validate_ollama_response(ollama_response, entry_id, sub_id, code_id):
    """
    Validate the response from Ollama and log any missing fields.

    Args:
        ollama_response (dict): Response from Ollama API
        entry_id (str): ID of the entry being processed
        sub_id (str): Sub ID of the entry being processed
        code_id (str): Code ID of the entry being processed

    Returns:
        bool: True if the response is valid, False otherwise
    """
    expected_fields = ['total_duration', 'load_duration', 'prompt_eval_count',
                     'prompt_eval_duration', 'eval_count', 'eval_duration']

    is_valid = True
    for field in expected_fields:
        if field not in ollama_response:
            logger.warning(f"Missing {field} in ollama response - ID:{entry_id}, Sub_ID:{sub_id}, Code_ID:{code_id}")
            is_valid = False

    return is_valid


def _process_relevant_entry(input_entry, ground_truth_entry, model_name, config, output_entry):
    """
    Process a relevant entry by calling the LLM and updating the output entry.

    Args:
        input_entry (dict): The input entry containing the LLM response
        ground_truth_entry (dict): The ground truth entry containing function information
        model_name (str): Name of the model to use
        config (dict): Configuration parameters
        output_entry (dict): The output entry to update

    Returns:
        dict: The updated output entry
    """
    entry_id = input_entry.get('id', 'Unknown')
    sub_id = input_entry.get('sub_id', 'Unknown')
    code_id = input_entry.get('code_id', 'Unknown')
    function_id = ground_truth_entry.get('function_id', 'Unknown')

    logger.info(f"Found relevant entry (relevance_label=1) for ID:{entry_id}, "
               f"Sub_ID:{sub_id}, Code_ID:{code_id}")

    logger.info(f"Extracting function data for Function_ID:{function_id}, "
               f"Function:{ground_truth_entry.get('function_name')}")

    # Generate prompt and call LLM
    prompt = generate_custom_prompt(input_entry.get('response', ''), ground_truth_entry)
    ollama_response = call_ollama_chat(model_name, prompt, config['system_prompt'], config)

    # Validate response
    _validate_ollama_response(ollama_response, entry_id, sub_id, code_id)

    # Update output entry with function analysis
    output_entry['function_analysis'] = ollama_response['message']['content']

    return output_entry


def process_entry(input_entry, ground_truth_entry, model_name, config):
    """
    Process a single entry and return the output entry.
    This matches the approach used in the archived main script.

    Args:
        input_entry (dict): The input entry containing the LLM response
        ground_truth_entry (dict): The ground truth entry containing function information
        model_name (str): Name of the model to use
        config (dict): Configuration parameters

    Returns:
        dict: A new entry with the model's response and performance metrics
    """
    entry_id = input_entry.get('id', 'Unknown')
    sub_id = input_entry.get('sub_id', 'Unknown')
    code_id = input_entry.get('code_id', 'Unknown')
    function_id = ground_truth_entry.get('function_id', 'Unknown')

    logger.info(f"Processing input entry ID:{entry_id}, Sub_ID:{sub_id}, Code_ID:{code_id}, Function_ID:{function_id}")

    # Create the basic output entry structure
    output_entry = _create_output_entry_structure(input_entry, ground_truth_entry)

    # Process the entry if it's relevant
    if _is_entry_relevant(input_entry):
        output_entry = _process_relevant_entry(input_entry, ground_truth_entry, model_name, config, output_entry)

    return output_entry