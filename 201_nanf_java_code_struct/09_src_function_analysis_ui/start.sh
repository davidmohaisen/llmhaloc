#!/bin/bash

# Start script for LLM Vulnerability Function Localization Web Processing

# Make sure we're in the correct directory
cd "$(dirname "$0")"

# Function to sanitize output by removing sensitive paths
sanitize_output() {
    # Replace full paths with relative paths in the output
    sed 's|'"$(pwd)"'|.|g'
}

# Function to build Tailwind CSS
build_tailwind_css() {
    # Check if curl is installed
    if ! command -v curl &> /dev/null; then
        echo "Error: curl is not installed. Please install curl."
        return 1
    fi

    # Determine the platform and architecture
    PLATFORM="macos"
    ARCH="arm64"
    if [[ "$(uname)" == "Linux" ]]; then
        PLATFORM="linux"
        if [[ "$(uname -m)" == "x86_64" ]]; then
            ARCH="x64"
        fi
    elif [[ "$(uname)" == "Darwin" ]]; then
        PLATFORM="macos"
        if [[ "$(uname -m)" == "x86_64" ]]; then
            ARCH="x64"
        else
            ARCH="arm64"
        fi
    fi

    # Download the standalone Tailwind CSS CLI if it doesn't exist
    if [ ! -f "./tailwindcss" ]; then
        echo "Downloading Tailwind CSS standalone CLI for $PLATFORM-$ARCH..."
        curl -sLO "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-$PLATFORM-$ARCH"
        chmod +x "tailwindcss-$PLATFORM-$ARCH"
        mv "tailwindcss-$PLATFORM-$ARCH" tailwindcss
    fi

    # Build the CSS using the standalone CLI
    echo "Building Tailwind CSS..."
    ./tailwindcss -i ./static/src/styles.css -o ./static/styles.css

    echo "Tailwind CSS build complete!"
}

# Build Tailwind CSS
build_tailwind_css

# Generate SSL certificates
echo "Setting up SSL certificates..."

# Get the current directory (but don't display it)
CURRENT_DIR=$(pwd)
CERT_DIR="./certs"
KEY_FILE="$CERT_DIR/key.pem"
CERT_FILE="$CERT_DIR/cert.pem"

echo "Certificate directory: $CERT_DIR"
echo "Key file: $KEY_FILE"
echo "Certificate file: $CERT_FILE"

# Create PEM certificates using the dedicated script (redirect detailed output)
echo "Creating PEM certificates..."
./create_pem_certs.sh 2>&1 | sanitize_output | grep -v "Certificate information:" | grep -v "Subject Public Key Info:" | grep -v "Modulus:" | grep -v "total"

# Check if the certificates were generated
if [ -f "$CURRENT_DIR/$KEY_FILE" ] && [ -f "$CURRENT_DIR/$CERT_FILE" ]; then
    echo "✅ PEM certificates found and ready to use!"
else
    echo "❌ Failed to generate PEM certificates!"
fi

# Start Tailwind CSS watch process in the background
echo "Starting Tailwind CSS watch process..."
./tailwindcss -i ./static/src/styles.css -o ./static/styles.css --watch &
TAILWIND_PID=$!

# Trap to kill the Tailwind process when the script exits
trap "kill $TAILWIND_PID 2>/dev/null" EXIT

# Start the FastAPI application with HTTP for testing
echo "Starting FastAPI application with HTTP for testing..."
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload --log-level warning
