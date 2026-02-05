# LLM Vulnerability Response Analysis


## Purpose

This directory contains scripts for analyzing LLM responses to vulnerability function localization tasks. The system processes multiple JSON files containing LLM responses, analyzes them to determine their relevance to vulnerability identification, and outputs the analysis results.

## Project Goal

The goal of this project is to analyze the responses from Large Language Models (LLMs) to determine whether they correctly identify vulnerable functions in source code. The system:

1. Takes a directory of input files containing LLM responses
2. Processes each file with a single configured model
3. Analyzes each response to classify it as "vulnerable", "not vulnerable", or "not relevant"
4. Outputs the analysis results to a separate directory

This analysis helps benchmark different LLMs on their ability to correctly identify and localize vulnerabilities in code.

## System Architecture

The system follows an object-oriented design with clear separation of concerns:

```
03_src_relevance_llm_analysis/
├── archived/                   # Archived original scripts
│   └── 00_main.py              # Original main script (reference only)
├── config/                     # Configuration files
│   └── common.yaml             # Common configuration with all settings
├── utils/                      # Utility modules
│   ├── __init__.py             # Package initialization
│   ├── config_loader.py        # Configuration loading utilities
│   ├── data_handler.py         # Data loading and saving utilities
│   ├── llm_processor.py        # LLM interaction utilities
│   ├── logger.py               # Object-oriented logging system
│   └── time_estimator.py       # Dynamic time estimation utilities
└── main.py                     # Main driver script with LLMVulProcessor class
```

## Object-Oriented Design

The system uses a fully object-oriented approach:

- **LLMVulProcessor**: Main class that orchestrates the entire process
- **Logger**: Singleton class for centralized, consistent logging
- **Utility Modules**: Focused modules with specific responsibilities

## Scripts

### Main Driver

- `main.py` - Contains the LLMVulProcessor class and main entry point

### Utility Modules

- `utils/config_loader.py` - Loads configuration from YAML files
- `utils/logger.py` - Object-oriented logging system with consistent formatting
- `utils/data_handler.py` - Handles loading, saving, and processing data files
- `utils/llm_processor.py` - Handles interactions with LLMs and prompt generation
- `utils/time_estimator.py` - Provides dynamic time estimation for processing

### Configuration Files

- `config/common.yaml` - Single configuration file with all settings

### Archived Scripts (Not Used)
- `archived/00_main.py` - Original main script (reference only)

## Processing Flow

The LLMVulProcessor class handles the entire processing flow:

1. **Initialization**: Load configuration and set up logging
2. **Data Loading**: Load information about available input files
3. **Directory Processing**: Process all files in the input directory:
   - Check if each file has already been processed
   - Load each file and process its entries
   - Initialize time estimation for each file
   - Generate analysis prompts for each response
   - Send prompts to the LLM for analysis
   - Track processing time for each entry
   - Save results to output files
   - Display progress and time estimates
4. **Completion Reporting**: Report statistics on processed files

### Time Estimation System

The system provides dynamic time estimation at multiple levels:

1. **Entry-Level**: Tracks processing time for individual entries within each file
2. **File-Level**: Estimates time to complete the current file based on average entry processing time
3. **Overall-Level**: Tracks total processing time for all files
4. **Visual Feedback**: Displays time estimates in the console with detailed progress indicators
5. **Persistent Storage**: Saves processing times to files for future reference and initial estimates

### Stop and Resume System

The system implements a comprehensive stop and resume mechanism:

1. **File-Level Resume**: Automatically skips files that have already been fully processed
2. **Entry-Level Resume**: Resumes processing from the last successfully processed entry within a file
3. **Persistent Resume Points**: Saves resume points after each entry is processed
4. **Automatic Detection**: Automatically detects and uses the appropriate resume point
5. **Graceful Interruption**: Can be stopped at any time and will resume from the last saved point

## Input Data

The system processes JSON files from the input directory, which contain:
- LLM responses to vulnerability function localization tasks
- Metadata including ID, sub_ID, and code_ID
- Performance metrics from the original LLM processing

## Output Format

Results are saved in the configured output directory with the same filenames as the input files. Each file contains an array of entries with:
- Original metadata (ID, sub_ID, code_ID)
- Original LLM response
- Relevance analysis (classification and reasoning)
- Performance metrics (processing time, token counts)

## Features

- **Object-Oriented Design**: Clean, maintainable code with clear responsibilities
- **Single Configuration File**: All settings in one YAML file
- **Fully Configurable LLM Settings**: All Ollama API parameters configurable from the config file
- **Enhanced Error Logging**: Errors and warnings are saved to a dedicated log file with detailed stack traces
- **Robust Logging System**: Multiple fallback mechanisms ensure errors are always captured
- **Centralized Logger**: Singleton Logger class for consistent logging across all modules
- **Local Logs**: Log files are stored in a subfolder within the source code directory
- **Directory-Based Processing**: Processes all files in an input directory
- **Detailed Progress Tracking**: Visual progress indicators and percentage completion
- **Dynamic Time Estimation**: Accurate time estimates for processing at entry, file, and overall levels
- **Stop and Resume Capability**: Can be stopped and resumed at any point, even within a file
- **Robust Error Handling**: Comprehensive error handling with detailed messages
- **Performance Metrics**: Records processing time and token counts
- **Verbose Mode**: Optional display of system and user prompts for debugging and analysis

## Recent Modifications

The system has been significantly updated from its original version:

1. **Directory-Based Processing**:
   - Changed from processing a single file to processing all files in a directory
   - Added functions to list and process files in a directory
   - Implemented file-specific output naming

2. **Single Model Configuration**:
   - Changed from using multiple models to using a single model for all files
   - Consolidated model configuration in the common.yaml file
   - Removed machine-specific configuration files

3. **Prompt Generation Improvements**:
   - Moved prompt building to the llm_processor module
   - Added a dedicated function for generating analysis prompts
   - Simplified the prompt generation process

4. **Configuration Enhancements**:
   - Made all Ollama API parameters configurable from the common.yaml file
   - Added model context window configuration
   - Simplified the configuration loading process

5. **Time Estimation Enhancements**:
   - Added entry-level time estimation for each file
   - Implemented persistent storage of processing times
   - Added detailed time estimates with completion predictions

6. **Stop and Resume Enhancements**:
   - Added entry-level resume capability within each file
   - Implemented persistent storage of resume points
   - Added automatic detection and use of resume points

7. **Enhanced Error Logging**:
   - Added dedicated error log file with detailed stack traces
   - Implemented multiple fallback mechanisms for error logging
   - Added direct file writing for critical errors

8. **Code Organization**:
   - Removed unused methods and imports
   - Simplified the main processing flow
   - Improved error handling and logging

## Dependencies

- Python 3.8+
- ollama
- colorama
- pyyaml
- json

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

### Configuration File (`config/common.yaml`)
- Input and output directories
- Logging configuration
- Model configuration (name and context window)
- Ollama API parameters (keep_alive, stream, format)
- Generation options (temperature, seed, etc.)
- System prompt

## Notes

- The system uses a single model for processing all files
- All configuration is in a single file (common.yaml)
- Processing can be interrupted and resumed at any time
- All errors are logged for troubleshooting
- The system is designed to be easily adaptable to future model improvements
