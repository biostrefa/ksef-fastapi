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
