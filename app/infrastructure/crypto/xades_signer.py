from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import uuid

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from lxml import etree

from app.core.exceptions import AuthenticationError
from app.infrastructure.crypto.certificate_loader import CertificateLoader

DS = "http://www.w3.org/2000/09/xmldsig#"
XADES = "http://uri.etsi.org/01903/v1.3.2#"

_DS = "{%s}" % DS
_XADES = "{%s}" % XADES

_NSMAP_DS = {"ds": DS}
_NSMAP_XADES = {"xades": XADES}


class XadesSigner:
    """Build an enveloped XAdES-BES XML signature for KSeF auth payloads."""

    DS_NS = DS
    XADES_NS = XADES

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sign_xml(self, unsigned_xml: str) -> str:
        if not unsigned_xml.strip():
            raise AuthenticationError("Unsigned XML payload is empty")

        self._certificate_loader.ensure_required_material_for_xades()
        private_key = self._certificate_loader.load_parsed_private_key()
        certificate = self._certificate_loader.load_parsed_xades_signing_certificate()

        try:
            root = etree.fromstring(unsigned_xml.encode("utf-8"))
        except etree.XMLSyntaxError as exc:
            raise AuthenticationError("Invalid XML for XAdES signature") from exc

        # --- unique IDs -----------------------------------------------
        sig_id = f"ID-{uuid.uuid4()}"
        signed_props_id = f"ID-{uuid.uuid4()}"
        qp_id = f"ID-{uuid.uuid4()}"

        # --- 1. Build Object/QualifyingProperties/SignedProperties ----
        object_el, signed_props_el = self._build_xades_object(
            sig_id,
            qp_id,
            signed_props_id,
            certificate,
        )

        # --- 2. Compute digests ---------------------------------------
        doc_digest = self._c14n_digest(root)
        sp_digest = self._c14n_digest(signed_props_el)

        # --- 3. Build SignedInfo (both references, final digests) ------
        signed_info_el = self._build_signed_info(
            doc_digest,
            sp_digest,
            signed_props_id,
        )

        # --- 4. Sign the C14N of SignedInfo ---------------------------
        signed_info_c14n = self._c14n(signed_info_el)
        try:
            sig_value = self._sign_bytes(
                private_key=private_key,
                data=signed_info_c14n,
            )
        except Exception as exc:
            raise AuthenticationError(
                f"Failed to sign XAdES XML: {exc}",
                details={
                    "private_key_type": type(private_key).__name__,
                    "signature_method": self._signature_method,
                    "error": str(exc),
                },
            ) from exc

        # --- 5. Embed certificate -------------------------------------
        cert_der = certificate.public_bytes(serialization.Encoding.DER)
        cert_b64 = base64.b64encode(cert_der).decode("ascii")

        # --- 6. Assemble ds:Signature ---------------------------------
        signature_el = self._assemble_signature(
            sig_id,
            signed_info_el,
            sig_value,
            cert_b64,
            object_el,
        )

        root.append(signature_el)
        return etree.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
        ).decode("utf-8")

    # ------------------------------------------------------------------
    # C14N helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _c14n(element: etree._Element) -> bytes:
        return etree.tostring(
            element,
            method="c14n",
            exclusive=False,
            with_comments=False,
        )

    def _c14n_digest(self, element: etree._Element) -> str:
        return self._digest_value(self._c14n(element), self._digest_method)

    # ------------------------------------------------------------------
    # XAdES Object builder
    # ------------------------------------------------------------------

    def _build_xades_object(
        self,
        sig_id: str,
        qp_id: str,
        signed_props_id: str,
        certificate,
    ) -> tuple[etree._Element, etree._Element]:
        """Return (ds:Object, xades:SignedProperties)."""
        object_el = etree.Element(_DS + "Object", nsmap=_NSMAP_DS)

        qp = etree.SubElement(
            object_el,
            _XADES + "QualifyingProperties",
            attrib={"Id": qp_id, "Target": f"#{sig_id}"},
            nsmap=_NSMAP_XADES,
        )

        sp = etree.SubElement(
            qp,
            _XADES + "SignedProperties",
            attrib={"Id": signed_props_id},
        )
        ssp = etree.SubElement(sp, _XADES + "SignedSignatureProperties")

        # SigningTime
        st = etree.SubElement(ssp, _XADES + "SigningTime")
        st.text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # SigningCertificate
        sc = etree.SubElement(ssp, _XADES + "SigningCertificate")
        cert_node = etree.SubElement(sc, _XADES + "Cert")

        cd = etree.SubElement(cert_node, _XADES + "CertDigest")
        etree.SubElement(
            cd,
            _DS + "DigestMethod",
            attrib={"Algorithm": self._digest_method},
        )
        dv = etree.SubElement(cd, _DS + "DigestValue")
        dv.text = base64.b64encode(
            certificate.fingerprint(hashes.SHA256()),
        ).decode("ascii")

        # IssuerSerial
        is_el = etree.SubElement(cert_node, _XADES + "IssuerSerial")
        iss_name = etree.SubElement(is_el, _DS + "X509IssuerName")
        iss_name.text = certificate.issuer.rfc4514_string()
        iss_serial = etree.SubElement(is_el, _DS + "X509SerialNumber")
        iss_serial.text = str(certificate.serial_number)

        return object_el, sp

    # ------------------------------------------------------------------
    # SignedInfo builder
    # ------------------------------------------------------------------

    def _build_signed_info(
        self,
        doc_digest: str,
        sp_digest: str,
        signed_props_id: str,
    ) -> etree._Element:
        si = etree.Element(_DS + "SignedInfo", nsmap=_NSMAP_DS)

        etree.SubElement(
            si,
            _DS + "CanonicalizationMethod",
            attrib={"Algorithm": self._canonicalization_method},
        )
        etree.SubElement(
            si,
            _DS + "SignatureMethod",
            attrib={"Algorithm": self._signature_method},
        )

        # Reference #1 — document body (enveloped-signature)
        ref1 = etree.SubElement(si, _DS + "Reference", attrib={"URI": ""})
        t1 = etree.SubElement(ref1, _DS + "Transforms")
        etree.SubElement(
            t1,
            _DS + "Transform",
            attrib={"Algorithm": "http://www.w3.org/2000/09/xmldsig#enveloped-signature"},
        )
        etree.SubElement(ref1, _DS + "DigestMethod", attrib={"Algorithm": self._digest_method})
        dv1 = etree.SubElement(ref1, _DS + "DigestValue")
        dv1.text = doc_digest

        # Reference #2 — SignedProperties
        ref2 = etree.SubElement(
            si,
            _DS + "Reference",
            attrib={
                "Type": "http://uri.etsi.org/01903#SignedProperties",
                "URI": f"#{signed_props_id}",
            },
        )
        etree.SubElement(ref2, _DS + "DigestMethod", attrib={"Algorithm": self._digest_method})
        dv2 = etree.SubElement(ref2, _DS + "DigestValue")
        dv2.text = sp_digest

        return si

    # ------------------------------------------------------------------
    # Signature assembler
    # ------------------------------------------------------------------

    def _assemble_signature(
        self,
        sig_id: str,
        signed_info_el: etree._Element,
        sig_value: bytes,
        cert_b64: str,
        object_el: etree._Element,
    ) -> etree._Element:
        """Build the complete ds:Signature element in correct child order."""
        sig = etree.Element(
            _DS + "Signature",
            attrib={"Id": sig_id},
            nsmap=_NSMAP_DS,
        )

        # 1. SignedInfo
        sig.append(signed_info_el)

        # 2. SignatureValue
        sv = etree.SubElement(sig, _DS + "SignatureValue")
        sv.text = base64.b64encode(sig_value).decode("ascii")

        # 3. KeyInfo
        ki = etree.SubElement(sig, _DS + "KeyInfo")
        x509 = etree.SubElement(ki, _DS + "X509Data")
        x509_cert = etree.SubElement(x509, _DS + "X509Certificate")
        x509_cert.text = cert_b64

        # 4. Object (QualifyingProperties)
        sig.append(object_el)

        return sig

    # ------------------------------------------------------------------
    # Crypto helpers
    # ------------------------------------------------------------------

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
