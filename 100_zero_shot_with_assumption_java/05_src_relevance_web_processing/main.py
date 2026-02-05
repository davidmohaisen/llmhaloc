"""
Main application for the LLM Vulnerability Function Localization Web Processing System.

"""

import logging
import os
import threading
import time
from typing import Callable, Union

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Import utility modules
from utils.config_manager import config
from utils.json_processor import json_processor
from utils.logging_manager import log_manager
from utils.ui_manager import ui_manager

# Initialize logging
log_manager.initialize("app")
logger = logging.getLogger(__name__)

# Get version identifier for cache busting from config
VERSION = config.get_version()
logger.info(f"Application starting with version identifier: {VERSION}")

# Create FastAPI application
app = FastAPI(title="LLM Vulnerability Function Localization System")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Cache control middleware
class CacheControlMiddleware(BaseHTTPMiddleware):
    """Middleware to add cache control headers to responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add cache control headers
        if request.url.path.startswith("/static"):
            # For static files, use cache with version parameter for cache busting
            response.headers["Cache-Control"] = "public, max-age=31536000"  # 1 year
        else:
            # For API responses and HTML, no caching
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, max-age=0"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response


# Add cache control middleware
app.add_middleware(CacheControlMiddleware)


# Configure logging to reduce access log noise
# This will filter out the frequent polling requests
class AccessLogFilter(logging.Filter):
    """Filter to reduce access log noise from polling endpoints."""

    def __init__(self):
        super().__init__()
        self.polling_endpoints = {"/current_object", "/progress", "/processing_status"}
        self.last_logged = {}

    def filter(self, record):
        # Only filter uvicorn access logs
        if not record.name.startswith("uvicorn.access"):
            return True

        # Check if this is a polling endpoint
        for endpoint in self.polling_endpoints:
            if endpoint in record.getMessage():
                # Only log once every 10 seconds per endpoint
                current_time = time.time()
                last_time = self.last_logged.get(endpoint, 0)

                if current_time - last_time > 10:
                    self.last_logged[endpoint] = current_time
                    return True
                return False

        # Log all other requests
        return True


# Add the filter to the uvicorn.access logger
logging.getLogger("uvicorn.access").addFilter(AccessLogFilter())

# Set up templates and static files
templates_dir = config.get_templates_dir()
static_dir = config.get_static_dir()
templates = Jinja2Templates(directory=templates_dir)

# Add version to config for template access
config.set_version(VERSION)

# Mount static files with cache busting
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Processing thread
processing_thread = None


# Connect UI manager to JSON processor
def update_progress_callback(file_index, total_files, obj_index, total_objects):
    ui_manager.update_progress(file_index, total_files, obj_index, total_objects)


# Monkey patch the JSON processor's _notify_progress method
json_processor._notify_progress = update_progress_callback


class Decision(BaseModel):
    """Model for user decisions."""

    decision: Union[int, bool, str]  # Allow multiple types for decision


@app.get("/favicon.ico")
async def favicon():
    """Serve the favicon."""
    response = FileResponse(os.path.join(static_dir, "favicon.ico"))
    # Add cache control headers
    response.headers["Cache-Control"] = "public, max-age=31536000"  # 1 year
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main index page."""
    try:
        # Pass the config object to the template
        return templates.TemplateResponse(
            "index.html", {"request": request, "config": config}
        )
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)


@app.get("/start_processing")
async def start_processing():
    """Start the JSON processing thread."""
    global processing_thread
    if processing_thread is None or not processing_thread.is_alive():
        input_dir = config.get_input_dir()
        output_dir = config.get_output_dir()
        logger.info(
            f"Starting processing with input_dir={input_dir}, output_dir={output_dir}"
        )
        processing_thread = threading.Thread(
            target=json_processor.process_json_files, args=(input_dir, output_dir)
        )
        processing_thread.start()
        return {"status": "Processing started"}
    else:
        return {"status": "Processing already in progress"}


@app.get("/stop_processing")
async def stop_processing():
    """Stop the JSON processing thread."""
    global processing_thread
    if processing_thread and processing_thread.is_alive():
        if json_processor.is_currently_processing():
            # Signal the processor to stop
            json_processor.request_stop_processing()
            logger.info("Stop processing requested and signal sent")
            return {"status": "Processing stop requested"}
        else:
            # Thread is alive but not processing (might be finishing up)
            logger.info("Processing thread is alive but not actively processing")
            return {"status": "No active processing to stop"}
    else:
        logger.info("No processing thread running")
        return {"status": "No processing in progress"}


