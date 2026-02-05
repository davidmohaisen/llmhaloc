import logging
import os
from datetime import datetime
import json
import ollama

# Get the base directory (working directory)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get the experiment directory (relative path)
EXPERIMENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configure directories
LOG_DIR = os.path.join(EXPERIMENT_DIR, "00_logs")
LOG_FILE_NAME = '04_function_analysis.log'
LOG_FILE_PATH = os.path.join(LOG_DIR, LOG_FILE_NAME)

# Input directory
INPUT_DIR = os.path.join(EXPERIMENT_DIR, "06_relevant_analysis_final_results")

# Output directory
OUTPUT_DIR = os.path.join(EXPERIMENT_DIR, "08_function_analysis_results")

# Ground truth file path
GROUND_TRUTH_PATH = os.path.join(BASE_DIR, "003_ground_truth_generation_ccpp", "02_ground_truth_c_cpp_functions.json")

# Model configuration
MODEL_NAME = 'llama3.3:70b-instruct-q5_K_M'

SYSTEM_PROMPT = """
You are a **Code Security Response Analyst**. Your task is to review the **previous LLM’s response** and determine if a specific function from the source code file is considered **vulnerable** or **not vulnerable** based on the content of that response.

### Context
1. A previous LLM has analyzed a code file for potential security vulnerabilities. Its response may or may not reference specific functions as vulnerable.
2. You are given:
   - The **previous LLM’s response** (which can be in any format, possibly JSON or free text).
   - The **function information**, including:
     - Class name
     - Subclass name (if any)
     - Function name
     - Full function body
3. Your job is to determine if this function is flagged as vulnerable according to the previous LLM’s response. If the function name or its body is explicitly mentioned as vulnerable, then you must classify it as **vulnerable**. Otherwise, classify it as **not vulnerable**.

### Output Requirements
You must produce output in **JSON format** with the following structure:

```json
{
  "is_function_vulnerable": "<vulnerable or not vulnerable>",
  "reasoning": "<concise reason>"
}
```

Where:
- **is_function_vulnerable** should be either `"vulnerable"` or `"not vulnerable"`.
- **reasoning** should concisely explain why you arrived at that conclusion (e.g., the function name or body was cited in the response, or it was not mentioned at all).

### Steps & Rules

1. **Parse the previous LLM’s response**: Look for any indication that the function in question (by name or by referencing its functionality) is deemed vulnerable.
2. **Check function details**: Compare the function name or relevant details with what the previous LLM flagged. If it matches or is described as risky, conclude that it is **vulnerable**.
3. **Justify your conclusion**:
   - If the function is referenced or flagged in the previous LLM’s response, provide a brief rationale (e.g., “It was cited for improper input validation”).
   - If there is no mention of the function or any related vulnerability in the previous LLM’s response, explain that it is not flagged as vulnerable.
4. **Output your findings** strictly in the designated JSON format.

### Example

**Previous LLM’s Response**:
```json
[
  {
    "vulnerable_function_signature": "someFunction(int param1, String param2)",
    "reason": "Potential buffer overflow"
  }
]
```
**Function Data**:
```json
{
  "class_name": "ExampleClass",
  "subclass_name": null,
  "function_name": "anotherFunction",
  "function_body": " ... "
}
```
**Analysis & Output**:
- The function in question, anotherFunction, does not appear in the vulnerable list from the previous LLM’s response.
- Therefore, the output is:

**Final JSON**:
```json
{
  "is_function_vulnerable": "not vulnerable",
  "reasoning": "This function was not mentioned in the previous LLM’s vulnerability report."
}
```
"""

OPTIONS = {
    "mirostat": 1,
    "mirostat_eta": 0.1,
    "mirostat_tau": 3.0,
    "num_ctx": 131072,
    "num_gqa": 8,
    "repeat_last_n": -1,
    "repeat_penalty": 1.5,
    "temperature": 0.3,
    "seed": 42,
    "tfs_z": 1.0,
    "num_predict": 2048,
    "top_k": 40,
    "top_p": 0.5
}

