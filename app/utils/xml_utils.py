"""
XML utilities.

This module provides:
- XML parsing and generation
- XML validation helpers
- XML formatting utilities
- XML namespace handling

Functions:
    create_root(tag: str, nsmap: dict | None = None) -> Element: Create XML root element
    append_text_element(parent: Element, tag: str, value: str | None) -> Element: Append text element
    serialize_xml(element: Element) -> str: Serialize XML element to string
    parse_xml(xml_content: str) -> Element: Parse XML content to element
    strip_xml_declaration(xml_content: str) -> str: Strip XML declaration
"""

from __future__ import annotations

from io import BytesIO
import re
from typing import Any

from lxml import etree
from lxml.etree import _Element as Element


XML_DECLARATION_RE = re.compile(r"^\s*<\?xml[^>]*\?>\s*", re.IGNORECASE)


def create_root(tag: str, nsmap: dict[str | None, str] | None = None) -> Element:
    """
    Create XML root element.

    Examples:
        create_root("Root")
        create_root("{urn:test}Root", nsmap={None: "urn:test"})
    """
    return etree.Element(tag, nsmap=nsmap)


def append_text_element(parent: Element, tag: str, value: str | None) -> Element:
    """
    Append child element with optional text value.

    If value is None, an empty element is still created.
    """
    child = etree.SubElement(parent, tag)
    if value is not None:
        child.text = str(value)
    return child


def append_optional_text_element(
    parent: Element,
    tag: str,
    value: str | None,
) -> Element | None:
    """
    Append child element only if value is not None and not empty after stripping.
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    child = etree.SubElement(parent, tag)
    child.text = text
    return child


def set_text(element: Element, value: str | None) -> Element:
    """
    Set text content on an existing element.
    """
    element.text = None if value is None else str(value)
    return element


def serialize_xml(
    element: Element,
    *,
    pretty_print: bool = False,
    xml_declaration: bool = True,
    encoding: str = "UTF-8",
) -> str:
    """
    Serialize XML element to string.
    """
    xml_bytes = etree.tostring(
        element,
        pretty_print=pretty_print,
        xml_declaration=xml_declaration,
        encoding=encoding,
    )
    return xml_bytes.decode(encoding)


def parse_xml(xml_content: str) -> Element:
    """
    Parse XML string into root element.
    """
    parser = etree.XMLParser(
        remove_blank_text=False,
        resolve_entities=False,
        no_network=True,
        recover=False,
        huge_tree=False,
    )
    return etree.fromstring(xml_content.encode("utf-8"), parser=parser)


def parse_xml_bytes(xml_content: bytes) -> Element:
    """
    Parse XML bytes into root element.
    """
    parser = etree.XMLParser(
        remove_blank_text=False,
        resolve_entities=False,
        no_network=True,
        recover=False,
        huge_tree=False,
    )
    return etree.fromstring(xml_content, parser=parser)


def strip_xml_declaration(xml_content: str) -> str:
    """
    Remove XML declaration from the beginning of XML string.
    """
    return XML_DECLARATION_RE.sub("", xml_content, count=1)


def pretty_format_xml(xml_content: str, *, xml_declaration: bool = True) -> str:
    """
    Parse and re-serialize XML in pretty-printed form.
    """
    root = parse_xml(xml_content)
    return serialize_xml(
        root,
        pretty_print=True,
        xml_declaration=xml_declaration,
    )


def get_namespace_map(element: Element) -> dict[str | None, str]:
    """
    Return namespace map from element.
    """
    return dict(element.nsmap)


def find_one(
    element: Element,
    xpath: str,
    namespaces: dict[str, str] | None = None,
) -> Element | None:
    """
    Find first element matching XPath.
    """
    result = element.xpath(xpath, namespaces=namespaces or {})
    if not result:
        return None
    first = result[0]
    return first if isinstance(first, etree._Element) else None


def find_text(
    element: Element,
    xpath: str,
    namespaces: dict[str, str] | None = None,
    default: str | None = None,
) -> str | None:
    """
    Find first matching element/value and return text.
    """
    result = element.xpath(xpath, namespaces=namespaces or {})
    if not result:
        return default

    first = result[0]
    if isinstance(first, etree._Element):
        return first.text if first.text is not None else default

    return str(first) if first is not None else default


def validate_xml_against_xsd(
    xml_content: str | bytes,
    xsd_content: str | bytes,
) -> tuple[bool, list[str]]:
    """
    Validate XML against XSD content.

    Returns:
        (is_valid, error_messages)
    """
    xml_bytes = (
        xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content
    )
    xsd_bytes = (
        xsd_content.encode("utf-8") if isinstance(xsd_content, str) else xsd_content
    )

    xml_parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        recover=False,
        huge_tree=False,
    )

    xml_doc = etree.parse(BytesIO(xml_bytes), parser=xml_parser)
    xsd_doc = etree.parse(BytesIO(xsd_bytes), parser=xml_parser)
    schema = etree.XMLSchema(xsd_doc)

    is_valid = schema.validate(xml_doc)
    errors = [str(error) for error in schema.error_log]
    return is_valid, errors


def canonicalize_xml(
    xml_content: str | bytes,
    *,
    exclusive: bool = False,
    with_comments: bool = False,
) -> bytes:
    """
    Canonicalize XML (C14N) and return bytes.

    Useful for signing and digest calculation.
    """
    root = parse_xml(
        xml_content.decode("utf-8") if isinstance(xml_content, bytes) else xml_content
    )
    return etree.tostring(
        root,
        method="c14n",
        exclusive=exclusive,
        with_comments=with_comments,
    )


def element_to_dict(element: Element) -> dict[str, Any]:
    """
    Convert XML element into a simple nested dictionary.

    Intended for debugging or lightweight inspection, not full round-trip fidelity.
    """
    children = list(element)

    if not children:
        return {
            "tag": element.tag,
            "text": element.text.strip() if element.text else None,
            "attributes": dict(element.attrib),
        }

    return {
        "tag": element.tag,
        "attributes": dict(element.attrib),
        "children": [element_to_dict(child) for child in children],
    }
