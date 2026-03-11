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