@app.get("/check_input_directory")
async def check_input_directory():
    """Check if the input directory exists and has files to process."""
    input_dir = config.get_input_dir()

    # Check if directory exists
    if not os.path.exists(input_dir):
        return {"exists": False, "file_count": 0, "processed_count": 0}

    # Count JSON files in directory
    json_files = [f for f in os.listdir(input_dir) if f.endswith(".json")]
    file_count = len(json_files)

    # Count processed files
    output_dir = config.get_output_dir()
    processed_count = 0
    if os.path.exists(output_dir):
        processed_files = [f for f in os.listdir(output_dir) if f.endswith(".json")]
        processed_count = len(processed_files)

    return {
        "exists": True,
        "file_count": file_count,
        "processed_count": processed_count,
    }


@app.get("/progress")
async def get_progress():
    """Get the current processing progress."""
    file_progress, total_progress = ui_manager.get_progress()
    return {
        "file_progress": file_progress,
        "total_progress": total_progress,
        "is_processing": json_processor.is_currently_processing(),
    }


@app.get("/processing_status")
async def get_processing_status():
    """Get the current processing status."""
    global processing_thread
    is_thread_alive = processing_thread is not None and processing_thread.is_alive()
    is_processing = json_processor.is_currently_processing()

    return {
        "thread_alive": is_thread_alive,
        "is_processing": is_processing,
        "current_file": json_processor.get_current_filename() or "None",
    }


@app.get("/current_object")
async def current_object():
    """Get the current object being processed."""
    obj = json_processor.get_current_object()

    if obj:
        # Create a copy to avoid modifying the original
        response_obj = dict(obj)
        response_obj["current_filename"] = json_processor.get_current_filename()

        # Get all identifiers for consistent logging
        obj_id = obj.get("id", "unknown")
        sub_id = obj.get("sub_id", "unknown")
        code_id = obj.get("code_id", "unknown")
        id_info = f"ID={obj_id}, Sub ID={sub_id}, Code ID={code_id}"

        # Add a flag to indicate if this object needs manual review
        needs_review = obj.get("relevance_label") is None
        response_obj["needs_manual_review"] = needs_review

        # Log only once when a new object is available for manual review
        if needs_review:
            logger.info(f"Object requiring manual review: {id_info}")
            logger.debug(
                f"Serving object for manual review: {id_info}, File: {json_processor.get_current_filename()}"
            )

        return response_obj
    else:
        # Return None without logging to reduce noise
        return None


@app.post("/submit_decision")
async def submit_decision(decision: Decision):
    """Submit a user decision for the current object."""
    try:
        # Get current object for better logging
        obj = json_processor.get_current_object()
        if obj:
            obj_id = obj.get("id", "unknown")
            sub_id = obj.get("sub_id", "unknown")
            code_id = obj.get("code_id", "unknown")
            id_info = f"ID={obj_id}, Sub ID={sub_id}, Code ID={code_id}"
        else:
            id_info = "unknown object"

        logger.info(f"Received decision for {id_info}: {decision.decision}")

        # Convert the decision to the correct type
        if isinstance(decision.decision, str):
            if decision.decision.lower() == "true":
                decision_value = True
                decision_str = "vulnerable"
            elif decision.decision.lower() == "false":
                decision_value = False
                decision_str = "not vulnerable"
            else:
                decision_value = int(decision.decision)
                decision_str = (
                    "not relevant"
                    if decision_value == -1
                    else f"unknown ({decision_value})"
                )
        else:
            decision_value = decision.decision
            decision_str = (
                "vulnerable"
                if decision_value == 1 or decision_value is True
                else "not vulnerable"
                if decision_value == 0 or decision_value is False
                else "not relevant"
                if decision_value == -1
                else f"unknown ({decision_value})"
            )

        logger.info(f"Converted decision for {id_info}: {decision_str}")
        json_processor.set_user_decision(decision_value)
        logger.info(f"Decision for {id_info} processed successfully")
        return {"status": "Decision received"}
    except Exception as e:
        # Try to get object info even in case of error
        obj = json_processor.get_current_object()
        id_info = "unknown object"
        if obj:
            id_info = f"ID={obj.get('id', 'unknown')}, Sub ID={obj.get('sub_id', 'unknown')}, Code ID={obj.get('code_id', 'unknown')}"

        logger.error(f"Error submitting decision for {id_info}: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/processed_status")
async def processed_status():
    """Get the status of processed objects."""
    status = json_processor.get_processed_status()
    return status


@app.get("/notifications")
async def get_notifications():
    """Get unread notifications."""
    notifications = ui_manager.get_unread_notifications()
    return notifications


# This file is meant to be run with uvicorn
# Use: uvicorn main:app --host 0.0.0.0 --port 8080
# Or use the start.sh script
