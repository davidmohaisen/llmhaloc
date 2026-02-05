"""
CONFIGURATION NOTES:
-------------------
1. Input Dataset:
   - Current: '001_datasets/final_java_dataset.json'
   - Modify DATA_DIR if dataset location/name changes
   
2. Log File:
   - Current: 'mac.log' in '00_logs' directory
   - Change LOG_FILE_NAME for different machines (e.g., 'windows.log', 'linux.log')
   
3. Results Directory:
   - Current: '02_initial_results'
   - Modify RESULT_DIR if different output location needed
"""

import logging
import os
from datetime import datetime
import json
import ollama
import time
import re

# Get the base directory (working directory)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "001_datasets", "final_c_dataset.json")

# Get the experiment directory (100_zero_shot)
EXPERIMENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configure directories
LOG_DIR = os.path.join(EXPERIMENT_DIR, "00_logs")
LOG_FILE_NAME = '01_mac.log'
RESULT_DIR = os.path.join(EXPERIMENT_DIR, "02_initial_results")

# Ensure directories exist
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
    # logging.info(f"Created logs directory: {LOG_DIR}")
if not os.path.exists(RESULT_DIR):
    os.makedirs(RESULT_DIR)
    # logging.info(f"Created results directory: {RESULT_DIR}")

SYSTEM_PROMPT = """
Role: Code Security Analyst

Goal: Analyze the provided code file to identify any functions that may contain security vulnerabilities. Assume the file may contain at least one vulnerable function. Report the name and arguments of any vulnerable functions and provide explanations for why each was flagged as vulnerable.

Instructions:
- Use a step-by-step approach to analyze the code at the function level, identifying any functions that may introduce security risks.

For each vulnerable function, provide:
   - **Function Signature**: The function name followed by its arguments in parentheses (e.g., `functionName(type1 arg1, type2 arg2)`).
   - **Reason**: A concise explanation of why this function is considered vulnerable, detailing any relevant issues that may lead to security risks.

Output Format:
Provide the output in JSON format as follows:

```json
[
  {
    "vulnerable_function_signature": "functionName(type1 arg1, type2 arg2)",
    "reason": "Explanation of the vulnerability in this function."
  },
  {
    "vulnerable_function_signature": "anotherFunctionName(type1 arg1)",
    "reason": "Explanation of the vulnerability in this function."
  }
]
```
"""

# Custom logging formatter with specified timestamp format
class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created)
        if datefmt:
            return ct.strftime(datefmt)
        return ct.isoformat()


# Configure the logging
log_file_path = os.path.join(LOG_DIR, LOG_FILE_NAME)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()  # This will also log to the console
    ]
)

