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


def extract_java_package(lines):
    """
    Extract package declaration from Java code.

    Args:
        lines (list): Lines of code to analyze

    Returns:
        str: Package name or empty string if not found
    """
    for line in lines:
        if line.strip().startswith('package '):
            return line.strip().replace('package ', '').replace(';', '')
    return ""

def extract_java_imports(lines):
    """
    Extract import declarations from Java code.

    Args:
        lines (list): Lines of code to analyze

    Returns:
        list: List of imported packages/classes
    """
    imports = []
    for line in lines:
        if line.strip().startswith('import '):
            imports.append(line.strip().replace('import ', '').replace(';', ''))
    return imports

def split_with_generics(text, delimiter=','):
    """
    Split text by delimiter while respecting generic type brackets.

    Args:
        text (str): Text to split
        delimiter (str): Delimiter character

    Returns:
        list: List of split parts
    """
    if not text or text.strip() == "":
        return []

    parts = []
    current_part = ""
    angle_bracket_count = 0

    for char in text:
        if char == '<':
            angle_bracket_count += 1
            current_part += char
        elif char == '>':
            angle_bracket_count -= 1
            current_part += char
        elif char == delimiter and angle_bracket_count == 0:
            parts.append(current_part.strip())
            current_part = ""
        else:
            current_part += char

    if current_part:
        parts.append(current_part.strip())

    return parts

def parse_parameters(params_str):
    """
    Parse method parameters string into structured format.

    Args:
        params_str (str): Parameter string from method signature

    Returns:
        list: List of parameter dictionaries with name and type
    """
    if not params_str or params_str.strip() == "":
        return []

    # Split parameters by comma
    param_parts = split_with_generics(params_str)
    params = []

    for part in param_parts:
        part = part.strip()
        if not part:
            continue

        # Handle the parameter
        words = part.split()
        if len(words) >= 2:
            param_type = ' '.join(words[:-1])
            param_name = words[-1]
            params.append({
                "name": param_name,
                "type": param_type
            })
        elif len(words) == 1:
            # Sometimes parameter names might be missing in method signatures
            params.append({
                "name": "",
                "type": words[0]
            })

    return params

def extract_access_modifier(line):
    """Extract access modifier from a line of code."""
    for modifier in ["public", "private", "protected"]:
        if re.search(r'\b' + modifier + r'\b', line):
            return modifier
    return ""

def extract_other_modifier(line):
    """Extract other modifier from a line of code."""
    for modifier in ["static", "final", "abstract", "synchronized"]:
        if re.search(r'\b' + modifier + r'\b', line):
            return modifier
    return ""

def extract_java_method(line):
    """
    Extract method information from a line of Java code.

    Args:
        line (str): Line of code to analyze

    Returns:
        dict: Method information or None if not a method
    """
    # Skip lines that end with semicolon (interface method declarations)
    if line.strip().endswith(';') and "interface" not in line:
        return None

    # Improved method pattern to match Java method signatures
    # This pattern matches methods with modifiers like public, private, etc.
    method_pattern = r'(?:public|private|protected)?\s*(?:static|final|abstract)?\s*(\w+)\s+(\w+)\s*\((.*?)\)'
    match = re.search(method_pattern, line)

    if not match:
        return None

    # Extract basic parts
    return_type = match.group(1)
    method_name = match.group(2)
    parameters_str = match.group(3)

    # Extract modifiers
    access_modifier = extract_access_modifier(line)
    other_modifier = extract_other_modifier(line)

    modifiers = []
    if access_modifier:
        modifiers.append(access_modifier)
    if other_modifier:
        modifiers.append(other_modifier)

    parameters = parse_parameters(parameters_str)

    # Create method info without body information yet
    # The body will be added later in process_class_body
    return {
        "name": method_name,
        "return_type": return_type,
        "parameters": parameters,
        "modifiers": modifiers
    }

def extract_field_modifiers(line):
    """Extract field modifiers from a line of code."""
    modifiers = []

    # Access modifiers
    for modifier in ["public", "private", "protected"]:
        if re.search(r'\b' + modifier + r'\b', line):
            modifiers.append(modifier)
            break

    # Other modifiers
    for modifier in ["static", "final", "volatile", "transient"]:
        if re.search(r'\b' + modifier + r'\b', line):
            modifiers.append(modifier)

    return modifiers

def extract_java_field(line):
    """
    Extract field information from a line of Java code.

    Args:
        line (str): Line of code to analyze

    Returns:
        dict: Field information or None if not a field
    """
    # Check if this is a field declaration (ends with semicolon)
    if not line.strip().endswith(';'):
        return None

    # Improved field pattern to match Java field declarations
    # This pattern matches fields with modifiers like private, public, etc.
    field_pattern = r'(?:private|public|protected)?\s*(?:static|final)?\s*(\w+)\s+(\w+)\s*(?:=.*)?\s*;'
    match = re.search(field_pattern, line)

    if not match:
        return None

    field_type = match.group(1)
    field_name = match.group(2)

    # Extract modifiers
    modifiers = extract_field_modifiers(line)

    return {
        "name": field_name,
        "type": field_type,
        "modifiers": modifiers
    }

