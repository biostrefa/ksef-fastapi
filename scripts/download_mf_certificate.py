#!/usr/bin/env python3
"""
Download MF public encryption certificate from KSeF API.

This script downloads the public key certificate used for encrypting
session symmetric keys in KSeF communication.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

from cryptography import x509
import httpx

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import get_settings


def download_mf_certificate(ksef_base_url: str, output_path: str, timeout: int = 30) -> None:
    """
    Download MF public encryption certificate from KSeF API.

    Args:
        ksef_base_url: KSeF base URL (e.g., https://api-test.ksef.mf.gov.pl/v2)
        output_path: Path to save the certificate file
        timeout: Request timeout in seconds
    """
    endpoint = f"{ksef_base_url.rstrip('/')}/security/public-key-certificates"

    print(f"Downloading MF public certificate from: {endpoint}")

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(endpoint)
            response.raise_for_status()

            certificates = response.json()

            if not certificates:
                raise ValueError("No certificates returned from KSeF API")

            # Get the first certificate (typically there's only one)
            cert_data = certificates[0]
            cert_pem = cert_data["certificate"]
            valid_from = cert_data["validFrom"]
            valid_to = cert_data["validTo"]
            usage = cert_data.get("usage", [])

            # Ensure proper PEM format
            if not cert_pem.startswith("-----BEGIN CERTIFICATE-----"):
                cert_pem = f"-----BEGIN CERTIFICATE-----\n{cert_pem}\n-----END CERTIFICATE-----"

            print(f"Certificate valid from: {valid_from}")
            print(f"Certificate valid to: {valid_to}")
            print(f"Certificate usage: {', '.join(usage)}")

            # Validate certificate format
            try:
                parsed_cert = x509.load_pem_x509_certificate(cert_pem.encode())
                print(f"Certificate subject: {parsed_cert.subject}")
                print(f"Certificate issuer: {parsed_cert.issuer}")
            except Exception as e:
                print(f"Warning: Could not parse certificate: {e}")

            # Save certificate to file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(cert_pem)

            print(f"Certificate saved to: {output_file}")

    except httpx.HTTPStatusError as e:
        print(f"HTTP error downloading certificate: {e}")
        print(f"Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"Error downloading certificate: {e}")
        sys.exit(1)


def main():
    """Main function."""
    try:
        settings = get_settings()

        # Use the configured KSeF base URL
        ksef_url = settings.ksef_base_url
        output_path = settings.ksef_mf_public_encryption_cert_path

        if not ksef_url:
            print("Error: KSEF_BASE_URL not configured")
            sys.exit(1)

        if not output_path:
            print("Error: KSEF_MF_PUBLIC_ENCRYPTION_CERT_PATH not configured")
            sys.exit(1)

        download_mf_certificate(ksef_url, output_path)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
