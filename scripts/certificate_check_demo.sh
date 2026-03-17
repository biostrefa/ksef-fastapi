#!/usr/bin/env bash
# Direct XAdES check against KSeF demo (bypasses your app HTTP client)
# Run from: /home/oski/code/ksef_fastapi or /home/oski/code/ksef_fastapi/scripts

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
  echo "ERROR: .env not found at $PROJECT_ROOT/.env"
  exit 1
fi

cd "$PROJECT_ROOT"

SIGNED_XML_PATH="${SIGNED_XML_PATH:-$PROJECT_ROOT/tmp_signed_auth_request.xml}"
RESPONSE_JSON_PATH="${RESPONSE_JSON_PATH:-$PROJECT_ROOT/tmp_ksef_xades_response.json}"

CHALLENGE="$(
  curl -sS -X POST 'https://api-demo.ksef.mf.gov.pl/v2/auth/challenge' \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '{}' | jq -r '.challenge'
)"

SIGNED_XML="$(CHALLENGE_VALUE="$CHALLENGE" uv run python - <<'PY'
import os
import sys
import textwrap
from cryptography.hazmat.primitives import hashes
from app.core.config import get_settings
from app.infrastructure.crypto.certificate_loader import CertificateLoader
from app.infrastructure.crypto.xades_signer import XadesSigner
from app.domain.strategies.xades_auth_strategy import XadesAuthStrategy

settings = get_settings()

loader = CertificateLoader(
    mf_public_encryption_cert_path=settings.ksef_mf_public_encryption_cert_path,
    private_key_path=settings.ksef_private_key_path,
    private_key_password=settings.ksef_private_key_password,
    xades_signing_cert_path=settings.ksef_xades_signing_cert_path,
)

signer = XadesSigner(
    certificate_loader=loader,
    canonicalization_method=settings.ksef_xades_canonicalization_method,
    digest_method=settings.ksef_xades_digest_method,
    signature_method=settings.ksef_xades_signature_method,
)

strategy = XadesAuthStrategy(
    signer=signer.sign_xml,
    namespace_uri="http://ksef.mf.gov.pl/auth/token/2.0",
)

certificate = loader.load_parsed_xades_signing_certificate()
private_key = loader.load_parsed_private_key()
fingerprint_hex = certificate.fingerprint(hashes.SHA256()).hex().upper()
fingerprint_colon = ":".join(textwrap.wrap(fingerprint_hex, 2))

print("=== CERT DIAGNOSTICS ===", file=sys.stderr)
print(f"XADES_CERT_PATH={settings.ksef_xades_signing_cert_path}", file=sys.stderr)
print(f"PRIVATE_KEY_PATH={settings.ksef_private_key_path}", file=sys.stderr)
print(f"CERT_SUBJECT={certificate.subject.rfc4514_string()}", file=sys.stderr)
print(f"CERT_ISSUER={certificate.issuer.rfc4514_string()}", file=sys.stderr)
print(f"CERT_SERIAL_HEX={hex(certificate.serial_number)}", file=sys.stderr)
print(f"CERT_NOT_BEFORE={certificate.not_valid_before_utc.isoformat()}", file=sys.stderr)
print(f"CERT_NOT_AFTER={certificate.not_valid_after_utc.isoformat()}", file=sys.stderr)
print(f"CERT_SHA256_FINGERPRINT={fingerprint_colon}", file=sys.stderr)
print(f"PRIVATE_KEY_TYPE={type(private_key).__name__}", file=sys.stderr)
print("=== END CERT DIAGNOSTICS ===", file=sys.stderr)

xml = strategy.build_signed_auth_request_xml(
    challenge=os.environ["CHALLENGE_VALUE"],
    context_identifier_type=settings.ksef_context_identifier_type,
    context_identifier_value=settings.ksef_context_identifier_value,
    subject_identifier_type="certificateSubject",
)
print(xml)
PY
)"

echo "$SIGNED_XML" > "$SIGNED_XML_PATH"
echo "SIGNED_XML_PATH=$SIGNED_XML_PATH"

curl -sS -X POST 'https://api-demo.ksef.mf.gov.pl/v2/auth/xades-signature?verifyCertificateChain=false' \
  -H 'Content-Type: application/xml' \
  --data "$SIGNED_XML" > "$RESPONSE_JSON_PATH"

echo "RESPONSE_JSON_PATH=$RESPONSE_JSON_PATH"
cat "$RESPONSE_JSON_PATH" | jq
