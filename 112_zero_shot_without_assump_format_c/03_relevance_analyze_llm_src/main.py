import logging
import os
from datetime import datetime
import json
import ollama

# Global Parameters
# Get the base directory (working directory)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get the experiment directory
EXPERIMENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configure directories
LOG_DIR = os.path.join(EXPERIMENT_DIR, "00_logs")
LOG_FILE_NAME = '03_relevance_analysis.log'
LOG_FILE_PATH = os.path.join(LOG_DIR, LOG_FILE_NAME)

# Input directory (previous script's output)
INPUT_DIR = os.path.join(EXPERIMENT_DIR, "02_initial_results")

# Output directory for analysis results
OUTPUT_DIR = os.path.join(EXPERIMENT_DIR, "04_relevant_analysis_results")

# Model configuration
MODEL_NAME = 'llama3.3:70b-instruct-q5_K_M'

SYSTEM_PROMPT = """
Role: LLM Vulnerability Response Verifier
Objective: Validate whether the response from the LLM adheres to the task of identifying vulnerable functions in the provided source code. Even if multiple instances of vulnerable functions are mentioned, your task is to provide one unified classification for the entire response.

Instructions:
1.	Review the Response: Carefully analyze the content provided by the LLM.
2.	Classify the Entire Response: Based on the overall content, classify the response into one of the following categories:
    •	“vulnerable”: At least one vulnerable function is explicitly stated, or the reasoning implies the presence of a vulnerability.
    •	“not vulnerable”: The response explicitly states that all the functions or code are not vulnerable. If explicit confirmation is missing, but the reasoning supports a lack of vulnerabilities, classify it as “not vulnerable.”
    •	“not relevant”: The response does not address the vulnerability status of the code or functions, either explicitly or implicitly.
3.	Provide Reasoning: Write a brief explanation to justify your classification. Reference any specific parts of the response (explicit statements or reasoning) that influenced your decision.

Output Format:
Return the output in JSON format as follows:

```json
{
  "result": "vulnerable | not vulnerable | not relevant",
  "reasoning": "A concise explanation referencing specific statements or reasoning in the LLM response to justify the single classification for the entire response."
}
```

Additional Notes
	•	Even if multiple instances of vulnerable or non-vulnerable functions are mentioned, provide only one classification for the entire response.
	•	Focus solely on the LLM’s adherence to identifying vulnerabilities and its reasoning process.
	•	Ensure your reasoning directly references content in the response that supports your final classification.

Clarifications
	•	“vulnerable” takes precedence if even one vulnerable function is identified explicitly or implicitly.
	•	If the response explicitly states no vulnerabilities exist or reasoning supports this, classify it as “not vulnerable”.
	•	If the response is unrelated to the task or ambiguous, classify it as “not relevant”.
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
    """
    Load and parse a JSON file into a Python dictionary.
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

def generate_prompt(input_response):
    """
    Generates a markdown prompt template for analyzing Java code vulnerabilities.
    """
    template = f"""Now, analyze the following response:
        ```
        {input_response}
        ```
    """
    return template

def extract_fields(entry):
    """
    Extracts 'response' fields from a single JSON object.
    """
    return entry.get('response', '')

def write_to_json(new_entry, file_name):
    """
    Writes a new JSON object to a file based on the model name.
    """
    filepath = os.path.join(OUTPUT_DIR, file_name)

    try:
        data = []
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            with open(filepath, 'r') as file:
                data = json.load(file)
        data.append(new_entry)

        with open(filepath, 'w') as file:
            json.dump(data, file, indent=4)
        logging.info(f"Appended data to {filepath}")
    except Exception as e:
        logging.error(f"Error writing data {filepath}: {e}")
        raise

def call_ollama_chat(model_name, custom_prompt):
    """
    Helper function to encapsulate the ollama.chat call.
    """
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
        options=OPTIONS,
        keep_alive=-1,
        stream=False,
        format='json'
    )

def process_json_entry(entry, assessment):
    """
    Process a single JSON entry and preserve existing metrics while adding relevance assessment.
    
    Args:
        entry: Original entry from previous script containing response and metrics
        assessment: New assessment of response relevance
        
    Returns:
        dict: Entry with preserved fields and new relevance assessment
    """
    # Preserve all original fields
    new_entry = {
        'id': entry.get('id'),
        'sub_id': entry.get('sub_id'),
        'code_id': entry.get('code_id'),
        'prompt_eval_count': entry.get('prompt_eval_count'),
        'prompt_eval_duration': entry.get('prompt_eval_duration'),
        'eval_count': entry.get('eval_count'),
        'eval_duration': entry.get('eval_duration'),
        'total_duration': entry.get('total_duration'),
        'load_duration': entry.get('load_duration'),
        'response': entry.get('response'),
        # Add new assessment field
        'relevance_analysis': assessment
    }
    return new_entry

