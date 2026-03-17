# KSeF CLI - Comprehensive Manual

## Environment Management

### List all profiles
```bash
uv run ksef profile list
```

### Switch between environments
```bash
# Switch to demo environment
uv run ksef profile set-active demo

# Switch to production environment
uv run ksef profile set-active production
```

### Check current active profile
```bash
uv run ksef profile show
```

### Create new profiles
```bash
# Demo profile
uv run ksef init --non-interactive --name demo --env DEMO --context-type nip --context-value 6793188868 --set-active

# Production profile
uv run ksef init --non-interactive --name production --env PROD --context-type nip --context-value 6793188868 --set-active
```

## Authentication

### Token Authentication (Demo/Testing)
```bash
uv run ksef auth login-token --ksef-token <KSEF_TOKEN>
uv run ksef auth status
uv run ksef profile show
```

### Certificate Authentication (Production)
```bash
# Secure method (recommended)
uv run ksef auth login-xades --pkcs12-path ./certificates/geosys.p12

# Using environment variable
source .env && uv run ksef auth login-xades --pkcs12-path ./certificates/geosys.p12 --pkcs12-password $PASSWORD

# Check authentication status
uv run ksef auth status
```

### Certificate Format Requirements
- **Format**: PKCS#12 (.p12 or .pfx files)
- **Content**: Certificate + private key in single file
- **Conversion**: Use OpenSSL if you have separate .cert/.key files:
```bash
openssl pkcs12 -export -out geosys.p12 -inkey geosys.key -in geosys.crt
```

### Session Management
```bash
# Check session status
uv run ksef auth status

# Refresh tokens
uv run ksef auth refresh

# Logout
uv run ksef auth logout
```

## Invoice Operations

### List Invoices
```bash
# Basic listing
uv run ksef invoice list --from 2026-01-01 --to 2026-01-31

# With pagination
uv run ksef invoice list --from 2026-03-01 --to 2026-03-17 --page-size 10

# With specific criteria
uv run ksef invoice list --from 2026-03-01 --to 2026-03-17 --subject-type nip --subject-value 6793188868
```

### Send Invoices
```bash
# Online session (single invoice)
uv run ksef send online --invoice ./fa.xml --wait-upo --save-upo ./out/upo-online.xml

# Batch session (multiple invoices)
uv run ksef send batch --zip ./invoices.zip --wait-upo --save-upo ./out/upo-batch.xml
```

### Download Invoices
```bash
# Download by KSeF number
uv run ksef invoice download --ksef-number <KSEF_NUMBER> --out ./out/

# Download by invoice number
uv run ksef invoice download --invoice-number <INVOICE_NUMBER> --out ./out/
```

### UPO (Urzędowe Poświadczenie Odbioru)
```bash
# Get UPO for specific invoice
uv run ksef upo get --ksef-number <KSEF_NUMBER> --out ./upo.xml

# Verify UPO
uv run ksef upo verify --upo-file ./upo.xml
```

## Lighthouse (Public Endpoints)

### Check KSeF Service Status
```bash
# Public status (no authentication required)
uv run ksef lighthouse status

# Service messages
uv run ksef lighthouse messages

# Test environment lighthouse
uv run ksef --env DEMO lighthouse status
```

## Profile Management

### Profile Operations
```bash
# Show current profile details
uv run ksef profile show

# List all available profiles
uv run ksef profile list

# Set active profile
uv run ksef profile set-active <profile_name>

# Update existing profile
uv run ksef profile update --name <profile_name> --context-value <new_nip>
```

### Profile Configuration
Each profile stores:
- Environment (DEMO/PROD)
- Base URL
- Context type (NIP/PESEL)
- Context value (NIP/PESEL number)
- Authentication tokens (if logged in)

## Advanced Usage

### Custom Base URLs
```bash
# Override default URL for specific command
uv run ksef --base-url https://custom.ksef.gov.pl invoice list

# Set custom URL in profile
uv run ksef init --name custom --base-url https://custom.ksef.gov.pl --context-type nip --context-value 1234567890
```

### Environment Variables
```bash
# Set environment variables for automation
export KSEF_CONTEXT_TYPE=nip
export KSEF_CONTEXT_VALUE=6793188868
export KSEF_BASE_URL=https://api.ksef.mf.gov.pl

# Use in commands
uv run ksef invoice list --from 2026-01-01 --to 2026-01-31
```

