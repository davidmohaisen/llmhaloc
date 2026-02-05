#!/bin/bash

# Script to create PEM certificates for HTTPS

echo "Creating PEM certificates for HTTPS..."

# Create certs directory if it doesn't exist
mkdir -p certs

# Create a configuration file for OpenSSL
cat > certs/openssl.cnf << EOL
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = localhost

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
IP.2 = 0.0.0.0
EOL

# Generate a private key and certificate in one step
echo "Generating private key and certificate..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout certs/key.pem -out certs/cert.pem \
    -config certs/openssl.cnf -extensions v3_req

# Set permissions
chmod 600 certs/key.pem
chmod 600 certs/cert.pem

echo "PEM certificates created successfully!"
echo "Key file: certs/key.pem"
echo "Certificate file: certs/cert.pem"

# Verify that the key and certificate match
echo "Verifying key and certificate match..."
KEY_MODULUS=$(openssl rsa -in certs/key.pem -noout -modulus | openssl md5)
CERT_MODULUS=$(openssl x509 -in certs/cert.pem -noout -modulus | openssl md5)

if [ "$KEY_MODULUS" = "$CERT_MODULUS" ]; then
    echo "✅ Verification successful: Key and certificate match!"
else
    echo "❌ Verification failed: Key and certificate do not match!"
    exit 1
fi

# Display minimal certificate information
echo "Certificate information:"
openssl x509 -in certs/cert.pem -noout -subject -issuer -dates | head -3