def interact_with_llm(entry, custom_prompt):
    """
    Simulates interaction with an LLM based on provided prompts and model name.
    """
    try:
        logging.info(f"Attempting to interact with {MODEL_NAME} for the vulnerable code with ID: {entry.get('id')}")
        response = call_ollama_chat(MODEL_NAME, custom_prompt)
        logging.info(f"Got response from model {MODEL_NAME} for the vulnerable code with ID: {entry.get('id')}")
        return process_json_entry(entry, response['message']['content'])
    except Exception as e:
        logging.error(f"Error interacting with LLM for model {MODEL_NAME}: {e}")
        raise

def list_files_in_directory(directory):
    """
    List all JSON files in the specified directory.
    """
    return [entry.name for entry in os.scandir(directory) if entry.is_file() and entry.name.endswith('.json')]

def find_resume_point(input_data, output_data):
    """
    Find the resume point by matching IDs between input and output data.
    
    Returns:
    int: Index to resume from
    """
    if not output_data:
        return 0
        
    last_processed = output_data[-1]
    last_id = (
        last_processed.get('id'),
        last_processed.get('sub_id'),
        last_processed.get('code_id')
    )
    
    for idx, entry in enumerate(input_data):
        current_id = (
            entry.get('id'),
            entry.get('sub_id'),
            entry.get('code_id')
        )
        if current_id == last_id:
            return idx + 1
            
    return 0

def is_fully_processed(input_file, output_file):
    """
    Check if input file has been fully processed by comparing the last entry IDs.
    """
    try:
        with open(input_file, 'r') as infile, open(output_file, 'r') as outfile:
            input_data = json.load(infile)
            output_data = json.load(outfile)

            if not input_data or not output_data:
                return False

            last_input = input_data[-1]
            last_output = output_data[-1]
            
            return (last_input['id'] == last_output['id'] and 
                   last_input['sub_id'] == last_output['sub_id'] and 
                   last_input['code_id'] == last_output['code_id'])
    except FileNotFoundError:
        return False
    except Exception as e:
        logging.error(f"Error checking file processing status: {e}")
        return False

def main():
    try:
        list_of_filenames = list_files_in_directory(INPUT_DIR)
        list_of_outputs = list_files_in_directory(OUTPUT_DIR)

        for filename in list_of_filenames:
            input_path = os.path.join(INPUT_DIR, filename)
            output_path = os.path.join(OUTPUT_DIR, filename)
            
            # Load input data
            ori_json_data = load_json_data(input_path)
            total_entries = len(ori_json_data)

            if filename in list_of_outputs and is_fully_processed(input_path, output_path):
                logging.info(f"File {filename} is fully processed. Skipping.")
                continue

            processed_data = load_json_data(output_path) if filename in list_of_outputs else []
            resume_index = find_resume_point(ori_json_data, processed_data)
            
            logging.info(f"Resuming processing for {filename} from index {resume_index}/{total_entries}")

            for idx, entry in enumerate(ori_json_data[resume_index:], start=resume_index):
                id = entry.get('id', 'Unknown')
                sub_id = entry.get('sub_id', 'Unknown')
                code_id = entry.get('code_id', 'Unknown')
                
                logging.info(
                    f"Processing {filename} - Progress: {idx+1}/{total_entries} "
                    f"({((idx+1)/total_entries*100):.2f}%) "
                    f"- ID: {id}, Sub_ID: {sub_id}, Code_ID: {code_id}"
                )

                response = extract_fields(entry)
                custom_prompt = generate_prompt(response)

                try:
                    new_entry = interact_with_llm(entry, custom_prompt)
                    write_to_json(new_entry, filename)
                except Exception as e:
                    logging.error(
                        f"Failed processing {filename} - Index: {idx+1}/{total_entries} "
                        f"- ID: {id}, Sub_ID: {sub_id}, Code_ID: {code_id}: {e}"
                    )
                    continue

    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == '__main__':
    main()
