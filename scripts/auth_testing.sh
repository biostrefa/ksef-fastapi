#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8033}"
COMPANY_ID="${COMPANY_ID:-123e4567-e89b-12d3-a456-426614174000}"
ENVIRONMENT="${ENVIRONMENT:-test}"
CONTEXT_ID_TYPE="${CONTEXT_ID_TYPE:-Nip}"
CONTEXT_ID_VALUE="${CONTEXT_ID_VALUE:-6793188868}"
TOKEN_POLL_ATTEMPTS="${TOKEN_POLL_ATTEMPTS:-15}"
TOKEN_POLL_DELAY_SECONDS="${TOKEN_POLL_DELAY_SECONDS:-1.0}"

json_read() {
  local json_input="$1"
  local path="$2"
  local default_value="${3-__MISSING__}"
  JSON_INPUT="$json_input" JSON_PATH="$path" DEFAULT_VALUE="$default_value" python3 - <<'PY'
import json
import os
import sys

data = json.loads(os.environ["JSON_INPUT"])
path = [p for p in os.environ["JSON_PATH"].split(".") if p]
default = os.environ["DEFAULT_VALUE"]
cur = data

try:
    for part in path:
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
except Exception:
    if default == "__MISSING__":
        sys.exit(1)
    print(default)
    sys.exit(0)

if isinstance(cur, (dict, list)):
    print(json.dumps(cur, separators=(",", ":")))
elif cur is None:
    print("")
else:
    print(cur)
PY
}

must_read() {
  local json_input="$1"
  local path="$2"
  local label="$3"
  local value
  value="$(json_read "$json_input" "$path" "__MISSING__")"
  if [[ "$value" == "__MISSING__" || -z "$value" ]]; then
    echo "ERROR: missing '$label' in response path '$path'"
    echo "$json_input"
    exit 1
  fi
  printf '%s' "$value"
}

check_step_error() {
  local response="$1"
  local step_name="$2"
  local err
  err="$(json_read "$response" "data.error" "" || true)"
  if [[ -n "$err" ]]; then
    echo "ERROR: $step_name failed: $err"
    echo "$response"
    exit 1
  fi
}

timestamp_to_ms() {
  local timestamp="$1"
  TS="$timestamp" python3 - <<'PY'
from datetime import datetime, timezone
import os

ts = os.environ["TS"]
if ts.endswith("Z"):
    ts = ts[:-1] + "+00:00"
dt = datetime.fromisoformat(ts)
if dt.tzinfo is None:
    dt = dt.replace(tzinfo=timezone.utc)
print(int(dt.timestamp() * 1000))
PY
}

post_json() {
  local endpoint="$1"
  local payload="$2"
  curl -sS -f -X POST "$BASE_URL$endpoint" \
    -H "Content-Type: application/json" \
    -d "$payload"
}

echo "=== STEP 1.1: challenge ==="
STEP1_CHALLENGE_RESP="$(post_json "/api/testing/ksef/auth/step1/challenge" \
  "{\"company_id\":\"$COMPANY_ID\",\"environment\":\"$ENVIRONMENT\"}")"
echo "$STEP1_CHALLENGE_RESP"

CHALLENGE="$(must_read "$STEP1_CHALLENGE_RESP" "data.challenge" "step1 challenge")"

echo "=== STEP 1.2: init xades signature ==="
STEP1_INIT_RESP="$(post_json "/api/testing/ksef/auth/step1/init/xades-signature" \
  "{\"challenge\":\"$CHALLENGE\",\"context_identifier_type\":\"$CONTEXT_ID_TYPE\",\"context_identifier_value\":\"$CONTEXT_ID_VALUE\"}")"
echo "$STEP1_INIT_RESP"
check_step_error "$STEP1_INIT_RESP" "step1.init_xades_signature"

AUTH_REF="$(must_read "$STEP1_INIT_RESP" "data.reference_number" "step1 reference_number")"
AUTH_TEMP_TOKEN="$(must_read "$STEP1_INIT_RESP" "data.authentication_token" "step1 authentication_token")"

