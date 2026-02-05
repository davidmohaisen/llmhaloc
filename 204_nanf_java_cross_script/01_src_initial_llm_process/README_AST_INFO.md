# AST Information Extraction for LLM Vulnerability Function Localization

## Overview

This document describes the changes made to the LLM Vulnerability Function Localization code to extract and use the Abstract Syntax Tree (AST) information from the input JSON objects.

## Changes Made

1. **Removed C/C++ Related Code**
   - Removed all C/C++ related code from `llm_processor.py` as per requirements
   - Simplified the code to focus only on Java vulnerability localization

2. **Modified AST Extraction**
   - Updated `extract_code_structure` function to accept pre-extracted AST information
   - Modified `extract_fields` function to extract AST info from the JSON object
   - Updated `generate_prompt` function to use the extracted AST info

3. **Updated Main Processing Logic**
   - Modified `process_model` and `process_model_streaming` methods to pass AST info to the prompt generation

## AST Information Structure

The AST information is extracted from the input JSON objects and has the following structure:

```json
"ast_info": {
  "package": "com.example",
  "imports": ["java.util.List", "java.io.IOException"],
  "classes": [
    {
      "name": "Vulnerable",
      "extends": "Object",
      "implements": ["Serializable"],
      "methods": [
        {
          "name": "processInput",
          "return_type": "void",
          "parameters": ["input"],
          "modifiers": ["public"],
          "body": {
            "start_line": 10,
            "end_line": 20
          }
        }
      ],
      "fields": [
        {
          "name": "data",
          "type": "String",
          "modifiers": ["private"]
        }
      ]
    }
  ],
  "interfaces": [],
  "analysis_status": "success",
  "statistics": {
    "class_count": 1,
    "method_count": 1,
    "field_count": 1,
    "interface_count": 0,
    "interface_method_count": 0
  }
}
```

## Usage

The code now extracts the AST information from the input JSON objects and includes it in the prompt sent to the LLM. This helps the LLM better understand the structure of the code and identify vulnerable functions more accurately.

## Implementation Details

### Modified Functions

1. **extract_fields**
   - Now returns the AST info as part of the tuple
   - `code, filename, entry_id, sub_id, code_id, ast_info = extract_fields(entry)`

2. **generate_prompt**
   - Now accepts AST info as an optional parameter
   - Uses the provided AST info instead of generating a new one

3. **extract_code_structure**
   - Now accepts AST info as an optional parameter
   - Uses the provided AST info instead of generating a new one if available

### Removed Functions

The following C/C++ related functions have been removed:
- `extract_c_includes`
- `extract_c_function`
- `extract_c_functions`
- `extract_c_struct`
- `extract_c_structs`
- `extract_c_structure`


