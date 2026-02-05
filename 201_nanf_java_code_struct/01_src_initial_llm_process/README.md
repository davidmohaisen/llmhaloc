# Initial LLM Processing for Vulnerability Function Localization


## Purpose

This directory contains scripts for the initial processing of code samples with Large Language Models (LLMs) to identify vulnerable functions. The scripts process a dataset of code samples, send them to various LLMs, and collect the responses for further analysis.

## System Architecture

The system follows an object-oriented design with clear separation of concerns:

```
01_src_initial_llm_process/
├── archived/                   # Archived original scripts
│   ├── 00_mac.py               # Original Mac script (reference only)
│   └── 01_studio.py            # Original Studio script (reference only)
├── config/                     # Configuration files
│   ├── common.yaml             # Common configuration shared across machines
│   ├── mac.yaml                # Mac-specific configuration (smaller models)
│   └── studio.yaml             # Studio-specific configuration (larger models)
├── utils/                      # Utility modules
│   ├── __init__.py             # Package initialization
│   ├── config_loader.py        # Configuration loading utilities
│   ├── data_handler.py         # Data loading and saving utilities with memory-efficient streaming
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

- `utils/config_loader.py` - Loads and merges configuration from YAML files
- `utils/logger.py` - Object-oriented logging system with consistent formatting
- `utils/data_handler.py` - Handles loading, saving, and processing data with memory-efficient streaming
- `utils/llm_processor.py` - Handles interactions with LLMs
- `utils/time_estimator.py` - Provides dynamic time estimation for processing

### Configuration Files

- `config/common.yaml` - Common configuration shared across all machines
- `config/mac.yaml` - Configuration specific to Mac machine (smaller models)
- `config/studio.yaml` - Configuration specific to Studio machine (larger models)

### Archived Scripts (Not Used)
- `archived/00_mac.py` - Original script for Mac environment (reference only)
- `archived/01_studio.py` - Original script for Studio environment (reference only)

## Processing Flow

The LLMVulProcessor class handles the entire processing flow:

1. **Initialization**: Load configuration and set up logging
2. **Data Loading**: Load the dataset metadata (for counting entries and initial estimates)
3. **Time Estimation**: Calculate initial time estimates based on previous runs
4. **Model Processing**: For each model in the machine's model list:
   - Check if the model has already processed all entries using dedicated resume point files
   - Find the resume point if processing was interrupted
   - Initialize the time estimator for this model
   - Stream and process each entry with the LLM (memory-efficient)
   - Save results to JSON files (memory-efficient)
   - Update time estimates after each entry
   - Update resume point files with time estimates after each successful processing
   - Display progress and time estimates
5. **Model Completion**: Report processing time for the model and update overall estimates
6. **Completion Reporting**: Report statistics on completed models and total processing time

### Resume Point System

The system uses lightweight JSON files to track processing progress:

- **Dedicated Files**: Each model has its own resume point file in the `00_logs/resume_points` directory
- **Rich Metadata**: Files contain processing index, completion status, timestamps, progress percentage, and time estimates
- **Efficient Resumption**: Quick resumption without scanning large result files
- **No Fallback Mechanism**: Relies solely on dedicated resume point files for accurate tracking

### Time Estimation System

The system provides dynamic time estimation at multiple levels:

- **Entry-Level**: Tracks processing time for individual entries and calculates averages
- **Model-Level**: Estimates time to complete the current model based on average entry processing time
- **Overall-Level**: Estimates time to complete all models based on progress and averages
- **Persistent Storage**: Saves processing times to files for future reference and initial estimates
- **Dynamic Updates**: Updates estimates as processing progresses for increasing accuracy
- **Visual Feedback**: Displays time estimates in the console with color-coded progress indicators

### Memory-Efficient Processing

The system implements memory-efficient processing for both reading and writing JSON data:

- **Streaming JSON Reading**: Processes JSON arrays one object at a time without loading the entire file
- **Efficient JSON Writing**: Appends entries to JSON files without reading the entire file
- **Minimal Memory Footprint**: Allows processing of datasets of any size, limited only by disk space
- **Backward Compatibility**: Maintains compatibility with the original in-memory processing approach

## Input Data

The scripts process data from the dataset file specified in the configuration, which contains:
- Code samples with potential vulnerabilities
- Metadata including ID, sub_ID, and code_ID
- Filenames for language detection

## Output Format

Results are saved in the configured results directory with one JSON file per model. Each file contains an array of entries with:
- Original metadata (ID, sub_ID, code_ID)
- LLM response text
- Performance metrics (processing time, token counts)

## Machine-Specific Configurations

Each machine configuration defines:
- Machine name and description
- List of models to process with their context window sizes

The system automatically detects which machine it's running on based on the hostname, or you can specify it explicitly with the `--machine` argument.

## Features

- **Object-Oriented Design**: Clean, maintainable code with clear responsibilities
- **YAML Configuration**: Easy-to-read configuration files
- **Consistent LLM Settings**: Ollama API options are consistent across all machines
- **Efficient Logging**: Only errors and warnings are saved to a log file, normal logs are only displayed in the console
- **Centralized Logger**: Singleton Logger class for consistent logging across all modules
- **Local Logs**: Log files are stored in a subfolder within the source code directory
- **Machine-Specific Processing**: Different models for different machines
- **Efficient Resume System**: Lightweight JSON files track processing progress for quick resumption
- **Detailed Progress Tracking**: Visual progress bars and percentage completion
- **Dynamic Time Estimation**: Accurate time estimates for processing at entry, model, and overall levels
- **Memory-Efficient Processing**: Streams JSON data to minimize memory usage for both reading and writing
- **Robust Error Handling**: Comprehensive error handling with detailed messages
- **Performance Metrics**: Records processing time and token counts
- **Verbose Mode**: Optional display of system and user prompts for debugging and analysis

## Dependencies

- Python 3.8+
- ollama
- colorama
- tqdm
- pyyaml
- argparse
- json

## Usage

```bash
# Activate the conda environment
conda activate llmvul

# Run with automatic machine detection
python main.py

# Run with explicit machine specification
python main.py --machine mac
python main.py --machine studio

# Run with verbose mode to display system and user prompts
python main.py --verbose

# Combine options
python main.py --machine mac --verbose
```

## Configuration

### Common Configuration (`config/common.yaml`)
- Data paths and file names
- Output directories (logs stored in local `00_logs` subfolder)
- Logging configuration (only errors and warnings saved to file)
- Ollama API options (consistent across all machines and models)
- System prompt

### Machine-Specific Configuration (`config/mac.yaml`, `config/studio.yaml`)
- Machine name and description
- List of models with context window sizes

## Notes

- The system prompt is consistent across all models
- Different machines process different sets of models
- Processing can be interrupted and resumed at any time
- All errors are logged for troubleshooting
