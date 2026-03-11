"""
Tax identifier validation.

This module provides:
- NIP validation logic
- Tax identifier format validation
- Contractor data validation
- European VAT validation
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.core.exceptions import ValidationError
from app.core.security import sanitize_text_input


NIP_LENGTH = 10
NIP_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)

EU_COUNTRY_CODES = {
    "AT",
    "BE",
    "BG",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "EL",
    "ES",
    "FI",
    "FR",
    "HR",
    "HU",
    "IE",
    "IT",
    "LT",
    "LU",
    "LV",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SE",
    "SI",
    "SK",
}

NON_ALNUM_RE = re.compile(r"[^A-Za-z0-9]+")
DIGITS_ONLY_RE = re.compile(r"\D+")
GENERIC_EU_VAT_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{2,12}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class TaxIdentifierValidator:
    """
    Validator for Polish NIP and basic EU VAT identifiers.

    Notes:
    - Polish NIP validation includes checksum verification.
    - EU VAT validation here is syntax-level only.
    - Live VAT activity / registration checks should be done via VIES.
    """

    @staticmethod
    def normalize_identifier(value: str | None) -> str:
        """
        Normalize identifier by removing spaces, dashes, dots and other separators.

        Keeps only alphanumeric characters and returns uppercase text.
        """
        if value is None:
            return ""

        cleaned = sanitize_text_input(value, max_length=64)
        cleaned = NON_ALNUM_RE.sub("", cleaned)
        return cleaned.upper()

    @staticmethod
    def normalize_digits(value: str | None) -> str:
        """
        Normalize identifier to digits only.
        """
        if value is None:
            return ""

        cleaned = sanitize_text_input(value, max_length=64)
        return DIGITS_ONLY_RE.sub("", cleaned)

    @staticmethod
    def is_valid_nip_checksum(nip: str) -> bool:
        """
        Validate Polish NIP checksum.

        NIP consists of 10 digits. The checksum is calculated from the first
        9 digits using weights: 6, 5, 7, 2, 3, 4, 5, 6, 7.
        """
        if len(nip) != NIP_LENGTH or not nip.isdigit():
            return False

        checksum = sum(int(nip[i]) * NIP_WEIGHTS[i] for i in range(9)) % 11
        if checksum == 10:
            return False

        return checksum == int(nip[9])

    @classmethod
    def validate_nip(
        cls,
        value: str | None,
        *,
        required: bool = True,
        field_name: str = "nip",
    ) -> str | None:
        """
        Validate Polish NIP and return normalized digits-only value.

        Raises:
            ValidationError: if the value is invalid.
        """
        normalized = cls.normalize_digits(value)

        if not normalized:
            if required:
                raise ValidationError(
                    message=f"Field '{field_name}' is required.",
                    details={"field": field_name},
                )
            return None

        if len(normalized) != NIP_LENGTH:
            raise ValidationError(
                message=f"Field '{field_name}' must contain exactly 10 digits.",
                details={"field": field_name, "value": value},
            )

        if not cls.is_valid_nip_checksum(normalized):
            raise ValidationError(
                message=f"Field '{field_name}' contains an invalid NIP checksum.",
                details={"field": field_name, "value": value},
            )

        return normalized

    @classmethod
    def validate_polish_vat_eu(
        cls,
        value: str | None,
        *,
        required: bool = True,
        field_name: str = "vat_eu",
    ) -> str | None:
        """
        Validate Polish VAT EU number in the form PL + NIP.

        Returns normalized uppercase value, e.g. PL1234567890.
        """
        normalized = cls.normalize_identifier(value)

        if not normalized:
            if required:
                raise ValidationError(
                    message=f"Field '{field_name}' is required.",
                    details={"field": field_name},
                )
            return None

        if not normalized.startswith("PL"):
            raise ValidationError(
                message=f"Field '{field_name}' must start with 'PL'.",
                details={"field": field_name, "value": value},
            )

        nip_part = normalized[2:]
        cls.validate_nip(nip_part, required=True, field_name=field_name)

        return normalized

    @classmethod
    def looks_like_eu_vat_number(cls, value: str | None) -> bool:
        """
        Perform a syntax-level check for an EU VAT number.

        This does not confirm whether the number is active in VIES.
        """
        normalized = cls.normalize_identifier(value)
        if not normalized:
            return False

        if not GENERIC_EU_VAT_RE.fullmatch(normalized):
            return False

        country_code = normalized[:2]
        if country_code not in EU_COUNTRY_CODES:
            return False

        if country_code == "PL":
            return cls.is_valid_nip_checksum(normalized[2:])

        return True

    @classmethod
    def validate_eu_vat_number(
        cls,
        value: str | None,
        *,
        required: bool = True,
        field_name: str = "vat_eu",
    ) -> str | None:
        """
        Validate EU VAT number syntax and return normalized uppercase value.

        Special handling:
        - PL VAT EU must contain valid NIP checksum.
        """
        normalized = cls.normalize_identifier(value)

        if not normalized:
            if required:
                raise ValidationError(
                    message=f"Field '{field_name}' is required.",
                    details={"field": field_name},
                )
            return None

        if not GENERIC_EU_VAT_RE.fullmatch(normalized):
            raise ValidationError(
                message=(
                    f"Field '{field_name}' must have EU VAT format: "
                    "2-letter country code followed by alphanumeric identifier."
                ),
                details={"field": field_name, "value": value},
            )

        country_code = normalized[:2]
        if country_code not in EU_COUNTRY_CODES:
            raise ValidationError(
                message=f"Field '{field_name}' contains unsupported EU country code.",
                details={"field": field_name, "value": value},
            )

        if country_code == "PL":
            cls.validate_nip(normalized[2:], required=True, field_name=field_name)

        return normalized

    @classmethod
    def validate_tax_identifier(
        cls,
        value: str | None,
        *,
        country_code: str | None = None,
        required: bool = True,
        field_name: str = "tax_identifier",
    ) -> str | None:
        """
        Validate a tax identifier based on country context.

        Rules:
        - For PL: accepts plain NIP or PL-prefixed VAT EU and returns normalized value.
        - For EU countries other than PL: expects EU VAT format with country prefix.
        - Without country context: tries to infer whether value is PL NIP or EU VAT.
        """
        country = sanitize_text_input(country_code).upper() if country_code else None
        normalized = cls.normalize_identifier(value)

        if not normalized:
            if required:
                raise ValidationError(
                    message=f"Field '{field_name}' is required.",
                    details={"field": field_name},
                )
            return None

        if country == "PL":
            if normalized.startswith("PL"):
                return cls.validate_polish_vat_eu(
                    normalized,
                    required=True,
                    field_name=field_name,
                )
            return cls.validate_nip(
                normalized,
                required=True,
                field_name=field_name,
            )

        if country in EU_COUNTRY_CODES:
            return cls.validate_eu_vat_number(
                normalized,
                required=True,
                field_name=field_name,
            )

        if normalized.isdigit():
            return cls.validate_nip(
                normalized,
                required=True,
                field_name=field_name,
            )

        return cls.validate_eu_vat_number(
            normalized,
            required=True,
            field_name=field_name,
        )

    @staticmethod
    def validate_email(
        value: str | None,
        *,
        required: bool = False,
        field_name: str = "email",
    ) -> str | None:
        """
        Basic email syntax validation for contractor data.
        """
        normalized = sanitize_text_input(value, max_length=255)

        if not normalized:
            if required:
                raise ValidationError(
                    message=f"Field '{field_name}' is required.",
                    details={"field": field_name},
                )
            return None

        if not EMAIL_RE.fullmatch(normalized):
            raise ValidationError(
                message=f"Field '{field_name}' is not a valid email address.",
                details={"field": field_name, "value": value},
            )

        return normalized.lower()

    @staticmethod
    def validate_non_empty_text(
        value: str | None,
        *,
        required: bool = True,
        field_name: str,
        max_length: int = 255,
    ) -> str | None:
        """
        Validate a non-empty text field.
        """
        normalized = sanitize_text_input(value, max_length=max_length)

        if not normalized:
            if required:
                raise ValidationError(
                    message=f"Field '{field_name}' is required.",
                    details={"field": field_name},
                )
            return None

        return normalized

    @classmethod
    def validate_contractor_data(
        cls,
        contractor: Mapping[str, Any],
        *,
        require_tax_identifier: bool = True,
        require_address: bool = True,
    ) -> dict[str, Any]:
        """
        Validate and normalize contractor data.

        Expected input keys may include:
        - name
        - country_code
        - tax_identifier
        - nip
        - vat_eu
        - email
        - city
        - postal_code
        - street
        - house_number

        Returns:
            Normalized contractor dictionary.

        Raises:
            ValidationError: if required data is missing or inconsistent.
        """
        if not contractor:
            raise ValidationError(
                message="Contractor data is required.",
                details={"field": "contractor"},
            )

        country_code = (
            sanitize_text_input(
                str(contractor.get("country_code") or ""),
                max_length=2,
            ).upper()
            or None
        )

        name = cls.validate_non_empty_text(
            contractor.get("name"),
            required=True,
            field_name="name",
            max_length=255,
        )

        email = cls.validate_email(
            contractor.get("email"),
            required=False,
            field_name="email",
        )

        tax_identifier_input = (
            contractor.get("tax_identifier")
            or contractor.get("vat_eu")
            or contractor.get("nip")
        )

        tax_identifier = cls.validate_tax_identifier(
            tax_identifier_input,
            country_code=country_code,
            required=require_tax_identifier,
            field_name="tax_identifier",
        )

        normalized: dict[str, Any] = {
            "name": name,
            "country_code": country_code,
            "tax_identifier": tax_identifier,
            "email": email,
        }

        if require_address:
            normalized["street"] = cls.validate_non_empty_text(
                contractor.get("street"),
                required=True,
                field_name="street",
                max_length=255,
            )
            normalized["house_number"] = cls.validate_non_empty_text(
                contractor.get("house_number"),
                required=True,
                field_name="house_number",
                max_length=32,
            )
            normalized["postal_code"] = cls.validate_non_empty_text(
                contractor.get("postal_code"),
                required=True,
                field_name="postal_code",
                max_length=32,
            )
            normalized["city"] = cls.validate_non_empty_text(
                contractor.get("city"),
                required=True,
                field_name="city",
                max_length=255,
            )
        else:
            normalized["street"] = (
                sanitize_text_input(
                    contractor.get("street"),
                    max_length=255,
                )
                or None
            )
            normalized["house_number"] = (
                sanitize_text_input(
                    contractor.get("house_number"),
                    max_length=32,
                )
                or None
            )
            normalized["postal_code"] = (
                sanitize_text_input(
                    contractor.get("postal_code"),
                    max_length=32,
                )
                or None
            )
            normalized["city"] = (
                sanitize_text_input(
                    contractor.get("city"),
                    max_length=255,
                )
                or None
            )

        return normalized
