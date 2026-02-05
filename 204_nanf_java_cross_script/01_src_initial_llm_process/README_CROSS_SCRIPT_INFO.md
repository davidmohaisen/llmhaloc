# Cross-Script Information for LLM Vulnerability Function Localization

## Overview

This document describes the changes made to the LLM Vulnerability Function Localization code to use cross-script information instead of AST information from the input JSON objects.

## Changes Made

1. **Removed AST-Related Code**
   - Removed all AST-related code from `llm_processor.py`
   - Simplified the code to focus on cross-script information

2. **Modified Information Extraction**
   - Updated `extract_fields` function to extract cross_script_info from the JSON object
   - Updated `generate_prompt` function to use the extracted cross_script_info

3. **Updated Main Processing Logic**
   - Modified `process_model` and `process_model_streaming` methods to pass cross_script_info to the prompt generation

## Cross-Script Information Structure

The cross-script information is extracted from the input JSON objects and has the following structure:

```json
"cross_script_info": {
  "imports": [
    {
      "path": "java.sql.Connection",
      "static": false,
      "wildcard": false
    }
  ],
  "class_inheritance": [
    {
      "class": "Vulnerable",
      "extends": "BaseProcessor"
    }
  ],
  "method_calls": [
    {
      "member": "executeQuery",
      "qualifier": "connection",
      "arguments": ["input"],
      "location": {
        "method": "processInput",
        "class": "Vulnerable",
        "interface": null
      }
    }
  ],
  "dependencies": ["java.sql.Connection", "java.sql.Statement"],
  "call_graph": {
    "callers": ["src/main/java/com/example/Controller.java"],
    "callees": ["src/main/java/com/example/Database.java"]
  },
  "analysis_status": "success",
  "statistics": {
    "import_count": 1,
    "inheritance_count": 1,
    "method_call_count": 1,
    "caller_count": 1,
    "callee_count": 1,
    "error_count": 0
  }
}
```

## Usage

The code now extracts the cross-script information from the input JSON objects and includes it in the prompt sent to the LLM. This helps the LLM better understand the relationships between different parts of the code and identify vulnerable functions more accurately.

## Implementation Details

### Modified Functions

1. **extract_fields**
   - Now returns the cross_script_info as part of the tuple
   - `code, filename, entry_id, sub_id, code_id, cross_script_info = extract_fields(entry)`

2. **generate_prompt**
   - Now accepts cross_script_info as an optional parameter
   - Uses the provided cross_script_info in the prompt

### Removed Functions

All AST-related functions have been removed, including:
- `extract_java_package`
- `extract_java_imports`
- `split_with_generics`
- `parse_parameters`
- `extract_access_modifier`
- `extract_other_modifier`
- `extract_java_method`
- `extract_field_modifiers`
- `extract_java_field`
- `extract_class_definition`
- `extract_extends`
- `extract_implements`
- `find_class_opening_brace`
- `handle_method_body`
- `handle_opening_brace`
- `handle_closing_brace`
- `process_class_body`
- `extract_java_class_or_interface`
- `extract_java_structure`
- `extract_c_structure`
- `extract_code_structure`


