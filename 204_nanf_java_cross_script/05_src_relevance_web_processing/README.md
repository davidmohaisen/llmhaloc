# LLM Vulnerability Function Localization Web Processing System

This system provides a web interface for processing and analyzing JSON files containing LLM responses for vulnerability function localization tasks.

## System Overview

The system is designed to process JSON files containing LLM responses to vulnerability function localization tasks. It provides a web interface for manual analysis of responses that could not be automatically classified.

### Key Features

- Modern, responsive web interface using Tailwind CSS
- Dark mode support with system preference detection
- Cache busting for immediate layout updates
- HTTPS support with self-signed certificates
- Automated processing of JSON files
- Progress tracking and visualization
- Configurable via YAML configuration files
- Modular, object-oriented design

## Architecture

The system follows a modular, object-oriented architecture:

- **Configuration Management**: YAML-based configuration system
- **Logging**: Centralized logging with rotation support
- **JSON Processing**: Object-oriented JSON file processing
- **UI Management**: Progress tracking and notification system
- **Web Interface**: FastAPI-based web server with responsive UI

## Directory Structure

```
├── 00_logs/                  # Log files
├── certs/                    # SSL certificates for HTTPS
├── config/                   # Configuration files
│   └── config.yaml           # Main configuration file
├── static/                   # Static web assets
│   ├── script.js             # JavaScript for the web interface
│   └── styles.css            # CSS for the web interface (deprecated, using Tailwind)
├── templates/                # HTML templates
│   └── index.html            # Main page template with Tailwind CSS
├── utils/                    # Utility modules
│   ├── __init__.py           # Package initialization
│   ├── config_manager.py     # Configuration management
│   ├── json_processor.py     # JSON processing utilities
│   ├── logging_manager.py    # Logging utilities
│   └── ui_manager.py         # UI status tracking
├── cache_buster.py           # Cache busting script (generated at runtime)
├── version.txt               # Version identifier for cache busting (generated at runtime)
├── main.py                   # FastAPI application
├── requirements.txt          # Python dependencies
├── start.sh                  # Startup script
├── .gitignore                # Git ignore file
└── README.md                 # This documentation
```

## Setup and Installation

### Prerequisites

- Python 3.8 or higher
- FastAPI and Uvicorn

### Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Configuration

The system is configured via the `config/config.yaml` file. Key configuration options include:

- **directories**: Input/output directory paths
- **server**: Host and port settings
- **logging**: Log level and rotation settings
- **ui**: UI refresh intervals and display settings

### Cache Busting

The system implements automatic cache busting to ensure UI changes are immediately visible:

1. On startup, a unique version identifier is generated and stored in `version.txt`
2. This version is appended as a query parameter to all static resources
3. Cache control headers are set to allow long-term caching of static resources
4. The version changes on each startup, forcing browsers to load fresh resources

## Usage

### Starting the Application

Run the application using the provided shell script:

```
./start.sh
```

Alternatively, you can start it directly with Uvicorn:

```
uvicorn main:app --host 0.0.0.0 --port 8080
```

### Web Interface

Once started, access the web interface at:
- HTTPS: `https://localhost:8080` (recommended, requires accepting self-signed certificate)
- HTTP: `http://localhost:8080` (alternative)

The interface provides:
- Modern, responsive UI with Tailwind CSS
- Dark mode support (toggle in top-right corner)
- Start/stop controls for processing
- Progress indicators with percentage display
- Current object display with improved readability
- Decision buttons for manual classification with keyboard shortcuts
- Alert notifications for user feedback

### Processing Flow

1. Click "Start Processing" to begin
2. The system processes JSON files from the input directory
3. When an object requires manual classification, it is displayed in the UI
4. Select a classification (Vulnerable, Not Vulnerable, Not Relevant) and submit
5. Processing continues until all files are processed
6. Results are saved to the output directory

## Development

### Adding New Features

The modular design makes it easy to extend the system:

1. Add new utility modules to the `utils/` directory
2. Update the configuration schema in `config_manager.py` if needed
3. Modify the web interface in `templates/` and `static/` as required

### Logging

The system uses a centralized logging system:

```python
from utils.logging_manager import log_manager

# Get a logger for your module
logger = logging.getLogger(__name__)

# Log messages
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```
