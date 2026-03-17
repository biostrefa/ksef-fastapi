# KSeF Certificates Setup

This document explains how to obtain and configure the required certificates for KSeF integration.

## Certificate Types

### 1. MF Public Encryption Certificate
- **Purpose**: Encrypts session symmetric keys for KSeF communication
- **Source**: Downloaded from KSeF API
- **Configuration**: `KSEF_MF_PUBLIC_ENCRYPTION_CERT_PATH`

### 2. XAdES Signing Certificate (`geosys.cert`)
- **Purpose**: Digital signature authentication
- **Source**: Generated in KSeF UI
- **Configuration**: `KSEF_XADES_SIGNING_CERT_PATH`

### 3. Private Key (`geosys.key`)
- **Purpose**: Paired with XAdES signing certificate
- **Source**: Generated in KSeF UI
- **Configuration**: `KSEF_PRIVATE_KEY_PATH`

## Downloading MF Public Certificate

### Method 1: Python Script
```bash
uv run python scripts/download_mf_certificate.py
```

### Method 2: Shell Script
```bash
./scripts/download_mf_certificate.sh
```

### Method 3: Manual Download
```bash
curl -s "https://api-test.ksef.mf.gov.pl/v2/security/public-key-certificates" | \
  jq -r '.[0].certificate' > certificates/mf_public_encryption_cert.pem
```

## Using KSeF UI Generated Certificates

### Step 1: Download from KSeF UI
1. Log into KSeF UI
2. Navigate to certificate management
3. Download your certificate and key files:
   - `geosys.cert` (certificate)
   - `geosys.key` (private key)

### Step 2: Convert to PEM Format
If the downloaded files are not in PEM format, convert them:

```bash
# Convert certificate to PEM (if needed)
openssl x509 -in geosys.cert -outform PEM -out certificates/xades_signing_cert.pem

# Convert private key to PEM (if needed)
openssl rsa -in geosys.key -outform PEM -out certificates/private_key.pem
```

### Step 3: Configure Environment
Update your `.env` file:
```bash
KSEF_MF_PUBLIC_ENCRYPTION_CERT_PATH=./certificates/mf_public_encryption_cert.pem
KSEF_XADES_SIGNING_CERT_PATH=./certificates/xades_signing_cert.pem
KSEF_PRIVATE_KEY_PATH=./certificates/private_key.pem
KSEF_PRIVATE_KEY_PASSWORD=your_password_if_protected
```

## Certificate Validation

The system automatically validates:
- Certificate file existence and format
- Private key file existence and permissions
- Certificate-key pair matching
- RSA key requirements for encryption

## Security Considerations

- Private key files should have restricted permissions (0600)
- Certificate files are excluded from Git via `.gitignore`
- Never commit certificate files to version control
- Store certificates in the `certificates/` directory

## Troubleshooting

### Certificate Parsing Errors
Ensure certificates are in proper PEM format with headers:
```
-----BEGIN CERTIFICATE-----
[certificate content]
-----END CERTIFICATE-----
```

### Permission Errors
Set proper permissions on private key:
```bash
chmod 600 certificates/private_key.pem
```

### Certificate-Key Mismatch
Verify that your signing certificate matches the private key:
```bash
openssl x509 -noout -modulus -in certificates/xades_signing_cert.pem | openssl md5
openssl rsa -noout -modulus -in certificates/private_key.pem | openssl md5
```

Both commands should produce the same MD5 hash.
