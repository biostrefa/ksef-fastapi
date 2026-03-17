# KSeF Authentication Testing Guide

This guide covers all implemented auth testing endpoints and includes a ready-to-run `curl` sequence for incremental debugging.

Base URL used below: `http://127.0.0.1:8033`

## Endpoint Map

### Step 1: XAdES bootstrap (first-time)
- `POST /api/testing/ksef/auth/step1/challenge`
- `POST /api/testing/ksef/auth/step1/init/xades-signature`
- `POST /api/testing/ksef/auth/step1/status`
- `POST /api/testing/ksef/auth/step1/redeem`
- Shortcut (orchestrated by `AuthService`): `POST /api/testing/ksef/auth/step1/redeem/xades`

### Step 2: Create reusable KSeF token
- `POST /api/testing/ksef/auth/step2/create-ksef-token`

### Step 3: Wait until token is active
- `POST /api/testing/ksef/auth/step3/token-status`
- `POST /api/testing/ksef/auth/step3/token-status/poll`

### Step 4: Daily login with KSeF token
- `POST /api/testing/ksef/auth/step1/challenge` (new challenge)
- `POST /api/testing/ksef/auth/step4/init/ksef-token`
- `POST /api/testing/ksef/auth/step4/status`
- `POST /api/testing/ksef/auth/step4/redeem`
- Shortcut (orchestrated by `AuthService`): `POST /api/testing/ksef/auth/step4/redeem/token`

### Context and maintenance
- `POST /api/testing/ksef/auth/context`
- `POST /api/testing/ksef/auth/context/revoke`
- `POST /api/testing/ksef/auth/refresh`

## Key and certificate checks

Run these commands before Step 1 to verify that the configured XAdES files are valid and match:

```bash
# from project root
CERT_PATH="./certificates/geosys.crt.pem"
KEY_PATH="./certificates/geosys.key.pem"
KEY_PASSWORD="mukzur-nyqpes-9rAtvy"

echo "=== check files exist ==="
ls -l "$CERT_PATH" "$KEY_PATH"

echo "=== parse certificate ==="
openssl x509 -in "$CERT_PATH" -noout -subject -issuer -dates

echo "=== parse private key ==="
openssl pkey -in "$KEY_PATH" -passin "pass:$KEY_PASSWORD" -noout

echo "=== verify cert-key pair match (RSA modulus) ==="
CERT_MD5=$(openssl x509 -noout -modulus -in "$CERT_PATH" | openssl md5 | awk '{print $2}')
KEY_MD5=$(openssl rsa -noout -modulus -in "$KEY_PATH" -passin "pass:$KEY_PASSWORD" | openssl md5 | awk '{print $2}')
echo "CERT_MD5=$CERT_MD5"
echo "KEY_MD5=$KEY_MD5"
test "$CERT_MD5" = "$KEY_MD5" && echo "MATCH: cert and key pair is valid" || echo "MISMATCH: cert and key do not match"
```

If `openssl pkey` fails with `bad decrypt` / `maybe wrong password`, the private key password is incorrect.

## Ready-to-run curl sequence

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://127.0.0.1:8033"
COMPANY_ID="123e4567-e89b-12d3-a456-426614174000"
ENVIRONMENT="test"
CONTEXT_ID_TYPE="Nip"
CONTEXT_ID_VALUE="6793188868"

echo "=== STEP 1.1: challenge ==="
STEP1_CHALLENGE_RESP=$(curl -sS -X POST "$BASE_URL/api/testing/ksef/auth/step1/challenge" \
  -H "Content-Type: application/json" \
  -d "{\"company_id\":\"$COMPANY_ID\",\"environment\":\"$ENVIRONMENT\"}")
echo "$STEP1_CHALLENGE_RESP"

# Copy challenge value from response.data.challenge
CHALLENGE="<PASTE_CHALLENGE_FROM_STEP_1_1>"

echo "=== STEP 1.2: init xades signature ==="
STEP1_INIT_RESP=$(curl -sS -X POST "$BASE_URL/api/testing/ksef/auth/step1/init/xades-signature" \
  -H "Content-Type: application/json" \
  -d "{\"challenge\":\"$CHALLENGE\",\"context_identifier_type\":\"$CONTEXT_ID_TYPE\",\"context_identifier_value\":\"$CONTEXT_ID_VALUE\"}")
echo "$STEP1_INIT_RESP"

# Copy from response.data
AUTH_REF="<PASTE_REFERENCE_NUMBER>"
AUTH_TEMP_TOKEN="<PASTE_AUTHENTICATION_TOKEN>"

