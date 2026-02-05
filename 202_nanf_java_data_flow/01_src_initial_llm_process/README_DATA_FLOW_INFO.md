# Data Flow Information for LLM Vulnerability Function Localization

## Overview

This document describes the changes made to the LLM Vulnerability Function Localization code to use Data Flow information exclusively, completely replacing Abstract Syntax Tree (AST) information in the prompts sent to LLMs.

## Changes Made

1. **Modified Field Extraction**
   - Updated `extract_fields` function to extract only data flow info from the JSON object
   - Removed AST info from the return tuple

2. **Simplified Prompt Generation**
   - Modified `generate_prompt` function to only accept data flow info as a parameter
   - Removed all AST info related code
   - Set the section title in the prompt to "Data Flow Analysis"

3. **Removed Code Structure Extraction**
   - Completely removed the `extract_code_structure` function as it's no longer needed
   - Simplified the code by focusing only on data flow information

4. **Updated Main Processing Logic**
   - Modified `process_model` and `process_model_streaming` methods to only pass data flow info to the prompt generation

## Data Flow Information Structure

The data flow information is extracted from the input JSON objects and has the following structure:

```json
"data_flow_info": {
  "variable_declarations": [
    {
      "name": "input",
      "type": "String",
      "initializer": "request.getParameter(\"input\")",
      "location": {
        "method": "processInput",
        "class": "Vulnerable",
        "interface": null
      }
    }
  ],
  "variable_assignments": [
    {
      "expressionl": "this.data",
      "value": "input",
      "type": "=",
      "location": {
        "method": "processInput",
        "class": "Vulnerable",
        "interface": null
      }
    }
  ],
  "method_parameters": [
    {
      "name": "input",
      "type": "String",
      "method": "processInput",
      "location": {
        "method": "processInput",
        "class": "Vulnerable",
        "interface": null
      }
    }
  ],
  "return_statements": [
    {
      "expression": "result",
      "location": {
        "method": "processInput",
        "class": "Vulnerable",
        "interface": null
      }
    }
  ],
  "analysis_status": "success",
  "statistics": {
    "variable_declaration_count": 1,
    "assignment_count": 1,
    "parameter_count": 1,
    "return_statement_count": 1
  }
}
```

## Usage

The code now extracts the data flow information from the input JSON objects and includes it in the prompt sent to the LLM. This helps the LLM better understand the data flow within the code and identify vulnerable functions more accurately.

## Implementation Details

### Modified Functions

1. **extract_fields**
   - Now returns only the data flow info as part of the tuple
   - `code, filename, entry_id, sub_id, code_id, data_flow_info = extract_fields(entry)`

2. **generate_prompt**
   - Now only accepts data flow info as an optional parameter
   - Uses the provided data flow info exclusively
   - Always uses "Data Flow Analysis" as the section title

3. **Removed Functions**
   - Completely removed the `extract_code_structure` function
   - Simplified the code by focusing only on data flow information

## Benefits of Data Flow Analysis

Data flow analysis provides several advantages over AST information for vulnerability detection:

1. **Tracking Tainted Data**: Data flow analysis helps track how user input (potentially tainted data) flows through the application.

2. **Identifying Sinks**: It helps identify where tainted data is used in security-sensitive operations (sinks).

3. **Detecting Vulnerabilities**: By analyzing the flow of data, LLMs can better detect vulnerabilities like SQL injection, XSS, and command injection.

4. **Understanding Variable Usage**: It provides information about variable declarations, assignments, and usage throughout the code.

5. **Method Parameter Analysis**: It helps understand how parameters are passed between methods, which is crucial for tracking tainted data across method boundaries.

## Example Prompt

The prompt now exclusively uses data flow information:

```
Now, analyze the following java code:

### 1. Data Flow Analysis
```json
{
  "variable_declarations": [
    {
      "name": "input",
      "type": "String",
      "initializer": "request.getParameter(\"input\")",
      "location": {
        "method": "processInput",
        "class": "Vulnerable",
        "interface": null
      }
    }
  ],
  "variable_assignments": [
    {
      "expressionl": "this.data",
      "value": "input",
      "type": "=",
      "location": {
        "method": "processInput",
        "class": "Vulnerable",
        "interface": null
      }
    }
  ],
  "method_parameters": [
    {
      "name": "input",
      "type": "String",
      "method": "processInput",
      "location": {
        "method": "processInput",
        "class": "Vulnerable",
        "interface": null
      }
    }
  ],
  "return_statements": [
    {
      "expression": "result",
      "location": {
        "method": "processInput",
        "class": "Vulnerable",
        "interface": null
      }
    }
  ]
}
```

### 2. Full Source Code
```java
public class Vulnerable {
    private String data;

    public void processInput(String input) {
        this.data = input;
        // Process the input and return result
        return result;
    }
}
```
```
