from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.x509 import Certificate, Name, NameAttribute
from cryptography.x509.oid import NameOID
from lxml import etree

from app.core.exceptions import AuthenticationError
from app.infrastructure.crypto.certificate_loader import CertificateLoader

DS = "http://www.w3.org/2000/09/xmldsig#"
XADES = "http://uri.etsi.org/01903/v1.3.2#"

_DS = f"{{{DS}}}"
_XADES = f"{{{XADES}}}"

_NSMAP = {
    "ds": DS,
    "xades": XADES,
}


class XadesSigner:
    """
    Minimalny XAdES-BES enveloped signature dla AuthTokenRequest KSeF 2.0.

    Założenia:
    - podpis jest dołączany jako ds:Signature wewnątrz dokumentu XML,
    - referencja do dokumentu ma transforms:
        1) enveloped-signature
        2) exclusive c14n
    - referencja do SignedProperties ma transform:
        1) exclusive c14n
    - digest SignedProperties liczony jest po osadzeniu podpisu w dokumencie.
    """

    def __init__(
        self,
        *,
        certificate_loader: CertificateLoader,
        canonicalization_method: str = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
        digest_method: str = "http://www.w3.org/2001/04/xmlenc#sha256",
        signature_method: str | None = None,
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

        signature_method = self._resolve_signature_method(private_key)
        self._validate_key_matches_signature_method(private_key, signature_method)

        try:
            root = etree.fromstring(unsigned_xml.encode("utf-8"))
        except etree.XMLSyntaxError as exc:
            raise AuthenticationError("Invalid XML for XAdES signature") from exc

        existing_signature = root.find(f".//{_DS}Signature")
        if existing_signature is not None:
            raise AuthenticationError("Input XML already contains ds:Signature")

        sig_id = "Signature"
        signed_props_id = "SignedProperties"

        object_el, _signed_props_el = self._build_xades_object(
            sig_id=sig_id,
            signed_props_id=signed_props_id,
            certificate=certificate,
        )

        doc_digest = self._digest_after_explicit_exc_c14n(root)

        signed_info_el = self._build_signed_info(
            doc_digest=doc_digest,
            signed_props_id=signed_props_id,
            signature_method=signature_method,
            sp_digest_placeholder=True,
        )

        signature_el = self._assemble_signature(
            sig_id=sig_id,
            signed_info_el=signed_info_el,
            sig_value_b64="",
            cert_b64=base64.b64encode(certificate.public_bytes(serialization.Encoding.DER)).decode("ascii"),
            object_el=object_el,
        )

        root.append(signature_el)

        signed_props_in_doc = root.find(f".//{_XADES}SignedProperties[@Id='{signed_props_id}']")
        if signed_props_in_doc is None:
            raise AuthenticationError("Cannot locate SignedProperties after insertion")

        sp_digest_real = self._digest_after_explicit_exc_c14n(signed_props_in_doc)

        ref_sp = signed_info_el.find(f"./{_DS}Reference[@URI='#{signed_props_id}']")
        if ref_sp is None:
            raise AuthenticationError("Reference to SignedProperties not found in SignedInfo")

        ref_sp_digest_value = ref_sp.find(f"./{_DS}DigestValue")
        if ref_sp_digest_value is None:
            raise AuthenticationError("DigestValue not found in SignedProperties reference")

        ref_sp_digest_value.text = sp_digest_real

        signed_info_c14n = self._c14n_exc(signed_info_el)

        try:
            sig_value_raw = self._sign_bytes(
                private_key=private_key,
                data=signed_info_c14n,
                signature_method=signature_method,
            )
        except Exception as exc:
            raise AuthenticationError(f"Failed to sign SignedInfo: {exc}") from exc

        signature_value_el = signature_el.find(f"./{_DS}SignatureValue")
        if signature_value_el is None:
            raise AuthenticationError("SignatureValue element not found")

        signature_value_el.text = base64.b64encode(sig_value_raw).decode("ascii")

        return etree.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=False,
        ).decode("utf-8")

    def _c14n_exc(self, element: etree._Element) -> bytes:
        return etree.tostring(
            element,
            method="c14n",
            exclusive=True,
            with_comments=False,
        )

    def _digest_bytes(self, data: bytes) -> str:
        digest_alg_name = self._digest_method.lower()

        if digest_alg_name.endswith("sha256"):
            digest = hashlib.sha256(data).digest()
        elif digest_alg_name.endswith("sha512"):
            digest = hashlib.sha512(data).digest()
        else:
            raise AuthenticationError(f"Unsupported digest method: {self._digest_method}")

        return base64.b64encode(digest).decode("ascii")

    def _digest_after_explicit_exc_c14n(self, element: etree._Element) -> str:
        return self._digest_bytes(self._c14n_exc(element))

    def _build_xades_object(
        self,
        *,
        sig_id: str,
        signed_props_id: str,
        certificate: Certificate,
    ) -> tuple[etree._Element, etree._Element]:
        object_el = etree.Element(_DS + "Object", nsmap=_NSMAP)

        qp = etree.SubElement(
            object_el,
            _XADES + "QualifyingProperties",
            attrib={
                "Target": f"#{sig_id}",
            },
        )

        sp = etree.SubElement(
            qp,
            _XADES + "SignedProperties",
            attrib={"Id": signed_props_id},
        )

        ssp = etree.SubElement(sp, _XADES + "SignedSignatureProperties")

        signing_time = etree.SubElement(ssp, _XADES + "SigningTime")
        signing_time.text = self._format_signing_time(datetime.now(timezone.utc) - timedelta(minutes=1))

        signing_certificate = etree.SubElement(ssp, _XADES + "SigningCertificate")
        cert_el = etree.SubElement(signing_certificate, _XADES + "Cert")

        cert_digest_el = etree.SubElement(cert_el, _XADES + "CertDigest")
        etree.SubElement(
            cert_digest_el,
            _DS + "DigestMethod",
            attrib={"Algorithm": self._digest_method},
        )

        cert_der = certificate.public_bytes(serialization.Encoding.DER)
        cert_digest_value = etree.SubElement(cert_digest_el, _DS + "DigestValue")
        cert_digest_value.text = self._digest_bytes(cert_der)

        issuer_serial = etree.SubElement(cert_el, _XADES + "IssuerSerial")
        etree.SubElement(
            issuer_serial,
            _DS + "X509IssuerName",
        ).text = self._format_dotnet_issuer_name(certificate.issuer)
        etree.SubElement(
            issuer_serial,
            _DS + "X509SerialNumber",
        ).text = self._format_dotnet_serial_number(certificate)

        return object_el, sp

    def _build_signed_info(
        self,
        *,
        doc_digest: str,
        signed_props_id: str,
        signature_method: str,
        sp_digest_placeholder: bool,
    ) -> etree._Element:
        si = etree.Element(_DS + "SignedInfo", nsmap=_NSMAP)

        etree.SubElement(
            si,
            _DS + "CanonicalizationMethod",
            attrib={"Algorithm": self._canonicalization_method},
        )
        etree.SubElement(
            si,
            _DS + "SignatureMethod",
            attrib={"Algorithm": signature_method},
        )

        ref1 = etree.SubElement(si, _DS + "Reference", attrib={"URI": ""})
        ref1_transforms = etree.SubElement(ref1, _DS + "Transforms")

        etree.SubElement(
            ref1_transforms,
            _DS + "Transform",
            attrib={"Algorithm": "http://www.w3.org/2000/09/xmldsig#enveloped-signature"},
        )
        etree.SubElement(
            ref1_transforms,
            _DS + "Transform",
            attrib={"Algorithm": self._canonicalization_method},
        )

        etree.SubElement(
            ref1,
            _DS + "DigestMethod",
            attrib={"Algorithm": self._digest_method},
        )
        etree.SubElement(ref1, _DS + "DigestValue").text = doc_digest

        ref2 = etree.SubElement(
            si,
            _DS + "Reference",
            attrib={
                "URI": f"#{signed_props_id}",
                "Type": "http://uri.etsi.org/01903#SignedProperties",
            },
        )
        ref2_transforms = etree.SubElement(ref2, _DS + "Transforms")
        etree.SubElement(
            ref2_transforms,
            _DS + "Transform",
            attrib={"Algorithm": self._canonicalization_method},
        )

        etree.SubElement(
            ref2,
            _DS + "DigestMethod",
            attrib={"Algorithm": self._digest_method},
        )

        dv2 = etree.SubElement(ref2, _DS + "DigestValue")
        dv2.text = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=" if sp_digest_placeholder else ""

        return si

    def _assemble_signature(
        self,
        *,
        sig_id: str,
        signed_info_el: etree._Element,
        sig_value_b64: str,
        cert_b64: str,
        object_el: etree._Element,
    ) -> etree._Element:
        sig = etree.Element(
            _DS + "Signature",
            attrib={"Id": sig_id},
            nsmap=_NSMAP,
        )

        sig.append(signed_info_el)

        signature_value = etree.SubElement(sig, _DS + "SignatureValue")
        signature_value.text = sig_value_b64

        key_info = etree.SubElement(sig, _DS + "KeyInfo")
        x509_data = etree.SubElement(key_info, _DS + "X509Data")
        etree.SubElement(x509_data, _DS + "X509Certificate").text = cert_b64

        sig.append(object_el)

        return sig

    def _sign_bytes(
        self,
        *,
        private_key: object,
        data: bytes,
        signature_method: str,
    ) -> bytes:
        hash_alg = self._hash_algorithm_from_signature_method(signature_method)

        if isinstance(private_key, rsa.RSAPrivateKey):
            return private_key.sign(data, padding.PKCS1v15(), hash_alg)

        if isinstance(private_key, ec.EllipticCurvePrivateKey):
            der_signature = private_key.sign(data, ec.ECDSA(hash_alg))
            return self._ecdsa_der_to_xmlsig(der_signature, private_key)

        raise AuthenticationError(
            "Unsupported private key type",
            details={"type": type(private_key).__name__},
        )

    @staticmethod
    def _ecdsa_der_to_xmlsig(signature_der: bytes, private_key: ec.EllipticCurvePrivateKey) -> bytes:
        r, s = decode_dss_signature(signature_der)
        component_size = (private_key.curve.key_size + 7) // 8
        return r.to_bytes(component_size, byteorder="big") + s.to_bytes(component_size, byteorder="big")

    def _resolve_signature_method(self, private_key: object) -> str:
        if self._signature_method:
            return self._signature_method

        digest_method = self._digest_method.lower()

        if isinstance(private_key, rsa.RSAPrivateKey):
            if digest_method.endswith("sha256"):
                return "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
            if digest_method.endswith("sha512"):
                return "http://www.w3.org/2001/04/xmldsig-more#rsa-sha512"

        if isinstance(private_key, ec.EllipticCurvePrivateKey):
            if digest_method.endswith("sha256"):
                return "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256"
            if digest_method.endswith("sha512"):
                return "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha512"

        raise AuthenticationError(
            "Unable to resolve signature method for provided private key and digest method",
            details={
                "private_key_type": type(private_key).__name__,
                "digest_method": self._digest_method,
            },
        )

    @staticmethod
    def _format_signing_time(value: datetime) -> str:
        iso_value = value.astimezone(timezone.utc).isoformat(timespec="microseconds")
        if iso_value.endswith("+00:00"):
            return f"{iso_value[:-6]}Z"
        return iso_value

    @staticmethod
    def _format_dotnet_serial_number(certificate: Certificate) -> str:
        serial_bytes_big_endian = certificate.serial_number.to_bytes(
            max(1, (certificate.serial_number.bit_length() + 7) // 8),
            byteorder="big",
            signed=False,
        )
        serial_bytes_little_endian = serial_bytes_big_endian[::-1]
        return str(int.from_bytes(serial_bytes_little_endian, byteorder="little", signed=False))

    @staticmethod
    def _format_dotnet_issuer_name(issuer: Name) -> str:
        friendly_names = {
            NameOID.COUNTRY_NAME: "C",
            NameOID.ORGANIZATION_NAME: "O",
            NameOID.ORGANIZATIONAL_UNIT_NAME: "OU",
            NameOID.COMMON_NAME: "CN",
            NameOID.SERIAL_NUMBER: "SERIALNUMBER",
            NameOID.GIVEN_NAME: "G",
            NameOID.SURNAME: "SN",
            NameOID.USER_ID: "UID",
            NameOID.DOMAIN_COMPONENT: "DC",
            NameOID.LOCALITY_NAME: "L",
            NameOID.STATE_OR_PROVINCE_NAME: "S",
            NameOID.STREET_ADDRESS: "STREET",
            NameOID.TITLE: "T",
            NameOID.POSTAL_CODE: "PostalCode",
            NameOID.BUSINESS_CATEGORY: "BusinessCategory",
        }

        parts: list[str] = []
        for rdn in issuer.rdns:
            for attribute in rdn:
                parts.append(XadesSigner._format_dotnet_name_attribute(attribute, friendly_names))
        return ", ".join(parts)

    @staticmethod
    def _format_dotnet_name_attribute(
        attribute: NameAttribute,
        friendly_names: dict[object, str],
    ) -> str:
        key = friendly_names.get(attribute.oid, attribute.oid.dotted_string)
        return f"{key}={attribute.value}"

    @staticmethod
    def _validate_key_matches_signature_method(private_key: object, signature_method: str) -> None:
        method = signature_method.lower()

        if isinstance(private_key, rsa.RSAPrivateKey) and "rsa-" not in method:
            raise AuthenticationError(
                "Configured SignatureMethod is incompatible with RSA private key",
                details={"signature_method": signature_method},
            )

        if isinstance(private_key, ec.EllipticCurvePrivateKey) and "ecdsa-" not in method:
            raise AuthenticationError(
                "Configured SignatureMethod is incompatible with EC private key",
                details={"signature_method": signature_method},
            )

    @staticmethod
    def _hash_algorithm_from_signature_method(signature_method: str) -> hashes.HashAlgorithm:
        method = signature_method.lower()

        if "sha256" in method:
            return hashes.SHA256()
        if "sha512" in method:
            return hashes.SHA512()

        raise AuthenticationError(f"Unsupported signature method: {signature_method}")