echo "=== STEP 1.3: auth status ==="
STEP1_STATUS_RESP="$(post_json "/api/testing/ksef/auth/step1/status" \
  "{\"reference_number\":\"$AUTH_REF\",\"authentication_token\":\"$AUTH_TEMP_TOKEN\"}")"
echo "$STEP1_STATUS_RESP"
check_step_error "$STEP1_STATUS_RESP" "step1.status"

echo "=== STEP 1.4: redeem temporary token ==="
STEP1_REDEEM_RESP="$(post_json "/api/testing/ksef/auth/step1/redeem" \
  "{\"authentication_token\":\"$AUTH_TEMP_TOKEN\"}")"
echo "$STEP1_REDEEM_RESP"

ACCESS_TOKEN="$(must_read "$STEP1_REDEEM_RESP" "data.access_token" "step1 access_token")"

echo "=== STEP 2: create reusable KSeF token ==="
STEP2_RESP="$(post_json "/api/testing/ksef/auth/step2/create-ksef-token" \
  "{\"access_token\":\"$ACCESS_TOKEN\",\"permissions\":[\"InvoiceRead\",\"InvoiceWrite\"],\"description\":\"Auth testing token\"}")"
echo "$STEP2_RESP"

KSEF_TOKEN_REF="$(must_read "$STEP2_RESP" "data.reference_number" "step2 reference_number")"
KSEF_TOKEN_VALUE="$(must_read "$STEP2_RESP" "data.token" "step2 token")"

echo "=== STEP 3: token status poll ==="
STEP3_RESP="$(post_json "/api/testing/ksef/auth/step3/token-status/poll" \
  "{\"access_token\":\"$ACCESS_TOKEN\",\"reference_number\":\"$KSEF_TOKEN_REF\",\"attempts\":$TOKEN_POLL_ATTEMPTS,\"delay_seconds\":$TOKEN_POLL_DELAY_SECONDS}")"
echo "$STEP3_RESP"

echo "=== STEP 4.1: challenge ==="
STEP4_CHALLENGE_RESP="$(post_json "/api/testing/ksef/auth/step1/challenge" \
  "{\"company_id\":\"$COMPANY_ID\",\"environment\":\"$ENVIRONMENT\"}")"
echo "$STEP4_CHALLENGE_RESP"

STEP4_CHALLENGE="$(must_read "$STEP4_CHALLENGE_RESP" "data.challenge" "step4 challenge")"
STEP4_TIMESTAMP="$(must_read "$STEP4_CHALLENGE_RESP" "data.challenge_timestamp" "step4 challenge_timestamp")"
STEP4_TIMESTAMP_MS="$(timestamp_to_ms "$STEP4_TIMESTAMP")"

echo "=== STEP 4.2: init auth with reusable ksef token ==="
STEP4_INIT_RESP="$(post_json "/api/testing/ksef/auth/step4/init/ksef-token" \
  "{\"challenge\":\"$STEP4_CHALLENGE\",\"timestamp_ms\":$STEP4_TIMESTAMP_MS,\"ksef_token\":\"$KSEF_TOKEN_VALUE\",\"context_identifier_type\":\"$CONTEXT_ID_TYPE\",\"context_identifier_value\":\"$CONTEXT_ID_VALUE\"}")"
echo "$STEP4_INIT_RESP"

STEP4_AUTH_REF="$(must_read "$STEP4_INIT_RESP" "data.reference_number" "step4 reference_number")"
STEP4_AUTH_TEMP_TOKEN="$(must_read "$STEP4_INIT_RESP" "data.authentication_token" "step4 authentication_token")"

echo "=== STEP 4.3: auth status ==="
STEP4_STATUS_RESP="$(post_json "/api/testing/ksef/auth/step4/status" \
  "{\"reference_number\":\"$STEP4_AUTH_REF\",\"authentication_token\":\"$STEP4_AUTH_TEMP_TOKEN\"}")"
echo "$STEP4_STATUS_RESP"

echo "=== STEP 4.4: redeem temporary token ==="
STEP4_REDEEM_RESP="$(post_json "/api/testing/ksef/auth/step4/redeem" \
  "{\"authentication_token\":\"$STEP4_AUTH_TEMP_TOKEN\"}")"
echo "$STEP4_REDEEM_RESP"