def extract_class_definition(line):
    """
    Extract class or interface definition from a line of code.

    Args:
        line (str): Line of code to analyze

    Returns:
        dict: Class/interface information or None if not a class/interface
    """
    # Pattern to match class/interface definition
    class_pattern = r'(class|interface|enum)\s+(\w+)'
    match = re.search(class_pattern, line)

    if not match:
        return None

    type_name = match.group(1)
    class_name = match.group(2)

    # Extract modifiers
    modifiers = []
    for modifier in ["public", "private", "protected", "abstract", "final"]:
        if re.search(r'\b' + modifier + r'\b', line):
            modifiers.append(modifier)

    # Initialize class/interface
    return {
        "name": class_name,
        "type": "class" if type_name == "class" or type_name == "enum" else "interface",
        "modifiers": modifiers,
        "extends": "",
        "implements": [],
        "fields": [],
        "methods": []
    }

def extract_extends(line, class_info):
    """
    Extract extends relationship from a line of code.

    Args:
        line (str): Line of code to analyze
        class_info (dict): Class information to update

    Returns:
        dict: Updated class information
    """
    extends_pattern = r'extends\s+([\w\.]+)'
    match = re.search(extends_pattern, line)

    if match:
        class_info["extends"] = match.group(1).strip()

    return class_info

def extract_implements(line, class_info):
    """
    Extract implements relationship from a line of code.

    Args:
        line (str): Line of code to analyze
        class_info (dict): Class information to update

    Returns:
        dict: Updated class information
    """
    implements_pattern = r'implements\s+([\w\s,\.]+)'
    match = re.search(implements_pattern, line)

    if match:
        implements_str = match.group(1).strip()
        class_info["implements"] = split_with_generics(implements_str)

    return class_info

def find_class_opening_brace(lines, start_index):
    """
    Find the opening brace of a class or interface.

    Args:
        lines (list): Lines of code to analyze
        start_index (int): Index to start searching from

    Returns:
        int: Index of the opening brace
    """
    for i in range(start_index, len(lines)):
        if '{' in lines[i]:
            return i
    return start_index  # Default if not found


def handle_method_body(current_method, method_start_line, brace_count, i):
    """
    Handle method body tracking when a closing brace is found.

    Args:
        current_method (dict): Current method being tracked
        method_start_line (int): Start line of the method body
        brace_count (int): Current brace count
        i (int): Current line index

    Returns:
        tuple: (updated_method, should_add_method, updated_start_line)
    """
    # If we're tracking a method and the brace count indicates we're exiting the method
    if current_method is not None and brace_count == 1:  # 1 because we're still inside the class
        # Add body line numbers to the method
        current_method["body"] = {
            "start_line": method_start_line,
            "end_line": i
        }
        return current_method, True, 0

    return current_method, False, method_start_line


def handle_opening_brace(brace_count, current_method, method_start_line, i):
    """
    Handle opening brace tracking.

    Args:
        brace_count (int): Current brace count
        current_method (dict): Current method being tracked
        method_start_line (int): Start line of the method body
        i (int): Current line index

    Returns:
        tuple: (updated_brace_count, updated_method_start_line)
    """
    brace_count += 1

    # If we just found a method, this might be the start of its body
    if current_method is not None and method_start_line == 0:
        method_start_line = i + 1  # Start line is the next line after opening brace

    return brace_count, method_start_line


def handle_closing_brace(brace_count, current_method, method_start_line, i, methods):
    """
    Handle closing brace tracking.

    Args:
        brace_count (int): Current brace count
        current_method (dict): Current method being tracked
        method_start_line (int): Start line of the method body
        i (int): Current line index
        methods (list): List of methods to append to

    Returns:
        tuple: (updated_brace_count, updated_current_method, updated_method_start_line, is_class_end)
    """
    brace_count -= 1

    # Handle method body completion
    updated_method, should_add, updated_start_line = handle_method_body(
        current_method, method_start_line, brace_count, i
    )

    if should_add:
        methods.append(updated_method)
        current_method = None
        method_start_line = updated_start_line

    # Check if we're exiting the class
    is_class_end = (brace_count == 0)

    return brace_count, current_method, method_start_line, is_class_end