echo "=== STEP 1.3: auth status ==="
curl -sS -X POST "$BASE_URL/api/testing/ksef/auth/step1/status" \
  -H "Content-Type: application/json" \
  -d "{\"reference_number\":\"$AUTH_REF\",\"authentication_token\":\"$AUTH_TEMP_TOKEN\"}"
echo

echo "=== STEP 1.4: redeem temporary token ==="
STEP1_REDEEM_RESP=$(curl -sS -X POST "$BASE_URL/api/testing/ksef/auth/step1/redeem" \
  -H "Content-Type: application/json" \
  -d "{\"authentication_token\":\"$AUTH_TEMP_TOKEN\"}")
echo "$STEP1_REDEEM_RESP"

# Copy access token from response.data.access_token
ACCESS_TOKEN="<PASTE_ACCESS_TOKEN_FROM_STEP_1_4>"

echo "=== STEP 2: create reusable KSeF token ==="
STEP2_RESP=$(curl -sS -X POST "$BASE_URL/api/testing/ksef/auth/step2/create-ksef-token" \
  -H "Content-Type: application/json" \
  -d "{\"access_token\":\"$ACCESS_TOKEN\",\"permissions\":[\"InvoiceRead\",\"InvoiceWrite\"],\"description\":\"Auth testing token\"}")
echo "$STEP2_RESP"

# Copy from response.data
KSEF_TOKEN_REF="<PASTE_KSEF_TOKEN_REFERENCE_NUMBER>"
KSEF_TOKEN_VALUE="<PASTE_KSEF_TOKEN_VALUE_SHOWN_ONCE>"

echo "=== STEP 3: token status poll ==="
curl -sS -X POST "$BASE_URL/api/testing/ksef/auth/step3/token-status/poll" \
  -H "Content-Type: application/json" \
  -d "{\"access_token\":\"$ACCESS_TOKEN\",\"reference_number\":\"$KSEF_TOKEN_REF\",\"attempts\":15,\"delay_seconds\":1.0}"
echo

echo "=== STEP 4.1: challenge ==="
STEP4_CHALLENGE_RESP=$(curl -sS -X POST "$BASE_URL/api/testing/ksef/auth/step1/challenge" \
  -H "Content-Type: application/json" \
  -d "{\"company_id\":\"$COMPANY_ID\",\"environment\":\"$ENVIRONMENT\"}")
echo "$STEP4_CHALLENGE_RESP"

# Copy challenge/timestamp from response.data
STEP4_CHALLENGE="<PASTE_CHALLENGE_FROM_STEP_4_1>"
STEP4_TIMESTAMP_MS="<PASTE_TIMESTAMP_MS_FROM_KSEF_CHALLENGE_ENDPOINT>"

echo "=== STEP 4.2: init auth with reusable ksef token ==="
STEP4_INIT_RESP=$(curl -sS -X POST "$BASE_URL/api/testing/ksef/auth/step4/init/ksef-token" \
  -H "Content-Type: application/json" \
  -d "{\"challenge\":\"$STEP4_CHALLENGE\",\"timestamp_ms\":$STEP4_TIMESTAMP_MS,\"ksef_token\":\"$KSEF_TOKEN_VALUE\",\"context_identifier_type\":\"$CONTEXT_ID_TYPE\",\"context_identifier_value\":\"$CONTEXT_ID_VALUE\"}")
echo "$STEP4_INIT_RESP"

# Copy from response.data
STEP4_AUTH_REF="<PASTE_REFERENCE_NUMBER>"
STEP4_AUTH_TEMP_TOKEN="<PASTE_AUTHENTICATION_TOKEN>"

echo "=== STEP 4.3: auth status ==="
curl -sS -X POST "$BASE_URL/api/testing/ksef/auth/step4/status" \
  -H "Content-Type: application/json" \
  -d "{\"reference_number\":\"$STEP4_AUTH_REF\",\"authentication_token\":\"$STEP4_AUTH_TEMP_TOKEN\"}"
echo

echo "=== STEP 4.4: redeem temporary token ==="
curl -sS -X POST "$BASE_URL/api/testing/ksef/auth/step4/redeem" \
  -H "Content-Type: application/json" \
  -d "{\"authentication_token\":\"$STEP4_AUTH_TEMP_TOKEN\"}"
echo
```

## Notes

- KSeF token value returned in Step 2 is displayed once; store it securely.
- If status is pending, repeat status checks or use the poll endpoint.
- You can also use full-service shortcuts:
  - `POST /api/testing/ksef/auth/step1/redeem/xades`
  - `POST /api/testing/ksef/auth/step4/redeem/token`
