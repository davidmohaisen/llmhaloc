#!/bin/bash

# Script to test certificate generation

# Get the current directory
CURRENT_DIR=$(pwd)
CERT_DIR="$CURRENT_DIR/certs"
KEY_FILE="$CERT_DIR/key.pem"
CERT_FILE="$CERT_DIR/cert.pem"

echo "Certificate directory: $CERT_DIR"
echo "Key file: $KEY_FILE"
echo "Certificate file: $CERT_FILE"

# Create the certificate directory if it doesn't exist
if [ ! -d "$CERT_DIR" ]; then
    echo "Creating certificates directory..."
    mkdir -p "$CERT_DIR"
fi

# Generate the certificates
echo "Generating self-signed SSL certificates..."
openssl req -x509 -newkey rsa:4096 -keyout "$KEY_FILE" -out "$CERT_FILE" -days 365 -nodes -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:0.0.0.0"
chmod 600 "$KEY_FILE" "$CERT_FILE"

# Check if the certificates were generated
if [ -f "$KEY_FILE" ] && [ -f "$CERT_FILE" ]; then
    echo "Certificates generated successfully!"
    echo "Key file: $KEY_FILE"
    echo "Certificate file: $CERT_FILE"
    ls -la "$CERT_DIR"
else
    echo "Failed to generate certificates!"
fi

# Display certificate information
echo "Certificate information:"
openssl x509 -in "$CERT_FILE" -text -noout | head -20
