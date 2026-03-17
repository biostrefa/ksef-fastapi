"""
XAdES signature authentication strategy.

This module provides:
- Digital signature authentication
- XAdES signature handling
- Certificate-based auth
- Signature validation logic

Classes:
    XadesAuthStrategy(AuthStrategyBase): XAdES signature-based authentication strategy

Methods:
    __init__(certificate_loader: CertificateLoader): Initialize with certificate loader
    build_redeem_payload(challenge: str) -> dict: Build token redemption payload from challenge
    sign_challenge(challenge: str) -> str: Sign challenge using XAdES signature
    get_auth_mode() -> str: Get authentication mode identifier
"""

from __future__ import annotations

from typing import Any, Callable
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

from app.core.constants import KsefAuthMode
from app.core.exceptions import AuthenticationError
from app.domain.strategies.auth_strategy_base import AuthStrategyBase


class XadesAuthStrategy(AuthStrategyBase):
    """
    Strategia uwierzytelnienia podpisem XAdES.

    Ta klasa:
    1. buduje unsigned XML AuthTokenRequest,
    2. przekazuje go do zewnętrznego signera,
    3. zwraca signed XML do wysłania na /auth/xades-signature.

    Nie implementuję własnego podpisu XAdES "na sztywno", bo to wymaga
    dokładnego dopasowania do profilu podpisu, canonicalizacji i certyfikatu.
    """

    def __init__(
        self,
        *,
        signer: Callable[[str], str],
        subject_identifier_type: str = "certificateSubject",
        namespace_uri: str | None = None,
        pretty_print: bool = False,
    ) -> None:
        self.signer = signer
        self.subject_identifier_type = subject_identifier_type
        self.namespace_uri = namespace_uri
        self.pretty_print = pretty_print

    def get_auth_mode(self) -> str:
        return KsefAuthMode.XADES.value

    def build_auth_init_payload(
        self,
        *,
        challenge: str,
        context_identifier_type: str,
        context_identifier_value: str,
        authorization_policy: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        signed_xml = self.build_signed_auth_request_xml(
            challenge=challenge,
            context_identifier_type=context_identifier_type,
            context_identifier_value=context_identifier_value,
            authorization_policy=authorization_policy,
        )
        return {"signed_xml": signed_xml}

    def build_signed_auth_request_xml(
        self,
        *,
        challenge: str,
        context_identifier_type: str,
        context_identifier_value: str,
        authorization_policy: dict[str, Any] | None = None,
        subject_identifier_type: str | None = None,
    ) -> str:
        unsigned_xml = self.build_unsigned_auth_request_xml(
            challenge=challenge,
            context_identifier_type=context_identifier_type,
            context_identifier_value=context_identifier_value,
            authorization_policy=authorization_policy,
            subject_identifier_type=subject_identifier_type or self.subject_identifier_type,
        )

        signed_xml = self.signer(unsigned_xml)
        if not signed_xml or not signed_xml.strip():
            raise AuthenticationError("XAdES signer returned empty XML")

        return signed_xml

    def build_unsigned_auth_request_xml(
        self,
        *,
        challenge: str,
        context_identifier_type: str,
        context_identifier_value: str,
        authorization_policy: dict[str, Any] | None = None,
        subject_identifier_type: str,
    ) -> str:
        if not challenge:
            raise AuthenticationError("Missing challenge for XAdES authentication")
        if not context_identifier_type or not context_identifier_value:
            raise AuthenticationError("Missing context identifier for XAdES authentication")
        if subject_identifier_type not in {
            "certificateSubject",
            "certificateFingerprint",
        }:
            raise AuthenticationError(
                "subject_identifier_type must be 'certificateSubject' or 'certificateFingerprint'"
            )

        if self.namespace_uri:
            register_namespace("", self.namespace_uri)

        root = Element(self._tag("AuthTokenRequest"))

        self._append_text(root, "Challenge", challenge)

        context_identifier = SubElement(root, self._tag("ContextIdentifier"))
        allowed_context_identifier_types = {"Nip", "InternalId", "NipVatUe", "PeppolId"}
        if context_identifier_type not in allowed_context_identifier_types:
            raise AuthenticationError(
                "Unsupported context identifier type for XAdES authentication",
                details={
                    "context_identifier_type": context_identifier_type,
                    "allowed": sorted(allowed_context_identifier_types),
                },
            )

        self._append_text(
            context_identifier,
            context_identifier_type,
            context_identifier_value,
        )

        self._append_text(root, "SubjectIdentifierType", subject_identifier_type)

        if authorization_policy:
            self._append_authorization_policy(root, authorization_policy)

        xml_bytes = tostring(root, encoding="utf-8", xml_declaration=True)

        if not self.pretty_print:
            return xml_bytes.decode("utf-8")

        parsed = minidom.parseString(xml_bytes)
        return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

    @staticmethod
    def build_authorization_policy(
        *,
        ip4_addresses: list[str] | None = None,
        ip4_masks: list[str] | None = None,
        ip4_ranges: list[str] | None = None,
    ) -> dict[str, Any]:
        allowed_ips: dict[str, Any] = {}

        if ip4_addresses:
            allowed_ips["ip4Addresses"] = ip4_addresses
        if ip4_masks:
            allowed_ips["ip4Masks"] = ip4_masks
        if ip4_ranges:
            allowed_ips["ip4Ranges"] = ip4_ranges

        if not allowed_ips:
            return {}

        return {"allowedIps": allowed_ips}

    def _append_authorization_policy(self, root: Element, authorization_policy: dict[str, Any]) -> None:
        policy = SubElement(root, self._tag("AuthorizationPolicy"))

        allowed_ips_payload = authorization_policy.get("allowedIps") or {}
        if allowed_ips_payload:
            allowed_ips = SubElement(policy, self._tag("AllowedIps"))

            for ip in allowed_ips_payload.get("ip4Addresses", []):
                self._append_text(allowed_ips, "Ip4Address", ip)

            for mask in allowed_ips_payload.get("ip4Masks", []):
                self._append_text(allowed_ips, "Ip4Mask", mask)

            for ip_range in allowed_ips_payload.get("ip4Ranges", []):
                self._append_text(allowed_ips, "Ip4Range", ip_range)

    def _tag(self, name: str) -> str:
        if self.namespace_uri:
            return f"{{{self.namespace_uri}}}{name}"
        return name

    def _append_text(self, parent: Element, tag: str, value: str) -> Element:
        node = SubElement(parent, self._tag(tag))
        node.text = value
        return node
