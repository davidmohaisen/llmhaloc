# LLM Vulnerability Function Localization Web Processing

A modern web interface for processing and analyzing JSON files containing LLM responses for vulnerability function localization tasks. Features a frosted glass design for a clean, professional look.

## Features

- Process JSON files containing LLM responses
- Automatically classify function vulnerability using JSON parsing
- Two-stage user review for relevant functions (initial decision, then confirmation if auto-analysis disagrees or cannot be parsed)
- Automatic analysis results hidden by default and shown only during second-round review
- Prominent notifications for manual analysis requirements
- Audio and visual alerts for required user actions
- Track processing progress
- Side-by-side comparison of function code and LLM response
- Syntax highlighting for code blocks
- Collapsible metadata sections with keyboard shortcuts
- Responsive design for all device sizes
- Modern frosted glass UI with light, translucent colors
- Distinct button colors for better visual cues
- Improved text wrapping for long LLM responses
- Robust error handling and validation
- Enhanced JSON parsing for escaped characters
- Incremental output writing as decisions are made (results are written on the fly)

## Project Structure

```
├── 00_logs/                  # Log files
├── config/                   # Configuration files
│   └── config.yaml           # Main configuration file
├── static/                   # Static web assets
│   ├── src/                  # Source files for CSS
│   │   └── styles.css        # Tailwind CSS source
│   ├── script.js             # JavaScript for the web interface
│   └── styles.css            # Compiled CSS (generated)
├── templates/                # HTML templates
│   └── index.html            # Main page template
├── utils/                    # Utility modules
│   ├── __init__.py           # Package initialization
│   ├── config_manager.py     # Configuration management
│   ├── json_processor.py     # JSON processing utilities
│   ├── logging_manager.py    # Logging utilities
│   └── ui_manager.py         # UI status tracking
├── main.py                   # FastAPI application
├── requirements.txt          # Python dependencies
├── package.json              # Node.js dependencies
├── tailwind.config.js        # Tailwind CSS configuration
├── postcss.config.js         # PostCSS configuration
├── start.sh                  # Startup script
└── README.md                 # Project documentation
```

## Installation

### Prerequisites

- Python 3.10+
- Node.js 16+ (for Tailwind CSS)
- npm 8+ (for Tailwind CSS)

### Dependencies

- FastAPI: Web framework
- Tailwind CSS 4.1: Utility-first CSS framework
- highlight.js: Syntax highlighting for code blocks
- jQuery: DOM manipulation

### Setup

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Install Node.js dependencies:

   ```bash
   npm install
   ```

4. Configure the application:
   - Edit `config/config.yaml` to set input/output directories and other settings

## Usage

1. Start the application:

   ```bash
   ./start.sh
   ```

2. Open a web browser and navigate to:

   ```
   http://localhost:8080
   ```

3. Click "Start Processing" to begin processing JSON files

4. Review each function using the code and LLM response. If a second-round review is required, the automatic analysis block appears for confirmation.

5. Use the following keyboard shortcuts for faster workflow:
   - `Q`: Mark current function as "Not Vulnerable"
   - `W`: Mark current function as "Vulnerable"
   - `S`: Submit decision
   - `M`: Toggle status metadata section
   - `D`: Toggle detailed metadata section

## Configuration

The application is configured using the `config/config.yaml` file:

```yaml
directories:
  input: "../08_function_analysis_results" # Input directory containing JSON files
  output: "../10_function_results" # Output directory for processed files
  logs: "00_logs" # Directory for log files

server:
  host: "0.0.0.0" # Server host
  port: 8080 # Server port

logging:
  level: "DEBUG" # Logging level
  format: "%(asctime)s - %(levelname)s - %(message)s" # Log format
  file_rotation: true # Enable log file rotation
  max_bytes: 10485760 # Maximum log file size (10MB)
  backup_count: 5 # Number of backup log files

ui:
  title: "Function Analysis Dashboard" # UI title
  refresh_interval: 1000 # UI refresh interval in milliseconds
  cache_busting: true # Enable cache busting
  theme:
    use_frosted_glass: true # Enable frosted glass effect
    code_highlighting: true # Enable syntax highlighting for code blocks
    side_by_side_layout: true # Enable side-by-side layout for function and response
```

## Development

### Building CSS

To build the CSS files:

```bash
npm run build:css
```

This will watch for changes in the source CSS files and rebuild them automatically.

### Running in Development Mode

```bash
npm run dev
```

This will start both the Tailwind CSS build process and the FastAPI server with hot reloading.