MODEL_CTX_MAP = {
    'codegemma:7b-instruct-v1.1-fp16': 8192,
    'codegemma:7b-instruct-v1.1-q5_K_M': 8192,
    'codellama:34b-instruct-fp16': 16384,
    'codellama:34b-instruct-q5_K_M': 16384,
    'codellama:7b-instruct-fp16': 16384,
    'codellama:7b-instruct-q5_K_M': 16384,
    'deepseek-coder-v2:16b-lite-instruct-fp16': 163840,
    'deepseek-coder-v2:16b-lite-instruct-q5_K_M': 163840,
    'deepseek-v2:16b-lite-chat-fp16': 163840,
    'deepseek-v2:16b-lite-chat-q5_K_M': 163840,
    'gemma2:27b-instruct-fp16': 8192,
    'gemma2:27b-instruct-q5_K_M': 8192,
    'gemma2:9b-instruct-fp16': 8192,
    'gemma2:9b-instruct-q5_K_M': 8192,
    'gemma:2b-instruct-v1.1-fp16': 8192,
    'gemma:2b-instruct-v1.1-q5_K_M': 8192,
    'gemma:7b-instruct-v1.1-fp16': 8192,
    'gemma:7b-instruct-v1.1-q5_K_M': 8192,
    'glm4:9b-chat-fp16': 131072,
    'glm4:9b-chat-q5_K_M': 131072,
    'llama2:13b-chat-fp16': 4096,
    'llama2:13b-chat-q5_K_M': 4096,
    'llama2:7b-chat-fp16': 4096,
    'llama2:7b-chat-q5_K_M': 4096,
    'llama3.1:8b-instruct-fp16': 131072,
    'llama3.1:8b-instruct-q5_K_M': 131072,
    'llama3:8b-instruct-fp16': 8192,
    'llama3:8b-instruct-q5_K_M': 8192,
    'mistral:7b-instruct-v0.2-fp16': 32768,
    'mistral:7b-instruct-v0.2-q5_K_M': 32768,
    'mistral:7b-instruct-v0.3-fp16': 32768,
    'mistral:7b-instruct-v0.3-q5_K_M': 32768,
    'mixtral:8x7b-instruct-v0.1-q5_K_M': 32768,
    'phi3:14b-medium-128k-instruct-f16': 131072,
    'phi3:14b-medium-128k-instruct-q5_K_M': 131072,
    'phi3:14b-medium-4k-instruct-f16': 4096,
    'phi3:14b-medium-4k-instruct-q5_K_M': 4096,
    'phi3:3.8b-mini-128k-instruct-f16': 131072,
    'phi3:3.8b-mini-128k-instruct-q5_K_M': 131072,
    'phi3:3.8b-mini-4k-instruct-f16': 4096,
    'phi3:3.8b-mini-4k-instruct-q5_K_M': 4096,
    'phi:2.7b-chat-v2-fp16': 2048,
    'phi:2.7b-chat-v2-q5_K_M': 2048,
    'qwen2:0.5b-instruct-fp16': 32768,
    'qwen2:0.5b-instruct-q5_K_M': 32768,
    'qwen2:1.5b-instruct-fp16': 32768,
    'qwen2:1.5b-instruct-q5_K_M': 32768,
    'qwen2:7b-instruct-fp16': 32768,
    'qwen2:7b-instruct-q5_K_M': 32768,
    'codellama:70b-instruct-fp16': 4096,
    'codellama:70b-instruct-q5_K_M': 2048,
    'llama2:70b-chat-fp16': 4096,
    'llama2:70b-chat-q5_K_M': 4096,
    # 'llama3.1:70b-instruct-fp16': 131072,
    'llama3.1:70b-instruct-q5_K_M': 131072,
    'llama3:70b-instruct-fp16': 8192,
    'llama3:70b-instruct-q5_K_M': 8192,
    'mistral-large:123b-instruct-2407-q5_K_M': 32768,
    # 'mistral-nemo:12b-instruct-2407-fp16': 1024000,
    # 'mistral-nemo:12b-instruct-2407-q5_K_M': 1024000,
    'mixtral:8x22b-instruct-v0.1-q5_K_M': 65536,
    'mixtral:8x7b-instruct-v0.1-fp16': 32768,
    'qwen2:72b-instruct-fp16': 32768,
    'qwen2:72b-instruct-q5_K_M': 32768,
    'qwq:32b-preview-fp16': 32768,
    'marco-o1:7b-fp16': 32768
}


