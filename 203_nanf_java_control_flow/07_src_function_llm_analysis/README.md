# LLMVUL: LLM Vulnerability Function Localization


## Overview

LLMVUL is a system for benchmarking Large Language Models (LLMs) on their ability to locate vulnerable functions within source code files. The system processes code samples with various LLMs, analyzes their responses, and evaluates their performance in identifying security vulnerabilities at the function level.

This project implements a robust, object-oriented architecture with comprehensive error handling, progress reporting, and resume capabilities to enable efficient processing of large datasets.

## System Architecture

The system follows a modular, object-oriented design with clear separation of concerns:

```
├── 00_logs/                    # Log directory for errors, warnings, and processing data
├── archived/                   # Archived original scripts (reference only)
├── config/                     # Configuration files
│   └── common.yaml             # Single configuration file with all settings
├── utils/                      # Utility modules
│   ├── config_loader.py        # Configuration loading utilities
│   ├── data_handler.py         # Data loading and saving utilities
│   ├── llm_processor.py        # LLM interaction utilities
│   ├── logger.py               # Enhanced logging system
│   ├── resume_manager.py       # Resume point management
│   └── time_estimator.py       # Dynamic time estimation utilities
└── main.py                     # Main driver script with LLMVulProcessor class
```

## Processing Pipeline

The system follows a hierarchical processing flow:

1. **Initialization**:
   - Load configuration from YAML files
   - Set up logging system with separate error and warning logs
   - Ensure required directories exist

2. **File-Level Processing**:
   - Scan input directory for JSON files to process
   - Check for existing resume points for each file
   - Track global progress across all files

3. **Function-Level Processing**:
   - For each file, process individual functions
   - Match ground truth entries with input entries
   - Process each function with the configured LLM
   - Track file-level progress for each function

4. **Output Generation**:
   - Save processed results to output files
   - Maintain the same filename structure as input
   - Include detailed metadata and analysis results

## Key Components

### Main Driver (`main.py`)

The `main.py` file contains the `LLMVulProcessor` class, which orchestrates the entire processing pipeline. It:

- Initializes the system with configuration and logging
- Loads data about available input files
- Processes each file and its functions
- Handles errors and provides progress reporting
- Manages the resume system for interrupted processing

### Logger System (`utils/logger.py`)

The logger provides a centralized, object-oriented logging system with:

- Separate error and warning log files
- Colorized console output for different message types
- Global and file-level progress reporting sections
- Fixed-width formatting for numerical values
- Clear section headers and visual organization

Example console output:
```
================================================================================
LLMVUL: VULNERABILITY FUNCTION LOCALIZATION
--------------------------------------------------------------------------------
Input directory: ../06_relevant_analysis_final_results
Using model: qwen3:32b-fp16
Error logs will be saved to: ./00_logs/errors.log
Warning logs will be saved to: ./00_logs/warnings.log
================================================================================

GLOBAL PROGRESS - Processing file 1/10
[  1/ 10] (  10.00%) Current file: llama3_70b_instruct.json
Average time per file:     0.00s
Elapsed: 0s              | Remaining: 0s              
Estimated completion time: Unknown

FILE PROGRESS - Processing function 1/250
[   1/ 250] (   0.40%) ID:1, Sub_ID:1, Code_ID:1, Function_ID:1
Processing rate:   0.00 functions/minute
Average time per function:     0.00s
Elapsed: 0s              | Remaining: 0s              
Estimated completion time: Unknown
```

### Time Estimation System (`utils/time_estimator.py`)

The time estimator provides dynamic time estimation at multiple levels:

- **GlobalTimeEstimator**: Tracks file-level processing times and estimates overall completion
- **TimeEstimator**: Tracks function-level processing times and estimates file completion
- Both estimators provide:
  - Running averages of processing times
  - Weighted averages giving more importance to recent times
  - Estimated completion times with timestamps
  - Progress percentages and rates (functions/minute, files/hour)

### Resume System (`utils/resume_manager.py`)

The `ResumeState` class manages the system's ability to stop and resume processing:

- Maintains persistent record of processing state in JSON files
- Tracks the last processed function using ID/sub_ID/code_ID/function_ID
- Enables resuming from the exact point of interruption
- Stores time estimates for accurate resumption
- Handles failed entries and completed files

### Data Handling (`utils/data_handler.py`)

The data handler provides utilities for:

- Loading JSON data from input files
- Ensuring required directories exist
- Listing available JSON files for processing
- Checking if files are fully processed
- Appending results to output files

### LLM Processing (`utils/llm_processor.py`)

The LLM processor handles:

- Generating prompts for vulnerability analysis
- Interacting with the configured LLM
- Processing responses and extracting relevant information
- Handling LLM-specific parameters and configurations

## Error Handling System

The system implements a robust error handling approach that:

1. **Records detailed error information**:
   - Logs errors with full traceback to the error log file
   - Creates timestamped error files with detailed information
   - Includes file and function identifiers in error messages

2. **Provides clear user feedback**:
   - Displays a prominent "SYSTEM HALTED" message in the console
   - Shows error details and stack trace with red highlighting
   - Provides clear instructions for resolving the issue

3. **Stops processing immediately**:
   - Raises exceptions instead of returning status codes
   - Ensures errors propagate to the top-level exception handler
   - Prevents the system from continuing with potentially corrupted data

4. **Preserves state for resuming**:
   - Maintains resume points for successful processing
   - Enables easy restart after fixing issues

