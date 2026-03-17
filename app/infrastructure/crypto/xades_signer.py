from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
from xml.etree import ElementTree as ET

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

from app.core.exceptions import AuthenticationError
from app.infrastructure.crypto.certificate_loader import CertificateLoader


class XadesSigner:
    """Build an enveloped XML signature for KSeF XAdES auth payloads."""

    DS_NS = "http://www.w3.org/2000/09/xmldsig#"
    XADES_NS = "http://uri.etsi.org/01903/v1.3.2#"

    def __init__(
        self,
        *,
        certificate_loader: CertificateLoader,
        canonicalization_method: str,
        digest_method: str,
        signature_method: str,
    ) -> None:
        self._certificate_loader = certificate_loader
        self._canonicalization_method = canonicalization_method
        self._digest_method = digest_method
        self._signature_method = signature_method

    def sign_xml(self, unsigned_xml: str) -> str:
        if not unsigned_xml.strip():
            raise AuthenticationError("Unsigned XML payload is empty")

        self._certificate_loader.ensure_required_material_for_xades()
        private_key = self._certificate_loader.load_parsed_private_key()
        certificate = self._certificate_loader.load_parsed_xades_signing_certificate()

        try:
            root = ET.fromstring(unsigned_xml)
        except ET.ParseError as exc:
            raise AuthenticationError("Invalid XML for XAdES signature") from exc

        signature_el, signed_info_el = self._build_signature_template(root)

        # Add XAdES elements before signing and get the SignedProperties ID
        signed_props_id = self._add_xades_elements_before_signing(signature_el, certificate)

        # Add the SignedProperties reference to SignedInfo before signing
        self._add_signed_properties_reference(signed_info_el, signed_props_id)

        # Calculate signature after all elements are in place
        signed_info_bytes = self._canonicalize_xml(signed_info_el)

        try:
            signature_bytes = self._sign_bytes(private_key=private_key, data=signed_info_bytes)
        except Exception as exc:
            raise AuthenticationError(
                f"Failed to sign XAdES XML: {exc}",
                details={
                    "private_key_type": type(private_key).__name__,
                    "signature_method": self._signature_method,
                    "error": str(exc),
                },
            ) from exc

        signature_value_el = signature_el.find(f"{{{self.DS_NS}}}SignatureValue")
        if signature_value_el is None:
            raise AuthenticationError("Unable to construct XML signature value element")
        signature_value_el.text = base64.b64encode(signature_bytes).decode("ascii")

        cert_der = certificate.public_bytes(serialization.Encoding.DER)
        cert_b64 = base64.b64encode(cert_der).decode("ascii")
        cert_el = signature_el.find(f"{{{self.DS_NS}}}KeyInfo/{{{self.DS_NS}}}X509Data/{{{self.DS_NS}}}X509Certificate")
        if cert_el is None:
            raise AuthenticationError("Unable to construct XML X509 certificate element")
        cert_el.text = cert_b64

        # Update the SignedProperties digest after all elements are finalized
        self._update_signed_properties_digest(signature_el, signed_props_id)

        root.append(signature_el)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

    def _build_signature_template(self, root: ET.Element) -> tuple[ET.Element, ET.Element]:
        ET.register_namespace("ds", self.DS_NS)
        ET.register_namespace("xades", self.XADES_NS)

        signature_el = ET.Element(f"{{{self.DS_NS}}}Signature")
        signed_info_el = ET.SubElement(signature_el, f"{{{self.DS_NS}}}SignedInfo")

        ET.SubElement(
            signed_info_el,
            f"{{{self.DS_NS}}}CanonicalizationMethod",
            {"Algorithm": self._canonicalization_method},
        )
        ET.SubElement(
            signed_info_el,
            f"{{{self.DS_NS}}}SignatureMethod",
            {"Algorithm": self._signature_method},
        )

        # Reference for the document content
        reference_el = ET.SubElement(signed_info_el, f"{{{self.DS_NS}}}Reference", {"URI": ""})
        transforms_el = ET.SubElement(reference_el, f"{{{self.DS_NS}}}Transforms")
        ET.SubElement(
            transforms_el,
            f"{{{self.DS_NS}}}Transform",
            {"Algorithm": "http://www.w3.org/2000/09/xmldsig#enveloped-signature"},
        )
        ET.SubElement(
            transforms_el,
            f"{{{self.DS_NS}}}Transform",
            {"Algorithm": self._canonicalization_method},
        )

        ET.SubElement(
            reference_el,
            f"{{{self.DS_NS}}}DigestMethod",
            {"Algorithm": self._digest_method},
        )

        digest_value = self._digest_value(self._canonicalize_xml(root), self._digest_method)
        digest_value_el = ET.SubElement(reference_el, f"{{{self.DS_NS}}}DigestValue")
        digest_value_el.text = digest_value

        # We'll add the XAdES reference later after we have the certificate
        ET.SubElement(signature_el, f"{{{self.DS_NS}}}SignatureValue")
        key_info_el = ET.SubElement(signature_el, f"{{{self.DS_NS}}}KeyInfo")
        x509_data_el = ET.SubElement(key_info_el, f"{{{self.DS_NS}}}X509Data")
        ET.SubElement(x509_data_el, f"{{{self.DS_NS}}}X509Certificate")

        return signature_el, signed_info_el

    @staticmethod
    def _canonicalize_xml(element: ET.Element) -> bytes:
        return ET.tostring(element, encoding="utf-8", method="xml")

    def _sign_bytes(self, *, private_key: object, data: bytes) -> bytes:
        hash_alg = self._hash_algorithm_from_signature_method(self._signature_method)

        if isinstance(private_key, rsa.RSAPrivateKey):
            return private_key.sign(data, padding.PKCS1v15(), hash_alg)

        if isinstance(private_key, ec.EllipticCurvePrivateKey):
            return private_key.sign(data, ec.ECDSA(hash_alg))

        raise AuthenticationError(
            "Unsupported private key type for XAdES signature",
            details={"private_key_type": type(private_key).__name__},
        )

    @staticmethod
    def _digest_value(data: bytes, digest_method: str) -> str:
        if digest_method.endswith("sha256"):
            digest = hashlib.sha256(data).digest()
        elif digest_method.endswith("sha512"):
            digest = hashlib.sha512(data).digest()
        else:
            raise AuthenticationError(
                "Unsupported XAdES digest method",
                details={"digest_method": digest_method},
            )

        return base64.b64encode(digest).decode("ascii")

    @staticmethod
    def _hash_algorithm_from_signature_method(signature_method: str) -> hashes.HashAlgorithm:
        if signature_method.endswith("rsa-sha256") or signature_method.endswith("ecdsa-sha256"):
            return hashes.SHA256()
        if signature_method.endswith("rsa-sha512") or signature_method.endswith("ecdsa-sha512"):
            return hashes.SHA512()

        raise AuthenticationError(
            "Unsupported XAdES signature method",
            details={"signature_method": signature_method},
        )

    def _add_xades_elements_before_signing(self, signature_el: ET.Element, certificate) -> str:
        """Add XAdES elements that need to be present before signing."""
        # Generate unique IDs
        import uuid

        signature_id = f"ID-{uuid.uuid4()}"
        signed_props_id = f"ID-{uuid.uuid4()}"
        qualifying_props_id = f"ID-{uuid.uuid4()}"

        # Set signature ID
        signature_el.set("Id", signature_id)

        # Create Object with QualifyingProperties (but without SignedProperties content yet)
        object_el = ET.SubElement(signature_el, f"{{{self.DS_NS}}}Object")
        qualifying_props_el = ET.SubElement(
            object_el,
            f"{{{self.XADES_NS}}}QualifyingProperties",
            {"Id": qualifying_props_id, "Target": f"#{signature_id}"},
        )

        signed_props_el = ET.SubElement(
            qualifying_props_el, f"{{{self.XADES_NS}}}SignedProperties", {"Id": signed_props_id}
        )

        # SignedSignatureProperties
        signed_sig_props_el = ET.SubElement(signed_props_el, f"{{{self.XADES_NS}}}SignedSignatureProperties")

        # SigningTime
        signing_time_el = ET.SubElement(signed_sig_props_el, f"{{{self.XADES_NS}}}SigningTime")
        signing_time_el.text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # SigningCertificate
        signing_cert_el = ET.SubElement(signed_sig_props_el, f"{{{self.XADES_NS}}}SigningCertificate")
        cert_el = ET.SubElement(signing_cert_el, f"{{{self.XADES_NS}}}Cert")

        # CertDigest
        cert_digest_el = ET.SubElement(cert_el, f"{{{self.XADES_NS}}}CertDigest")
        ET.SubElement(cert_digest_el, f"{{{self.DS_NS}}}DigestMethod", {"Algorithm": self._digest_method})

        # Calculate certificate fingerprint
        cert_fingerprint = certificate.fingerprint(hashes.SHA256())
        digest_value_el = ET.SubElement(cert_digest_el, f"{{{self.DS_NS}}}DigestValue")
        digest_value_el.text = base64.b64encode(cert_fingerprint).decode("ascii")

        # IssuerSerial
        issuer_serial_el = ET.SubElement(cert_el, f"{{{self.XADES_NS}}}IssuerSerial")
        issuer_name_el = ET.SubElement(issuer_serial_el, f"{{{self.DS_NS}}}X509IssuerName")
        issuer_name_el.text = certificate.issuer.rfc4514_string()

        serial_number_el = ET.SubElement(issuer_serial_el, f"{{{self.DS_NS}}}X509SerialNumber")
        serial_number_el.text = str(certificate.serial_number)

        return signed_props_id

    def _add_signed_properties_reference(self, signed_info_el: ET.Element, signed_props_id: str) -> None:
        """Add the SignedProperties reference to SignedInfo."""
        xades_ref_el = ET.SubElement(
            signed_info_el,
            f"{{{self.DS_NS}}}Reference",
            {"Type": "http://uri.etsi.org/01903#SignedProperties", "URI": f"#{signed_props_id}"},
        )
        transforms_el = ET.SubElement(xades_ref_el, f"{{{self.DS_NS}}}Transforms")
        ET.SubElement(transforms_el, f"{{{self.DS_NS}}}Transform", {"Algorithm": self._canonicalization_method})
        ET.SubElement(xades_ref_el, f"{{{self.DS_NS}}}DigestMethod", {"Algorithm": self._digest_method})
        # Add placeholder digest value - will be updated later
        ET.SubElement(xades_ref_el, f"{{{self.DS_NS}}}DigestValue").text = ""

    def _update_signed_properties_digest(self, signature_el: ET.Element, signed_props_id: str) -> None:
        """Update the SignedProperties digest value."""
        # Find the SignedProperties reference in SignedInfo
        signed_info_el = signature_el.find(f"{{{self.DS_NS}}}SignedInfo")
        if signed_info_el is None:
            raise AuthenticationError("SignedInfo not found")

        # Find the reference with the SignedProperties type
        xades_ref = None
        for ref in signed_info_el.findall(f"{{{self.DS_NS}}}Reference"):
            ref_type = ref.get("Type")
            if ref_type == "http://uri.etsi.org/01903#SignedProperties":
                xades_ref = ref
                break

        if xades_ref is None:
            raise AuthenticationError("SignedProperties reference not found")

        # Find the SignedProperties element and calculate its digest
        object_el = signature_el.find(
            f"{{{self.DS_NS}}}Object/{{{self.XADES_NS}}}QualifyingProperties/{{{self.XADES_NS}}}SignedProperties"
        )
        if object_el is None:
            raise AuthenticationError("SignedProperties element not found")

        signed_props_bytes = self._canonicalize_xml(object_el)
        signed_props_digest = self._digest_value(signed_props_bytes, self._digest_method)

        # Update the digest value
        digest_value_el = xades_ref.find(f"{{{self.DS_NS}}}DigestValue")
        if digest_value_el is None:
            raise AuthenticationError("DigestValue element not found in SignedProperties reference")
        digest_value_el.text = signed_props_digest