def load_json_data(file_path):
    """
    Load and parse a JSON file into a Python dictionary.

    Args:
    file_path (str): The path to the JSON file to be loaded.

    Returns:
    dict: A dictionary containing the parsed JSON data.

    Raises:
    FileNotFoundError: If the JSON file does not exist at the specified path.
    json.JSONDecodeError: If the file is not a valid JSON.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        logging.info(f"Successfully loaded data from {file_path}")
        return data
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {file_path}: {e}")
        raise
    except Exception as e:
        logging.error(f"An error occurred while loading {file_path}: {e}")
        raise


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


def extract_fields(entry):
    """
    Extracts fields from a single JSON object.

    Args:
    entry (dict): A dictionary representing a single CVE entry.

    Returns:
    tuple: A tuple containing the code, filename, and identification fields.
    """
    code = entry.get('code', '')
    filename = entry.get('filename', '')
    id = entry.get('id', 'Unknown')
    sub_id = entry.get('sub_id', 'Unknown')
    code_id = entry.get('code_id', 'Unknown')
    return code, filename, id, sub_id, code_id


def sanitize_model_name(model_name):
    """
    Sanitizes model names for use in filenames.
    
    Args:
    model_name (str): Original model name with potential special characters
    
    Returns:
    str: Sanitized name safe for filesystem use
    """
    return re.sub(r'[^a-zA-Z0-9]', '_', model_name)


def write_to_json(new_entry, model_name):
    """
    Writes a new JSON object to a file based on the model name.

    Args:
    new_entry (dict): The new JSON object to write.
    model_name (str): Model name, used to determine the filename.
    """
    id = new_entry.get('id', 'Unknown')
    sub_id = new_entry.get('sub_id', 'Unknown')
    code_id = new_entry.get('code_id', 'Unknown')

    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)
        logging.info(f"Created directory {RESULT_DIR}")

    filename = sanitize_model_name(model_name) + '.json'
    filepath = os.path.join(RESULT_DIR, filename)

    try:
        data = []
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            with open(filepath, 'r') as file:
                data = json.load(file)
        data.append(new_entry)

        with open(filepath, 'w') as file:
            json.dump(data, file, indent=4)
        logging.info(f"Appended data for {model_name} - ID: {id}, Sub_ID: {sub_id}, Code_ID: {code_id}")
    except Exception as e:
        logging.error(f"Error writing data for {model_name} - ID: {id}, Sub_ID: {sub_id}, Code_ID: {code_id}: {e}")
        raise


def call_ollama_chat(model_name, custom_prompt):
    """
    Helper function to encapsulate the ollama.chat call.
    """
    num_ctx = MODEL_CTX_MAP.get(model_name, 0)
    if num_ctx == 0:
        logging.warning(f"Model {model_name} has no context window defined in MODEL_CTX_MAP, using default value 0")

    options = {
        "mirostat": 0,
        "mirostat_eta": 0.1,
        "mirostat_tau": 3.0,
        "num_ctx": num_ctx,
        "num_gqa": 8,
        "repeat_last_n": -1,
        "repeat_penalty": 1.5,
        "temperature": 0.5,
        "seed": 42,
        "tfs_z": 1.0,
        "num_predict": 2048,
        "top_k": 40,
        "top_p": 0.5
    }

    return ollama.chat(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
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


def ns_to_seconds(ns):
    """
    Convert nanoseconds to seconds.
    
    Args:
    ns (int/float): Time in nanoseconds
    
    Returns:
    float: Time in seconds, rounded to 3 decimal places
    """
    return round(ns / 1e9, 3)


def interact_with_llm(entry, custom_prompt, model_name):
    """
    Simulates interaction with an LLM based on provided prompts and model name.
    Logs warnings for missing fields and uses default values.
    """
    id = entry.get('id', 'Unknown')
    sub_id = entry.get('sub_id', 'Unknown')
    code_id = entry.get('code_id', 'Unknown')
    
    try:
        logging.info(f"Processing with {model_name} - ID: {id}, Sub_ID: {sub_id}, Code_ID: {code_id}")

        response = call_ollama_chat(model_name, custom_prompt)
        logging.info(f"Got response from {model_name} - ID: {id}, Sub_ID: {sub_id}, Code_ID: {code_id}")

        # Check for missing fields and log warnings
        expected_fields = ['total_duration', 'load_duration', 'prompt_eval_count', 
                         'prompt_eval_duration', 'eval_count', 'eval_duration']
        for field in expected_fields:
            if field not in response:
                logging.warning(f"Missing {field} in response for {model_name} - ID: {id}, Sub_ID: {sub_id}, Code_ID: {code_id}")

        new_entry = {
            'id': id,
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
        logging.error(f"Error with {model_name} - ID: {id}, Sub_ID: {sub_id}, Code_ID: {code_id}: {e}")
        raise


def generate_prompt(code, filename):
    """
    Generates a markdown prompt template for analyzing code vulnerabilities.

    Args:
    code (str): The source code to analyze
    filename (str): Source file name to determine language

    Returns:
    str: A markdown formatted prompt template.
    """
    language = get_language_from_filename(filename)
    template = f"""Now, analyze the following {language} code:
        ```{language}
        {code}
        ```
        """
    return template


def get_last_processed_entry(model_name):
    """
    Gets the last successfully processed entry for a given model.
    
    Args:
    model_name (str): Name of the model to check
    
    Returns:
    tuple: (id, sub_id, code_id) of last processed entry, or None if no file exists
    """
    filename = sanitize_model_name(model_name) + '.json'
    filepath = os.path.join(RESULT_DIR, filename)
    
    try:
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            with open(filepath, 'r') as file:
                data = json.load(file)
                if data:  # If file has entries
                    last_entry = data[-1]
                    return (
                        last_entry.get('id'),
                        last_entry.get('sub_id'),
                        last_entry.get('code_id')
                    )
    except Exception as e:
        logging.error(f"Error reading last processed entry for {model_name}: {e}")
    
    return None

def is_model_completed(model_name, ori_json_data):
    """
    Checks if a model has completed processing all entries.
    
    Args:
    model_name (str): Name of the model to check
    ori_json_data (list): Original JSON data
    
    Returns:
    bool: True if model has processed all entries
    """
    last_processed = get_last_processed_entry(model_name)
    if not last_processed:
        return False
        
    last_original = ori_json_data[-1]
    return (
        last_processed[0] == last_original['id'] and
        last_processed[1] == last_original['sub_id'] and
        last_processed[2] == last_original['code_id']
    )

def find_resume_point(model_name, ori_json_data):
    """
    Finds the index to resume processing from.
    
    Args:
    model_name (str): Name of the model
    ori_json_data (list): Original JSON data
    
    Returns:
    int: Index to resume from, or 0 if starting fresh
    """
    last_processed = get_last_processed_entry(model_name)
    if not last_processed:
        return 0
        
    for i, entry in enumerate(ori_json_data):
        if (entry['id'] == last_processed[0] and 
            entry['sub_id'] == last_processed[1] and 
            entry['code_id'] == last_processed[2]):
            return i + 1
    
    return 0

def main():
    try:
        ori_json_data = load_json_data(DATA_DIR)
        total_entries = len(ori_json_data)
        
        for model_name in MODEL_CTX_MAP.keys():
            logging.info(f"Processing model: {model_name}")
            
            # Skip if model has completed all entries
            if is_model_completed(model_name, ori_json_data):
                logging.info(f"Skipping {model_name} - already completed")
                continue
            
            # Find resume point
            start_idx = find_resume_point(model_name, ori_json_data)
            logging.info(f"Resuming {model_name} from index {start_idx}/{total_entries}")
            
            # Process remaining entries
            for idx, entry in enumerate(ori_json_data[start_idx:], start=start_idx):
                try:
                    code, filename, id, sub_id, code_id = extract_fields(entry)
                    logging.info(f"Processing {model_name} - Progress: {idx+1}/{total_entries} "
                               f"({((idx+1)/total_entries*100):.2f}%) "
                               f"- ID: {id}, Sub_ID: {sub_id}, Code_ID: {code_id}")
                    
                    custom_prompt = generate_prompt(code, filename)
                    new_entry = interact_with_llm(entry, custom_prompt, model_name)
                    write_to_json(new_entry, model_name)
                    
                except Exception as e:
                    logging.error(
                        f"Failed processing {model_name} - Index: {idx+1}/{total_entries} "
                        f"- ID: {id}, Sub_ID: {sub_id}, Code_ID: {code_id}: {e}"
                    )
                    continue

    except Exception as e:
        logging.error(f"An error occurred: {e}")


if __name__ == '__main__':
    main()
