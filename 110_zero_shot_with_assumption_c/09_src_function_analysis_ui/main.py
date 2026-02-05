"""
FastAPI application for LLM Vulnerability Function Localization Web Processing.
"""

import os
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import threading
from pydantic import BaseModel
from typing import Optional

# Import utility modules
from utils.config_manager import config
from utils.logging_manager import logger
from utils.json_processor import (
    process_json_files, get_current_object, set_user_decision,
    get_current_filename, get_processed_status, reset_processing_state,
    get_decision_context
)
from utils.ui_manager import ui_manager, progress, reset_progress

# Create a timestamp for cache busting
CACHE_BUSTER = str(int(time.time()))

# Create a middleware to add cache control headers
class NoCacheMiddleware(BaseHTTPMiddleware):
    """Middleware to add cache control headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        """
        Add cache control headers to all responses.

        Args:
            request: The incoming request.
            call_next: The next middleware or route handler.

        Returns:
            The response with cache control headers added.
        """
        response = await call_next(request)

        # Add cache control headers to all responses
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        return response

# Create FastAPI app
app = FastAPI()

# Add the no-cache middleware
app.add_middleware(NoCacheMiddleware)

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount static files with cache busting
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global variables
processing_thread = None
processing_complete = False
last_processed_object = None

# Get input and output directories from config
INPUT_DIR = config.get_input_dir()
OUTPUT_DIR = config.get_output_dir()

# Define Pydantic models for request validation
class Decision(BaseModel):
    """Model for decision submission."""
    decision: int | bool | str  # Allow multiple types for decision

class ErrorLog(BaseModel):
    """Model for frontend error logging."""
    message: str
    source: str
    stack: Optional[str] = None

@app.get("/favicon.ico")
async def favicon():
    """Serve the favicon."""
    return FileResponse("static/favicon.ico")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main page."""
    try:
        # Pass the cache buster to the template
        return templates.TemplateResponse("index.html", {"request": request, "cache_buster": CACHE_BUSTER})
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)

# Certificate help routes removed as they're no longer needed with mkcert
# Certificates are automatically trusted by the system

@app.get("/start_processing")
async def start_processing():
    """Start processing JSON files."""
    global processing_thread, processing_complete, last_processed_object

    if processing_thread is None or not processing_thread.is_alive():
        # Reset processing state
        processing_complete = False
        last_processed_object = None

        # Reset UI progress and processing state
        reset_progress()
        reset_processing_state()

        # Start processing thread
        processing_thread = threading.Thread(target=process_json_files, args=(INPUT_DIR, OUTPUT_DIR))
        processing_thread.start()
        logger.info("Processing started")
        return {"status": "Processing started"}
    else:
        logger.warning("Processing already in progress")
        return {"status": "Processing already in progress"}

@app.get("/stop_processing")
async def stop_processing():
    """Stop processing JSON files."""
    global processing_thread
    if processing_thread and processing_thread.is_alive():
        # Implement a way to stop the processing thread safely
        logger.info("Processing stopped")
        return {"status": "Processing stopped"}
    else:
        logger.warning("No processing in progress")
        return {"status": "No processing in progress"}

@app.get("/progress")
async def get_progress():
    """Get the current progress."""
    global processing_complete, last_processed_object

    # Get the current progress
    current_progress = progress.get()

    # Check if processing is complete
    if (current_progress["total_files"] > 0 and
        current_progress["current_file_index"] == current_progress["total_files"] and
        current_progress["file_progress"] >= 100):
        if not processing_complete:
            processing_complete = True
            logger.debug("Processing marked as complete")

            # Make sure we have a last processed object
            if last_processed_object:
                logger.debug(f"Last processed object preserved: {last_processed_object.get('id', 'unknown')}")
            else:
                logger.warning("No last processed object available at completion")

    # Add processing_complete flag to the response
    current_progress["processing_complete"] = processing_complete

    return current_progress

@app.get("/current_object")
async def current_object():
    """Get the current object being processed."""
    global processing_complete, last_processed_object

    # If processing is complete and we have a last object, return it
    if processing_complete and last_processed_object:
        logger.debug("Processing complete, returning last processed object")
        response_obj = dict(last_processed_object)
        response_obj["manual_analysis_required"] = False
        response_obj["awaiting_user_decision"] = False
        response_obj["show_auto_analysis"] = False
        response_obj["decision_stage"] = None
        return response_obj

    obj = get_current_object()

    if obj:
        # Create a copy to avoid modifying the original
        response_obj = dict(obj)
        response_obj['current_filename'] = get_current_filename()
        decision_context = get_decision_context()
        response_obj["decision_stage"] = decision_context.get("decision_stage")
        response_obj["show_auto_analysis"] = decision_context.get("show_auto_analysis", False)
        response_obj["awaiting_user_decision"] = decision_context.get("awaiting_user_decision", False)
        response_obj["manual_analysis_required"] = response_obj["decision_stage"] == 2

        # Store this as the last processed object
        last_processed_object = response_obj

        return response_obj
    else:
        return None