Example error output:
```
================================================================================
SYSTEM HALTED: CRITICAL ERROR DETECTED
================================================================================
Error details: Critical error while processing function ID:1, Sub_ID:2, Code_ID:3, Function_ID:4:
Failed to process entry: Invalid JSON response

Stack trace:
Traceback (most recent call last):
  File "main.py", line 529, in run
    self.process_all_files()
  ...

INSTRUCTIONS FOR RESOLUTION:
1. Review the error details above and in the error log at: ./00_logs/errors.log
2. Fix the identified issue in the code or configuration
3. Restart the system by running: python main.py

The system has been halted and must be manually restarted after the issue is resolved.
```

## Recent Improvements

The system has been significantly enhanced with the following improvements:

### 1. Enhanced Logging System
- **Separated Log Files**: Error and warning logs are now stored in separate files
- **Detailed Context**: Log entries include file, line number, and position information
- **Overwrite Mode**: Log files are overwritten on each run for cleaner history
- **Colorized Output**: Console output uses color coding for different message types

### 2. Improved Progress Reporting
- **Dual-Level Progress**: Separate global and file-level progress sections
- **Fixed-Width Formatting**: Consistent numerical value display with alignment
- **Clear Section Headers**: Distinct visual separation between progress sections
- **Color-Coded Progress**: Progress indicators change color based on completion percentage

### 3. Dynamic Time Estimation
- **File-Level Estimation**: Added GlobalTimeEstimator for tracking file processing times
- **Function-Level Estimation**: Enhanced TimeEstimator for tracking function processing times
- **Running Averages**: Implemented weighted averages for more accurate estimates
- **Completion Timestamps**: Added estimated completion times with formatted timestamps

### 4. Robust Error Handling
- **Immediate Halting**: System stops immediately when errors occur
- **Detailed Error Logs**: Comprehensive error information with stack traces
- **User Instructions**: Clear guidance for resolving issues and restarting
- **Timestamped Error Files**: Separate error files for each critical error

### 5. Code Organization
- **Modular Design**: Clear separation of concerns with focused modules
- **Object-Oriented Approach**: Consistent use of classes with single responsibilities
- **Reduced Complexity**: Functions broken down to reduce cognitive complexity
- **Improved Documentation**: Comprehensive docstrings and comments

## Coding Guidelines

### Error Handling Approach

1. **Exception Propagation**:
   - Use exceptions for error handling rather than return codes
   - Raise specific exceptions with detailed error messages
   - Let exceptions propagate to the top-level handler for consistent handling

2. **Error Logging**:
   - Log errors with `exc_info=True` to capture stack traces
   - Include context information (file, function, IDs) in error messages
   - Use `logger.error()` for recoverable errors and `logger.critical()` for fatal errors

3. **User Feedback**:
   - Provide clear, actionable error messages
   - Include instructions for resolving common issues
   - Use color coding (red for errors, yellow for warnings)

### Logging Standards

1. **Log Levels**:
   - **DEBUG**: Detailed debugging information (not saved to files)
   - **INFO**: General information and progress updates (console only)
   - **WARNING**: Potential issues that don't stop processing (warning log file)
   - **ERROR**: Recoverable errors that affect a single function (error log file)
   - **CRITICAL**: Fatal errors that stop processing (error log file)

2. **Color Scheme**:
   - **Green**: Success messages, completed operations, high progress (>75%)
   - **Blue/Cyan**: Information, processing status
   - **Yellow**: Warnings, important notes, medium progress (25-75%)
   - **Red**: Errors, critical issues, low progress (<25%)
   - **Magenta**: Section headers, major process boundaries

3. **Formatting**:
   - Use fixed-width formatting for numerical values
   - Include timestamps in all log entries
   - Add file and line information for errors and warnings
   - Use separators to visually distinguish sections

### Progress Reporting Conventions

1. **Global Progress**:
   - Display file-level progress with current/total files
   - Show percentage completion with fixed-width formatting
   - Include average time per file and estimated completion time
   - Update after each file is processed

2. **File Progress**:
   - Display function-level progress with current/total functions
   - Include function identifiers (ID, sub_ID, code_ID, function_ID)
   - Show processing rate (functions per minute)
   - Update after each function is processed

### Documentation Requirements

1. **Function Docstrings**:
   - Include a brief description of the function's purpose
   - Document all parameters with types and descriptions
   - Specify return values with types and descriptions
   - Document exceptions that may be raised
   - Use consistent formatting across all docstrings

2. **Class Docstrings**:
   - Describe the class's purpose and responsibilities
   - Document class attributes and their types
   - Include examples of usage where appropriate
   - Document inheritance relationships

3. **Module Docstrings**:
   - Describe the module's purpose and contents
   - Document dependencies and relationships with other modules

### Code Organization Principles

1. **Single Responsibility**:
   - Each class should have a single, well-defined responsibility
   - Each function should do one thing and do it well
   - Break complex functions into smaller, focused functions

2. **Dependency Management**:
   - Use dependency injection where appropriate
   - Minimize circular dependencies
   - Make dependencies explicit in function signatures

3. **Consistent Naming**:
   - Use descriptive names for variables, functions, and classes
   - Follow consistent naming conventions (snake_case for functions/variables, PascalCase for classes)
   - Prefix private methods and attributes with underscore

4. **Error Handling**:
   - Use try/except blocks to handle specific exceptions
   - Avoid catching generic exceptions without re-raising
   - Include context information when re-raising exceptions

## Usage

```bash
# Activate the conda environment
conda activate llmvul

# Run the script
python main.py

# Run with verbose mode to display system and user prompts
python main.py --verbose
```

## Configuration

All configuration is stored in `config/common.yaml`, which includes:

- Input and output directories
- Model configuration (name and context window)
- Logging settings
- LLM-specific parameters
- System prompt for analysis

## Dependencies

- Python 3.8+
- colorama (for colored console output)
- pyyaml (for configuration loading)
- ollama (for LLM interaction)
