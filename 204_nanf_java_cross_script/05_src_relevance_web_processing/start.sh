#!/bin/bash

# Start script for the LLM Vulnerability Function Localization Web Processing System

# Set up error handling
set -e

# Display banner
echo "=================================================="
echo "  LLM Vulnerability Function Localization System  "
echo "=================================================="
echo ""

# Create required directories if they don't exist
mkdir -p 00_logs
mkdir -p config

# Create a Python script to handle cache busting
echo "Setting up cache busting..."
cat > cache_buster.py << 'EOF'
#!/usr/bin/env python3
"""
Cache busting script for the LLM Vulnerability Function Localization Web Processing System.

"""

import os
import time
import random
import re

def update_version_in_config():
    """Update the version in the config file."""
    version = str(int(time.time())) + str(random.randint(1000, 9999))
    print(f"Generated new version identifier: {version}")

    # Create a version file that will be read by the application
    with open('version.txt', 'w') as f:
        f.write(version)

    print("Version file updated successfully.")
    return version

if __name__ == "__main__":
    update_version_in_config()
    print("Cache busting setup complete.")
EOF

# Make the script executable
chmod +x cache_buster.py

# Run the cache busting script
echo "Running cache busting script..."
python cache_buster.py

# Check if SSL certificates exist, if not, create self-signed certificates
CERT_DIR="./certs"
KEY_FILE="$CERT_DIR/key.pem"
CERT_FILE="$CERT_DIR/cert.pem"

if [ ! -d "$CERT_DIR" ]; then
    echo "Creating certificates directory..."
    mkdir -p "$CERT_DIR"
fi

if [ ! -f "$KEY_FILE" ] || [ ! -f "$CERT_FILE" ]; then
    echo "Generating self-signed SSL certificates..."
    openssl req -x509 -newkey rsa:4096 -keyout "$KEY_FILE" -out "$CERT_FILE" -days 365 -nodes -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:0.0.0.0"
    echo "SSL certificates generated."
fi

# Start the application using uvicorn with reload for development
echo "Starting the application..."
echo "Access the application at http://localhost:8080"

# Default to HTTP for local development (more compatible)
echo "Starting with HTTP for local development..."
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# Note: To use HTTPS, uncomment the following lines:
# if [ -f "$KEY_FILE" ] && [ -f "$CERT_FILE" ]; then
#     echo "Starting with SSL enabled..."
#     uvicorn main:app --host 0.0.0.0 --port 8080 --reload --ssl-keyfile="$KEY_FILE" --ssl-certfile="$CERT_FILE"
# else
#     echo "Starting without SSL (certificates not found)..."
#     uvicorn main:app --host 0.0.0.0 --port 8080 --reload
# fi

# Exit message
echo ""
echo "Application terminated."