@app.post("/submit_decision")
async def submit_decision(decision: Decision):
    """Submit a decision for the current object."""
    try:
        logger.info(f"Received decision: {decision.decision}")
        # Convert the decision to the correct type
        if isinstance(decision.decision, str):
            if decision.decision.lower() == 'true':
                decision_value = True
            elif decision.decision.lower() == 'false':
                decision_value = False
            else:
                decision_value = int(decision.decision)
        else:
            decision_value = decision.decision

        logger.info(f"Converted decision value: {decision_value}")
        set_user_decision(decision_value)
        logger.info("Decision set successfully")
        return {"status": "Decision received"}
    except Exception as e:
        logger.error(f"Error submitting decision: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/processed_status")
async def processed_status():
    """
    Endpoint that returns the list of processed files.

    Returns:
        list: List of dictionaries with {'filename': 'filename.json'} format.
    """
    try:
        # Get the processed files status using the function from json_processor.py
        status = get_processed_status()

        # The get_processed_status function should always return a list, but let's double-check
        if not isinstance(status, list):
            logger.warning(f"Invalid status format returned: {status}, converting to empty list")
            status = []

        # Ensure each item has the expected format and contains only the filename
        cleaned_status = []
        for item in status:
            if isinstance(item, dict) and 'filename' in item and isinstance(item['filename'], str):
                # Only include the filename, no other data
                cleaned_status.append({"filename": item['filename']})
            else:
                logger.warning(f"Invalid item in status: {item}, skipping")

        # Return the cleaned status list
        return cleaned_status
    except Exception as e:
        # If anything goes wrong, log it and return an empty list
        logger.error(f"Error in processed_status endpoint: {str(e)}")
        return []

@app.get("/clear_cache")
async def clear_cache():
    """
    Endpoint that forces a cache refresh by returning a new cache buster value.

    Returns:
        dict: A dictionary with the new cache buster value.
    """
    global CACHE_BUSTER
    # Generate a new cache buster timestamp
    CACHE_BUSTER = str(int(time.time()))
    # Update the UI manager's cache buster
    ui_manager.update_cache_buster()
    return {"cache_buster": CACHE_BUSTER, "status": "Cache cleared"}

@app.post("/log_frontend_error")
async def log_frontend_error(error_log: ErrorLog):
    """
    Endpoint to log frontend errors to a file.

    Args:
        error_log: ErrorLog object containing error details.

    Returns:
        dict: Status of the logging operation.
    """
    try:
        # Format the error message
        error_message = f"{error_log.source}: {error_log.message}"
        if error_log.stack:
            error_message += f"\nStack: {error_log.stack}"

        # Log the error
        logger.error(f"Frontend error: {error_message}")

        return {"status": "Error logged successfully"}
    except Exception as e:
        logger.error(f"Error logging frontend error: {str(e)}")
        return JSONResponse(content={"error": "Failed to log error"}, status_code=500)

if __name__ == '__main__':
    try:
        import uvicorn
        import os

        host = config.get_server_host()
        port = config.get_server_port()

        # Get absolute paths for SSL certificates
        current_dir = os.getcwd()
        ssl_keyfile = os.path.join(current_dir, "certs", "key.pem")
        ssl_certfile = os.path.join(current_dir, "certs", "cert.pem")

        logger.info("Looking for SSL certificates at:")
        logger.info(f"  - Key file: {ssl_keyfile}")
        logger.info(f"  - Cert file: {ssl_certfile}")

        if os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile):
            logger.info(f"PEM certificates found. Starting HTTPS server on {host}:{port}")
            try:
                uvicorn.run(
                    app,
                    host=host,
                    port=port,
                    ssl_keyfile=ssl_keyfile,
                    ssl_certfile=ssl_certfile
                )
            except Exception as e:
                logger.error(f"Error starting HTTPS server: {str(e)}")
                logger.warning("Falling back to HTTP server.")
                uvicorn.run(app, host=host, port=port)
        else:
            logger.warning(f"PEM certificates not found at {ssl_keyfile} and {ssl_certfile}")
            logger.warning("Starting server without HTTPS.")
            logger.info(f"Starting HTTP server on {host}:{port}")
            uvicorn.run(app, host=host, port=port)
    except Exception as e:
        logger.error(f"Error starting FastAPI app: {str(e)}")
