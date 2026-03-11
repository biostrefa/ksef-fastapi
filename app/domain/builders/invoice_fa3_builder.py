"""
FA(3) XML builder for invoices.

This module provides:
- FA(3) XML generation
- Invoice XML structure building
- XML validation and formatting
- KSeF XML compliance

Classes:
    InvoiceFa3Builder: FA(3) XML builder for invoices

Methods:
    build(invoice: Invoice) -> str: Build complete FA(3) XML from invoice
    _build_header(invoice: Invoice) -> Element: Build XML header section
    _build_seller(invoice: Invoice) -> Element: Build seller XML section
    _build_buyer(invoice: Invoice) -> Element: Build buyer XML section
    _build_lines(invoice: Invoice) -> Element: Build invoice lines XML section
    _build_totals(invoice: Invoice) -> Element: Build totals XML section
    _serialize_xml(root: Element) -> str: Serialize XML element to string

Note: This should be a pure XML builder without HTTP and database dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

from app.domain.models.invoice import Address, Invoice, InvoiceLine, InvoiceParty


class InvoiceFa3Builder:
    """
    Poprawiony builder bazowy dla FA(3).

    Założenia:
    - buduje główne sekcje: Naglowek, Podmiot1, Podmiot2, Fa, FaWiersz
    - używa układu adresów KodKraju + AdresL1/AdresL2
    - używa DaneKontaktowe dla Email/Telefon
    - używa pól FaWiersz: NrWierszaFa, P_6A, P_7, P_8A, P_8B, P_9A, P_11, P_12
    - używa P_15 jako należności ogółem

    Świadomie nie obejmuje jeszcze pełnej implementacji:
    - Podmiot3 / PodmiotUpowazniony
    - pełnych bucketów P_13_* / P_14_*
    - Rozliczenie / WarunkiTransakcji / Stopka / Zalacznik
    - wszystkich szczególnych wariantów korekt i zaliczek

    Uwaga:
    - root_tag zostawiłem konfigurowalny, aby nie zaszywać na stałe
      nazwy roota bez pełnego przepięcia na finalne XSD po Twojej stronie.
    """

    def __init__(
        self,
        *,
        root_tag: str = "Faktura",
        namespace_uri: str | None = None,
        pretty_print: bool = False,
        system_info: str = "FastAPI-KSeF-FA3",
    ) -> None:
        self.root_tag = root_tag
        self.namespace_uri = namespace_uri
        self.pretty_print = pretty_print
        self.system_info = system_info

    def build(self, invoice: Invoice) -> str:
        root = Element(self._tag(self.root_tag))

        self._build_naglowek(root)
        self._build_podmiot1(root, invoice.seller)
        self._build_podmiot2(root, invoice.buyer)
        self._build_fa(root, invoice)

        xml_bytes = tostring(root, encoding="utf-8", xml_declaration=True)

        if not self.pretty_print:
            return xml_bytes.decode("utf-8")

        parsed = minidom.parseString(xml_bytes)
        return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

    def _tag(self, name: str) -> str:
        if self.namespace_uri:
            return f"{{{self.namespace_uri}}}{name}"
        return name

    def _append_text(self, parent: Element, tag: str, value: str | None) -> Element:
        node = SubElement(parent, self._tag(tag))
        if value is not None:
            node.text = value
        return node

    def _append_bool_flag(self, parent: Element, tag: str, value: bool | None) -> None:
        if value is None:
            return
        self._append_text(parent, tag, "1" if value else "2")

    def _decimal(self, value: Decimal | int | float | str) -> str:
        if isinstance(value, Decimal):
            return format(value, "f")
        if isinstance(value, str):
            return value
        return format(Decimal(str(value)), "f")

    def _utc_now_z(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _build_naglowek(self, root: Element) -> None:
        naglowek = SubElement(root, self._tag("Naglowek"))

        kod_formularza = SubElement(naglowek, self._tag("KodFormularza"))
        kod_formularza.text = "FA"
        kod_formularza.set("kodSystemowy", "FA (3)")
        kod_formularza.set("wersjaSchemy", "1-0E")

        self._append_text(naglowek, "WariantFormularza", "3")
        self._append_text(naglowek, "DataWytworzeniaFa", self._utc_now_z())
        self._append_text(naglowek, "SystemInfo", self.system_info)

    def _build_podmiot1(self, root: Element, seller: InvoiceParty) -> None:
        podmiot1 = SubElement(root, self._tag("Podmiot1"))
        self._build_party(podmiot1, seller, is_buyer=False)

    def _build_podmiot2(self, root: Element, buyer: InvoiceParty) -> None:
        podmiot2 = SubElement(root, self._tag("Podmiot2"))
        self._build_party(podmiot2, buyer, is_buyer=True)

    def _build_party(
        self, parent: Element, party: InvoiceParty, *, is_buyer: bool
    ) -> None:
        dane = SubElement(parent, self._tag("DaneIdentyfikacyjne"))

        # Minimalne mapowanie zgodne z obecnym modelem.
        # Docelowo dla Podmiot2 warto rozdzielić:
        # NIP / NrVatUE / NrID / BrakID.
        if party.tax_id:
            self._append_text(dane, "NIP", party.tax_id)
        elif is_buyer:
            self._append_text(dane, "BrakID", "1")
        else:
            raise ValueError("Seller must have tax_id for FA(3) Podmiot1")

        self._append_text(dane, "Nazwa", party.name)

        self._build_address(parent, party.address)
        self._build_contact(parent, party)

        # Pola dodatkowe wspierane przez przyszłe rozszerzenie modelu.
        nr_klienta = getattr(party, "customer_number", None)
        id_nabywcy = getattr(party, "buyer_link_id", None)
        jst_flag = getattr(party, "jst_flag", None)
        gv_flag = getattr(party, "gv_flag", None)

        if is_buyer:
            self._append_text(parent, "NrKlienta", nr_klienta)
            self._append_text(parent, "IDNabywcy", id_nabywcy)
            self._append_bool_flag(parent, "JST", jst_flag)
            self._append_bool_flag(parent, "GV", gv_flag)

    def _build_address(self, parent: Element, address: Address | None) -> None:
        if not address:
            return

        adres = SubElement(parent, self._tag("Adres"))
        self._append_text(adres, "KodKraju", address.country_code)

        adres_l1, adres_l2 = self._map_address_lines(address)
        self._append_text(adres, "AdresL1", adres_l1)
        self._append_text(adres, "AdresL2", adres_l2)

        gln = getattr(address, "gln", None)
        self._append_text(adres, "GLN", gln)

    def _build_contact(self, parent: Element, party: InvoiceParty) -> None:
        email = getattr(party, "email", None)
        phone = getattr(party, "phone", None)

        if not email and not phone:
            return

        kontakt = SubElement(parent, self._tag("DaneKontaktowe"))
        self._append_text(kontakt, "Email", email)
        self._append_text(kontakt, "Telefon", phone)

    def _map_address_lines(self, address: Address) -> tuple[str, str | None]:
        # Wspiera zarówno przyszły model address_line_1/address_line_2,
        # jak i obecny model street/building_no/apartment_no/postal_code/city.
        line1 = getattr(address, "address_line_1", None)
        line2 = getattr(address, "address_line_2", None)

        if line1:
            return line1, line2

        street = getattr(address, "street", None)
        building_no = getattr(address, "building_no", None)
        apartment_no = getattr(address, "apartment_no", None)
        postal_code = getattr(address, "postal_code", None)
        city = getattr(address, "city", None)

        street_part = ""
        if street:
            street_part = street
            if building_no:
                street_part += f" {building_no}"
            if apartment_no:
                street_part += f"/{apartment_no}"

        city_part = ""
        if postal_code and city:
            city_part = f"{postal_code} {city}"
        elif city:
            city_part = city
        elif postal_code:
            city_part = postal_code

        if street_part and city_part:
            return f"{street_part}, {city_part}", None
        if street_part:
            return street_part, city_part or None
        if city_part:
            return city_part, None

        return "", None

    def _build_fa(self, root: Element, invoice: Invoice) -> None:
        fa = SubElement(root, self._tag("Fa"))

        self._append_text(fa, "KodWaluty", invoice.currency.value)
        self._append_text(fa, "P_1", invoice.issue_date.isoformat())

        # P_1M - miesiąc - tylko gdy model to wspiera.
        p_1m = getattr(invoice, "issue_month", None)
        self._append_text(fa, "P_1M", str(p_1m) if p_1m is not None else None)

        self._append_text(fa, "P_2", invoice.invoice_number)

        # W FA(3) może wystąpić P_6 albo OkresFa.
        # Ten builder obsługuje prosty przypadek jednej daty sprzedaży.
        if invoice.sale_date:
            self._append_text(fa, "P_6", invoice.sale_date.isoformat())

        self._append_text(fa, "RodzajFaktury", invoice.invoice_kind.value)

        # Minimalnie poprawne mapowanie należności ogółem.
        self._append_text(fa, "P_15", self._decimal(invoice.totals.total_gross))

        # Pola korekty - tylko jeśli model je posiada.
        self._append_text(
            fa, "PrzyczynaKorekty", getattr(invoice, "correction_reason", None)
        )
        self._append_text(
            fa, "NrFaKorygowanej", getattr(invoice, "original_invoice_number", None)
        )
        self._append_text(
            fa, "NrKSeFFaKorygowanej", getattr(invoice, "original_ksef_number", None)
        )

        # Adnotacje / dodatkowe opisy - uproszczone wsparcie.
        notes = getattr(invoice, "notes", None)
        if notes:
            dodatkowy_opis = SubElement(fa, self._tag("DodatkowyOpis"))
            self._append_text(dodatkowy_opis, "Klucz", "Uwagi")
            self._append_text(dodatkowy_opis, "Wartosc", notes)

        self._build_payment(fa, invoice)
        self._build_lines(fa, invoice)

        # TODO:
        # - P_13_* / P_14_* po rozbudowie modelu bucketów VAT
        # - Rozliczenie
        # - WarunkiTransakcji
        # - Zamowienie
        # - FakturaZaliczkowa
        # - Stopka / Zalacznik

    def _build_payment(self, fa: Element, invoice: Invoice) -> None:
        payment = getattr(invoice, "payment", None)
        if not payment:
            return

        platnosc = SubElement(fa, self._tag("Platnosc"))

        # TerminPlatnosci
        if payment.due_date:
            termin = SubElement(platnosc, self._tag("TerminPlatnosci"))
            termin_opis = SubElement(termin, self._tag("TerminOpis"))
            self._append_text(termin_opis, "Ilosc", "0")
            self._append_text(termin_opis, "Jednostka", "dni")
            self._append_text(
                termin_opis, "ZdarzeniePoczatkowe", payment.due_date.isoformat()
            )

        # FormaPlatnosci:
        # Używam wyłącznie pewnego mapowania "transfer" -> 6.
        # Pozostałe typy idą jako płatność opisana tekstowo.
        method = getattr(payment, "method", None)
        method_value = getattr(method, "value", None) if method else None

        if method_value == "transfer":
            self._append_text(platnosc, "FormaPlatnosci", "6")
        elif method_value:
            self._append_text(platnosc, "PlatnoscInna", "1")
            self._append_text(platnosc, "OpisPlatnosci", method_value)

        # RachunekBankowy
        bank_account = getattr(payment, "bank_account", None)
        if bank_account:
            rachunek = SubElement(platnosc, self._tag("RachunekBankowy"))
            self._append_text(rachunek, "NrRB", bank_account)

        # MPP nie ma tu osobnego własnego pola z poprzedniego buildera.
        # Docelowo powinno być mapowane do właściwej sekcji adnotacji / cech faktury
        # po rozszerzeniu modelu domenowego.

    def _build_lines(self, fa: Element, invoice: Invoice) -> None:
        for line in invoice.lines:
            self._build_single_line(fa, line, invoice)

    def _build_single_line(
        self, fa: Element, line: InvoiceLine, invoice: Invoice
    ) -> None:
        wiersz = SubElement(fa, self._tag("FaWiersz"))

        self._append_text(wiersz, "NrWierszaFa", str(line.line_no))

        uu_id = getattr(line, "uu_id", None)
        self._append_text(wiersz, "UU_ID", uu_id)

        # P_6A – data pozycji. Jeżeli linia nie ma własnej daty,
        # użyj daty sprzedaży z faktury, a jeśli jej brak - daty wystawienia.
        line_sale_date = (
            getattr(line, "line_sale_date", None)
            or invoice.sale_date
            or invoice.issue_date
        )
        self._append_text(wiersz, "P_6A", line_sale_date.isoformat())

        self._append_text(wiersz, "P_7", line.name)
        self._append_text(wiersz, "P_8A", line.unit_code)
        self._append_text(wiersz, "P_8B", self._decimal(line.quantity))
        self._append_text(wiersz, "P_9A", self._decimal(line.unit_net_price))
        self._append_text(wiersz, "P_11", self._decimal(line.net_value))
        self._append_text(wiersz, "P_12", self._decimal(line.vat_rate))

        # Pola fakultatywne / dodatkowe
        self._append_text(wiersz, "PKWiU", getattr(line, "pkwiu", None))
        self._append_text(wiersz, "GTIN", getattr(line, "gtin", None))
        self._append_text(wiersz, "CN", getattr(line, "cn", None))
        self._append_text(wiersz, "PKOB", getattr(line, "pkob", None))

        stan_przed = getattr(line, "state_before_flag", None)
        if stan_przed:
            self._append_text(wiersz, "StanPrzed", "1")

        # GTU / procedury - przygotowane na rozszerzenie modelu.
        gtu_code = getattr(line, "gtu_code", None)
        if gtu_code:
            self._append_text(wiersz, "GTU", gtu_code)

        procedure_code = getattr(line, "procedure_code", None)
        if procedure_code:
            self._append_text(wiersz, "Procedura", procedure_code)
