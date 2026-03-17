#!/bin/bash
# Download MF public encryption certificate from KSeF API using curl

set -e

# Default KSeF test environment URL
KSEF_URL="${KSEF_BASE_URL:-https://api-demo.ksef.mf.gov.pl/v2}"
OUTPUT_PATH="${KSEF_MF_PUBLIC_ENCRYPTION_CERT_PATH:-./certificates/mf_public_encryption_cert.pem}"

echo "Downloading MF public certificate from: ${KSEF_URL}/security/public-key-certificates"
echo "Output path: $OUTPUT_PATH"

# Create output directory if it doesn't exist
mkdir -p "$(dirname "$OUTPUT_PATH")"

# Download certificate using curl and format with PEM headers
CERT_CONTENT=$(curl -s -f "${KSEF_URL}/security/public-key-certificates" | jq -r '.[0].certificate')

# Add PEM headers if not present
if [[ ! "$CERT_CONTENT" =~ "-----BEGIN CERTIFICATE-----" ]]; then
    CERT_CONTENT="-----BEGIN CERTIFICATE-----
$CERT_CONTENT
-----END CERTIFICATE-----"
fi

echo "$CERT_CONTENT" > "$OUTPUT_PATH"

echo "Certificate downloaded successfully to: $OUTPUT_PATH"

# Display certificate info
echo ""
echo "Certificate info:"
openssl x509 -in "$OUTPUT_PATH" -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After:)" || echo "Could not parse certificate info"