# Create directories if they don't exist
for directory in [LOG_DIR, OUTPUT_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Custom logging formatter with specified timestamp format
class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created)
        return ct.isoformat() if not datefmt else ct.strftime(datefmt)

# Configure the logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s msg="%(message)s"',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler()
    ]
)

def load_json_data(file_path):
    """Load JSON data from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            logging.info(f"Successfully loaded data from {file_path}")
            return data
    except Exception as e:
        logging.error(f"Error loading data from {file_path}: {e}")
        raise

def generate_custom_prompt(previous_response, ground_truth_entry):
    """Generate custom prompt for function analysis."""
    return f"""**Previous LLM's Response**:
{previous_response}

**Function Data**:
Class Name: {ground_truth_entry.get('class_name', 'N/A')}
Subclass Name: {ground_truth_entry.get('subclass_name', 'N/A')}
Function Name: {ground_truth_entry.get('function_name', 'N/A')}
Function Body:
{ground_truth_entry.get('function_body', 'N/A')}
"""

def call_ollama(custom_prompt):
    """
    Helper function to encapsulate the ollama.chat call.
    """
    return ollama.chat(
        model=MODEL_NAME,
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
        options=OPTIONS,
        keep_alive=-1,
        stream=False,
        format='json'
    )

def process_entry(input_entry, ground_truth_entry):
    """Process a single entry and return the output entry."""
    entry_id = (
        input_entry.get('id'),
        input_entry.get('sub_id'),
        input_entry.get('code_id')
    )
    
    logging.info(f"Processing input entry ID:{entry_id[0]}, Sub_ID:{entry_id[1]}, Code_ID:{entry_id[2]}")
    
    output_entry = {
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
    
    if input_entry.get('relevance_label') == 1:
        logging.info(f"Found relevant entry (relevance_label=1) for ID:{entry_id[0]}, "
                    f"Sub_ID:{entry_id[1]}, Code_ID:{entry_id[2]}")
        
        logging.info(f"Extracting function data for Function_ID:{ground_truth_entry.get('function_id')}, "
                    f"Function:{ground_truth_entry.get('function_name')}")
        
        prompt = generate_custom_prompt(input_entry.get('response', ''), ground_truth_entry)
        ollama_response = call_ollama(prompt)

        # Check for missing fields in ollama response
        expected_fields = ['total_duration', 'load_duration', 'prompt_eval_count', 
                         'prompt_eval_duration', 'eval_count', 'eval_duration']
        for field in expected_fields:
            if field not in ollama_response:
                logging.warning(f"Missing {field} in ollama response - ID:{entry_id[0]}, Sub_ID:{entry_id[1]}, Code_ID:{entry_id[2]}")

        output_entry['function_analysis'] = ollama_response['message']['content']
    
    return output_entry

def append_to_output(output_file, entry):
    """
    Append a single entry to the output JSON file.
    If file doesn't exist or is empty, create new file with list.
    If exists, load, append, and write back.
    """
    try:
        data = []
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            with open(output_file, 'r') as f:
                data = json.load(f)
        
        data.append(entry)
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=4)
            
        logging.info(
            f"Successfully appended entry (ID:{entry['id']}, Sub_ID:{entry['sub_id']}, "
            f"Code_ID:{entry['code_id']}, Function_ID:{entry['function_id']}) to {output_file}"
        )
        
    except Exception as e:
        logging.error(
            f"Error appending entry (ID:{entry['id']}, Sub_ID:{entry['sub_id']}, "
            f"Code_ID:{entry['code_id']}, Function_ID:{entry['function_id']}) to {output_file}: {e}"
        )
        raise

def list_files_in_directory(directory):
    """
    List all JSON files in the specified directory.
    """
    return [entry.name for entry in os.scandir(directory) if entry.is_file() and entry.name.endswith('.json')]

def get_functions_for_code(ground_truth_data, id, sub_id, code_id):
    """Get all functions from ground truth that belong to a specific code."""
    return [
        entry for entry in ground_truth_data
        if entry['id'] == id and 
           entry['sub_id'] == sub_id and 
           entry['code_id'] == code_id
    ]

def is_fully_processed(output_file, ground_truth_data):
    """
    Check if output file contains all functions from ground truth.
    """
    try:
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            return False
            
        with open(output_file, 'r') as f:
            output_data = json.load(f)

        if len(output_data) != len(ground_truth_data):
            return False

        # Verify all ground truth entries are in output
        output_keys = {
            (entry['id'], entry['sub_id'], entry['code_id'], entry['function_id'])
            for entry in output_data
        }
        ground_truth_keys = {
            (entry['id'], entry['sub_id'], entry['code_id'], entry['function_id'])
            for entry in ground_truth_data
        }
        
        return output_keys == ground_truth_keys
                   
    except Exception as e:
        logging.error(f"Error checking file processing status: {e}")
        return False

def find_resume_point(ground_truth_data, output_file):
    """
    Find the last processed function in the output file and return the index
    in ground truth to resume from.
    """
    if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
        return 0
        
    try:
        with open(output_file, 'r') as f:
            output_data = json.load(f)
            
        if not output_data:
            return 0
            
        # Get last processed entry
        last_processed = output_data[-1]
        
        # Find matching index in ground truth
        for idx, gt_entry in enumerate(ground_truth_data):
            if (gt_entry['id'] == last_processed['id'] and 
                gt_entry['sub_id'] == last_processed['sub_id'] and 
                gt_entry['code_id'] == last_processed['code_id'] and 
                gt_entry['function_id'] == last_processed['function_id']):
                return idx + 1  # Resume from next entry
                
        return 0  # If no match found, start from beginning
        
    except Exception as e:
        logging.warning(f"Error finding resume point: {e}. Starting from beginning.")
        return 0

def main():
    try:
        # Load ground truth data
        ground_truth_data = load_json_data(GROUND_TRUTH_PATH)
        logging.info(f"Loaded {len(ground_truth_data)} entries from ground truth")

        # Get list of input files
        input_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.json')]
        total_files = len(input_files)
        logging.info(f"Found {total_files} input files to process")

        # Process each input file
        for file_idx, input_file in enumerate(input_files, 1):
            input_path = os.path.join(INPUT_DIR, input_file)
            output_path = os.path.join(OUTPUT_DIR, input_file)
            
            percentage = (file_idx / total_files) * 100
            logging.info(f"Processing file {file_idx}/{total_files} ({percentage:.2f}%): {input_file}")
            
            # Check if file is already fully processed
            if is_fully_processed(output_path, ground_truth_data):
                logging.info(f"File {input_file} is already fully processed. Skipping.")
                continue
            
            # Load input data
            input_data = load_json_data(input_path)
            
            # Find resume point in ground truth
            resume_idx = find_resume_point(ground_truth_data, output_path)
            if resume_idx > 0:
                logging.info(f"Resuming from function {resume_idx + 1}/{len(ground_truth_data)}")
            
            # Process each ground truth entry from resume point
            for gt_idx, ground_truth_entry in enumerate(ground_truth_data[resume_idx:], resume_idx + 1):
                # Find matching input entry
                input_entry = next(
                    (entry for entry in input_data 
                     if entry['id'] == ground_truth_entry['id'] and 
                        entry['sub_id'] == ground_truth_entry['sub_id'] and 
                        entry['code_id'] == ground_truth_entry['code_id']),
                    None
                )
                
                entry_percentage = (gt_idx / len(ground_truth_data)) * 100
                logging.info(
                    f"File {file_idx}/{total_files} - "
                    f"Processing function {gt_idx}/{len(ground_truth_data)} ({entry_percentage:.2f}%) "
                    f"(ID: {ground_truth_entry['id']}, "
                    f"Sub_ID: {ground_truth_entry['sub_id']}, "
                    f"Code_ID: {ground_truth_entry['code_id']}, "
                    f"Function_ID: {ground_truth_entry['function_id']})"
                )

                if input_entry:
                    output_entry = process_entry(input_entry, ground_truth_entry)
                    append_to_output(output_path, output_entry)
                else:
                    logging.warning(f"No matching input entry found for ground truth entry")
                
            logging.info(f"Completed processing file {file_idx}/{total_files}: {input_file}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise

if __name__ == '__main__':
    main()
