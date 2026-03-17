**Nie, name.cert i name.key to nie jest to samo co plik .p12 (PKCS#12 / PFX).**

Są to **dwa zupełnie różne formaty** przechowywania certyfikatu i klucza prywatnego – i właśnie dlatego komenda, którą podałeś:

```bash
uv run ksef auth login-xades --pkcs12-path ./cert.p12 --pkcs12-password <HASLO_CERTYFIKATU>
```

oczekuje pliku **PKCS#12** (czyli jednego pliku .p12 lub .pfx), a nie osobnych .cert + .key.

### Krótko o formatach w kontekście KSeF (2026)

| Format       | Pliki zazwyczaj              | Co zawiera                              | Hasło                                  | Typowy sposób użycia w KSeF / integracjach |
|--------------|------------------------------|-----------------------------------------|----------------------------------------|--------------------------------------------|
| **PKCS#12**  | jeden plik: `.p12` lub `.pfx`| certyfikat publiczny + klucz prywatny + ewentualnie łańcuch CA | tak (obowiązkowe przy eksporcie)      | Najczęściej akceptowany przez narzędzia XAdES (w tym wiele bibliotek Python, Java, CLI do KSeF) |
| **PEM / DER osobno** | `.cert` / `.crt` / `.cer` + `.key` | certyfikat publiczny (.cert) + klucz prywatny (.key) | klucz prywatny może mieć hasło osobno | Często pobierany bezpośrednio z MCU KSeF (certyfikaty uwierzytelniające / offline) |

W praktyce:

- Certyfikaty **KSeF** (te pobierane z Modułu Certyfikatów i Uprawnień – MCU) są najczęściej wydawane właśnie jako **para .cert + .key** (certyfikat w formacie PEM/DER + niezaszyfrowany lub zaszyfrowany klucz prywatny).
- Natomiast wiele narzędzi (w tym te oparte na XAdES do uwierzytelniania w API KSeF) oczekuje **jednego pliku PKCS#12**, bo jest to format wygodniejszy do importu klucza + certyfikatu razem (np. w Java KeyStore, Python signxml / cryptography, pyksef itp.).

### Co zrobić, jeśli masz name.cert i name.key?

Musisz połączyć je w plik .p12 / .pfx. Najprostszy i najbezpieczniejszy sposób (OpenSSL jest prawie na każdym systemie):

```bash
openssl pkcs12 -export \
  -out geosys.p12 \
  -inkey geosys.key \
  -in geosys.crt \
  -certfile geosys.crt   # ewentualnie dodaj łańcuch CA jeśli masz osobny plik .ca
```

- Zostaniesz poproszony o podanie hasła eksportu → to będzie dokładnie to `<HASLO_CERTYFIKATU>`, którego używasz potem w `--pkcs12-password`.
- Jeśli klucz prywatny (.key) ma już własne hasło → podaj je, gdy OpenSSL zapyta o import („Enter pass phrase for name.key”).

Po tym poleceniu powinieneś mieć plik `name.p12`, który możesz użyć w komendzie:

```bash
uv run ksef auth login-xades --pkcs12-path ./name.p12 --pkcs12-password TwojeHasloDoP12
```

### Uwaga o certyfikatach KSeF w 2026

- Certyfikaty KSeF dzielą się na **uwierzytelniające** (do logowania do API) i **do trybu offline** (do podpisywania faktur w trybie awaryjnym / offline24).
- Oba typy zazwyczaj przychodzą jako .cert + .key.
- Jeśli narzędzie, którego używasz (prawdopodobnie jakiś wrapper / fork pyksef lub podobny projekt), nie akceptuje osobno cert+key → konwersja do PKCS#12 jest standardowym rozwiązaniem.

Jeśli po konwersji nadal masz błąd – podaj komunikat błędu, to pomogę dalej (może być problem z hasłem, łańcuchem CA, wersją OpenSSL, szyfrowaniem klucza itp.).