### Batch Operations
```bash
# Send multiple invoices from directory
uv run ksef send batch --directory ./invoices --wait-upo --save-upo ./out/

# Process with custom parallelism
uv run ksef send batch --zip ./invoices.zip --parallelism 8 --wait-upo
```

## Troubleshooting

### Common Issues

#### Certificate Authentication Fails
```bash
# Check certificate file
openssl pkcs12 -info -in certificates/geosys.p12 -noout

# Ensure correct environment (production certs need production env)
uv run ksef profile set-active production

# Check certificate expiration
openssl pkcs12 -in certificates/geosys.p12 -clcerts -noout -info
```

#### Token Expired
```bash
# Check token validity
uv run ksef auth status

# Refresh if needed
uv run ksef auth refresh

# Re-authenticate
uv run ksef auth login-xades --pkcs12-path ./certificates/geosys.p12
```

#### API Errors
```bash
# Use verbose output for debugging
uv run ksef --verbose invoice list --from 2026-01-01 --to 2026-01-31

# Check environment
uv run ksef profile show

# Verify network connectivity
uv run ksef lighthouse status
```

### Logging and Debugging
```bash
# Enable verbose logging
uv run ksef --verbose <command>

# Check logs directory
ls ~/.ksef/logs/

# Clear cache if needed
rm -rf ~/.ksef/cache/
```

## Security Best Practices

### Password Management
```bash
# Use secure prompt (recommended)
uv run ksef auth login-xades --pkcs12-path ./certificates/geosys.p12

# Use environment variables (less secure)
source .env && uv run ksef auth login-xades --pkcs12-path ./certificates/geosys.p12 --pkcs12-password $PASSWORD

# Never hardcode passwords in scripts
```

### Certificate Security
```bash
# Set proper permissions
chmod 600 certificates/geosys.p12
chmod 600 certificates/geosys.key
chmod 644 certificates/geosys.crt

# Store certificates in secure location
mkdir -p ~/.ksef/certificates/
mv certificates/geosys.p12 ~/.ksef/certificates/
```

### Environment Separation
```bash
# Use separate profiles for different environments
uv run ksef profile set-active demo    # For testing
uv run ksef profile set-active production  # For production

# Never use production certificates in demo environment
```

## Integration Examples

### Shell Script Automation
```bash
#!/bin/bash
# Auto-authenticate and send invoice

set -e

# Load environment
source .env

# Authenticate
uv run ksef auth login-xades --pkcs12-path ./certificates/geosys.p12 --pkcs12-password $PASSWORD

# Send invoice
uv run ksef send online --invoice ./invoice.xml --wait-upo --save-upo ./out/upo.xml

echo "Invoice sent successfully"
```

### Cron Job Setup
```bash
# Add to crontab for daily status check
0 9 * * * cd /path/to/ksef-client && uv run ksef auth status >> /var/log/ksef-status.log
```

## File Structure

### Directory Organization
```
ksef-client-python/
├── certificates/          # Certificate files
│   ├── geosys.p12         # PKCS#12 certificate
│   ├── geosys.crt         # Public certificate
│   └── geosys.key         # Private key
├── invoices/              # Input invoices
├── out/                   # Output files (UPO, downloads)
├── .env                   # Environment variables
└── .ksef/                 # CLI configuration and cache
    ├── profiles.json     # Profile configurations
    ├── tokens/           # Authentication tokens
    └── logs/             # CLI logs
```

### Configuration Files
- `~/.ksef/profiles.json` - Profile configurations
- `~/.ksef/tokens/` - Authentication tokens per profile
- `~/.ksef/logs/` - CLI operation logs
- `.env` - Local environment variables

## Help and Documentation

### Getting Help
```bash
# General help
uv run ksef --help

# Command-specific help
uv run ksef auth --help
uv run ksef invoice --help
uv run ksef send --help

# Subcommand help
uv run ksef auth login-xades --help
uv run ksef invoice list --help
```

### Documentation References
- Main documentation: `docs/README.md`
- API reference: `docs/api/README.md`
- Examples: `docs/examples/README.md`
- Error handling: `docs/errors.md`

---

**Note**: This manual covers the most common CLI operations. For advanced SDK usage and detailed API documentation, refer to the main documentation files in the `docs/` directory.