def process_class_body(lines, start_index):
    """
    Process the body of a class or interface.

    Args:
        lines (list): Lines of code to analyze
        start_index (int): Index to start processing from

    Returns:
        tuple: (fields, methods, end_index)
    """
    fields = []
    methods = []

    # Find the opening brace
    end_index = find_class_opening_brace(lines, start_index)
    brace_count = 1  # We found the opening brace

    current_method = None
    method_start_line = 0

    # Process the class body
    i = end_index + 1
    while i < len(lines):
        line = lines[i].strip()

        # Track opening braces
        if '{' in line:
            brace_count, method_start_line = handle_opening_brace(
                brace_count, current_method, method_start_line, i
            )

        # Track closing braces
        elif '}' in line:
            brace_count, current_method, method_start_line, is_class_end = handle_closing_brace(
                brace_count, current_method, method_start_line, i, methods
            )

            if is_class_end:
                end_index = i
                break

        # Extract methods - only capture the signature here
        elif current_method is None:  # Only start tracking a new method if we're not already tracking one
            method = extract_java_method(line)
            if method:
                current_method = method

        # Extract fields
        else:
            field = extract_java_field(line)
            if field:
                fields.append(field)

        i += 1

    return fields, methods, end_index

def extract_java_class_or_interface(lines):
    """
    Extract class and interface definitions from Java code.

    Args:
        lines (list): Lines of code to analyze

    Returns:
        tuple: Lists of classes and interfaces
    """
    classes = []
    interfaces = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for class/interface definitions
        class_info = extract_class_definition(line)
        if class_info:
            # Extract extends and implements
            class_info = extract_extends(line, class_info)
            class_info = extract_implements(line, class_info)

            # Process class body
            fields, methods, end_index = process_class_body(lines, i)

            # Update class info
            class_info["fields"] = fields
            class_info["methods"] = methods

            # Add to appropriate list
            if class_info["type"] == "class":
                classes.append(class_info)
            else:
                interfaces.append(class_info)

            # Skip to end of class
            i = end_index

        i += 1

    return classes, interfaces

# C/C++ related code has been removed as per requirements

def extract_java_structure(lines, filename):
    """
    Extract structure from Java code.

    Args:
        lines (list): Lines of code to analyze
        filename (str): Name of the source file

    Returns:
        dict: Structure information
    """
    # Extract basic structure
    classes, interfaces = extract_java_class_or_interface(lines)

    # Calculate statistics
    class_count = len(classes)
    method_count = sum(len(cls.get("methods", [])) for cls in classes)
    field_count = sum(len(cls.get("fields", [])) for cls in classes)
    interface_count = len(interfaces)
    interface_method_count = sum(len(iface.get("methods", [])) for iface in interfaces)

    # Format parameters for each method to match the expected format
    for cls in classes:
        methods = cls.get("methods", [])
        for method in methods:
            # Convert parameters from list of dicts to list of names
            if "parameters" in method:
                param_names = [param.get("name", "") for param in method["parameters"]]
                method["parameters"] = param_names

    # Create the AST info structure
    ast_info = {
        "package": extract_java_package(lines),
        "imports": extract_java_imports(lines),
        "classes": classes,
        "interfaces": interfaces,
        "analysis_status": "success",
        "statistics": {
            "class_count": class_count,
            "method_count": method_count,
            "field_count": field_count,
            "interface_count": interface_count,
            "interface_method_count": interface_method_count
        }
    }

    # Create the full structure with file path and ast_info
    structure = {
        "file_path": filename,
        "ast_info": ast_info
    }

    return structure





def generate_prompt(code, filename, data_flow_info=None):
    """
    Generates a markdown prompt template for analyzing code vulnerabilities.
    Includes data flow information to assist with vulnerability detection and localization.

    Args:
        code (str): The source code to analyze
        filename (str): Source file name to determine language
        data_flow_info (dict, optional): Pre-extracted data flow information

    Returns:
        str: A markdown formatted prompt template.
    """
    language = get_language_from_filename(filename)

    # Extract code structure using the provided data flow info
    structure = {"file_path": filename, "data_flow_info": data_flow_info} if data_flow_info else {"file_path": filename, "data_flow_info": {}}

    # Extract the data flow info for the prompt
    data_flow_info = structure.get("data_flow_info", {})

    # Convert to JSON string with indentation for readability
    info_json = json.dumps(data_flow_info, indent=2)

    section_title = "Data Flow Information"

    template = f"""Now, analyze the following {language} code:

### 1. {section_title}
```json
{info_json}
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

    # Print prompts if verbose mode is enabled
    if config.get('verbose', False):
        logger.separator("=", 80)
        logger.info("VERBOSE MODE: Printing System Prompt")
        logger.separator("-", 80)
        print(system_prompt)
        logger.separator("-", 80)
        logger.info("VERBOSE MODE: Printing User Prompt")
        logger.separator("-", 80)
        print(custom_prompt)
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
        tuple: A tuple containing the code, filename, identification fields, and data flow info.
    """
    code = entry.get('code', '')
    filename = entry.get('filename', '')
    entry_id = entry.get('id', 'Unknown')
    sub_id = entry.get('sub_id', 'Unknown')
    code_id = entry.get('code_id', 'Unknown')
    data_flow_info = entry.get('data_flow_info', None)
    return code, filename, entry_id, sub_id, code_id, data_flow_info


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
