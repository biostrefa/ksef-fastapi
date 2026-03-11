Struktura katalogów w ASCII

project-root/
|
+-- app/
|   |
|   +-- main.py
|   |    `-- start aplikacji FastAPI, rejestracja routerów, lifespan
|   |
|   +-- core/
|   |   |
|   |   +-- config.py
|   |   |    `-- ustawienia środowiskowe, URL-e KSeF, timeouty, retry
|   |   |
|   |   +-- security.py
|   |   |    `-- helpery bezpieczeństwa, maskowanie danych, ochrona sekretów
|   |   |
|   |   +-- logging.py
|   |   |    `-- konfiguracja loggera i format logów
|   |   |
|   |   +-- exceptions.py
|   |   |    `-- wyjątki aplikacyjne i mapowanie błędów
|   |   |
|   |   +-- constants.py
|   |        `-- stałe systemowe, nazwy statusów, typy środowisk
|   |
|   +-- api/
|   |   |
|   |   +-- deps.py
|   |   |    `-- dependency injection dla serwisów i repozytoriów
|   |   |
|   |   +-- routers/
|   |       |
|   |       +-- health_router.py
|   |       |    `-- healthcheck / readiness / liveness
|   |       |
|   |       +-- ksef_auth_router.py
|   |       |    `-- endpointy wewnętrzne do auth KSeF
|   |       |
|   |       +-- ksef_session_router.py
|   |       |    `-- endpointy do sesji online / batch
|   |       |
|   |       +-- ksef_invoice_router.py
|   |       |    `-- endpointy wysyłki i odczytu faktur
|   |       |
|   |       +-- ksef_status_router.py
|   |       |    `-- statusy, UPO, monitoring procesu
|   |       |
|   |       +-- webhook_router.py
|   |            `-- opcjonalne callbacki / zdarzenia wewnętrzne
|   |
|   +-- schemas/
|   |   |
|   |   +-- common.py
|   |   |    `-- wspólne modele request/response
|   |   |
|   |   +-- auth.py
|   |   |    `-- modele wejścia/wyjścia dla auth
|   |   |
|   |   +-- sessions.py
|   |   |    `-- modele sesji online / batch
|   |   |
|   |   +-- invoices.py
|   |   |    `-- modele wysyłki faktury, statusów, UPO
|   |   |
|   |   +-- errors.py
|   |        `-- zunifikowane odpowiedzi błędów
|   |
|   +-- domain/
|   |   |
|   |   +-- models/
|   |   |   |
|   |   |   +-- invoice.py
|   |   |   |    `-- model domenowy faktury
|   |   |   |
|   |   |   +-- session.py
|   |   |   |    `-- model domenowy sesji KSeF
|   |   |   |
|   |   |   +-- auth.py
|   |   |   |    `-- model domenowy tokenów / challenge / auth context
|   |   |   |
|   |   |   +-- status.py
|   |   |        `-- enumy i modele statusów lokalnych
|   |   |
|   |   +-- builders/
|   |   |   |
|   |   |   +-- invoice_fa3_builder.py
|   |   |        `-- generowanie XML zgodnego z FA(3)
|   |   |
|   |   +-- validators/
|   |   |   |
|   |   |   +-- invoice_validator.py
|   |   |   |    `-- walidacja biznesowa danych faktury
|   |   |   |
|   |   |   +-- tax_identifier_validator.py
|   |   |        `-- walidacja NIP, danych kontrahenta itd.
|   |   |
|   |   +-- mappers/
|   |   |   |
|   |   |   +-- invoice_mapper.py
|   |   |   |    `-- mapowanie ERP -> model domenowy -> XML/input do KSeF
|   |   |   |
|   |   |   +-- ksef_response_mapper.py
|   |   |        `-- mapowanie odpowiedzi KSeF do modeli lokalnych
|   |   |
|   |   +-- strategies/
|   |       |
|   |       +-- auth_strategy_base.py
|   |       |    `-- interfejs strategii auth
|   |       |
|   |       +-- xades_auth_strategy.py
|   |       |    `-- strategia auth podpisem
|   |       |
|   |       +-- token_auth_strategy.py
|   |            `-- strategia auth tokenem KSeF
|   |
|   +-- services/
|   |   |
|   |   +-- auth_service.py
|   |   |    `-- challenge, redeem token, refresh token, lifecycle auth
|   |   |
|   |   +-- session_service.py
|   |   |    `-- otwarcie / zamknięcie sesji, reference numbers
|   |   |
|   |   +-- invoice_service.py
|   |   |    `-- główna orkiestracja wysyłki faktury
|   |   |
|   |   +-- status_service.py
|   |   |    `-- pobieranie statusów sesji, statusów faktur i UPO
|   |   |
|   |   +-- retry_service.py
|   |   |    `-- ponowienia, polling, timeouty, dead-letter decisions
|   |   |
|   |   +-- audit_service.py
|   |        `-- zapis śladu operacyjnego
|   |
|   +-- infrastructure/
|   |   |
|   |   +-- http/
|   |   |   |
|   |   |   +-- base_client.py
|   |   |   |    `-- wspólny klient HTTP, retry, timeout, nagłówki
|   |   |   |
|   |   |   +-- ksef_http_client.py
|   |   |        `-- surowe wywołania endpointów KSeF
|   |   |
|   |   +-- crypto/
|   |   |   |
|   |   |   +-- encryption_service.py
|   |   |   |    `-- szyfrowanie payloadu, SHA-256, obsługa kluczy
|   |   |   |
|   |   |   +-- certificate_loader.py
|   |   |        `-- ładowanie certyfikatów i materiału kluczowego
|   |   |
|   |   +-- persistence/
|   |   |   |
|   |   |   +-- db.py
|   |   |   |    `-- engine, sessionmaker, połączenie do bazy
|   |   |   |
|   |   |   +-- models/
|   |   |   |   |
|   |   |   |   +-- token_model.py
|   |   |   |   |    `-- tabela tokenów / auth context
|   |   |   |   |
|   |   |   |   +-- session_model.py
|   |   |   |   |    `-- tabela sesji KSeF
|   |   |   |   |
|   |   |   |   +-- invoice_submission_model.py
|   |   |   |   |    `-- tabela rekordów wysyłki i statusów
|   |   |   |   |
|   |   |   |   +-- audit_log_model.py
|   |   |   |        `-- tabela audytu
|   |   |   |
|   |   |   +-- repositories/
|   |   |       |
|   |   |       +-- token_repository.py
|   |   |       |    `-- zapis i odczyt tokenów
|   |   |       |
|   |   |       +-- session_repository.py
|   |   |       |    `-- zapis i odczyt sesji
|   |   |       |
|   |   |       +-- invoice_repository.py
|   |   |       |    `-- zapis faktur, statusów i UPO
|   |   |       |
|   |   |       +-- audit_log_repository.py
|   |   |            `-- zapis operacji i błędów
|   |   |
|   |   +-- adapters/
|   |       |
|   |       +-- erp_adapter.py
|   |       |    `-- pobranie danych faktur z ERP/CRM
|   |       |
|   |       +-- storage_adapter.py
|   |            `-- zapis XML, UPO, payloadów do storage
|   |
|   +-- workers/
|   |   |
|   |   +-- poll_ksef_statuses.py
|   |   |    `-- okresowy polling statusów sesji i dokumentów
|   |   |
|   |   +-- retry_failed_submissions.py
|   |        `-- zadania ponawiające
|   |
|   +-- utils/
|   |   |
|   |   +-- xml_utils.py
|   |   |    `-- helpery XML
|   |   |
|   |   +-- hash_utils.py
|   |   |    `-- helpery hashy i checksum
|   |   |
|   |   +-- datetime_utils.py
|   |        `-- czas, strefy, formatowanie
|   |
|   +-- tests/
|       |
|       +-- unit/
|       |   |
|       |   +-- test_invoice_builder.py
|       |   +-- test_invoice_validator.py
|       |   +-- test_auth_service.py
|       |   +-- test_session_service.py
|       |   `-- test_status_service.py
|       |
|       +-- integration/
|       |   |
|       |   +-- test_ksef_http_client.py
|       |   +-- test_invoice_flow_online.py
|       |   `-- test_auth_flow.py
|       |
|       `-- fixtures/
|           |
|           +-- sample_fa3.xml
|           +-- challenge_response.json
|           `-- session_status_response.json
|
+-- alembic/
|   |
|   +-- versions/
|   `-- env.py
|
+-- _docs/
|   |
|   +-- architecture/
|   |   +-- ksef_modules.md
|   |   `-- ksef_sequence_online.md
|   |
|   `-- api/
|       `-- internal_endpoints.md
|
+-- scripts/
|   |
|   +-- run_dev.sh
|   +-- run_worker.sh
|   `-- generate_openapi_client.sh
|
+-- pyproject.toml
+-- .env
+-- .env.example
`-- README.md




Jak to mapuje się do odpowiedzialności

Najkrócej:

api/              -> przyjmuje requesty z Twojego systemu
schemas/          -> opisuje kontrakty request/response
domain/           -> reguły biznesowe i modele faktury/sesji
services/         -> orkiestruje pełne procesy KSeF
infrastructure/   -> HTTP, baza, szyfrowanie, storage
workers/          -> polling i retry poza request-response
tests/            -> testy jednostkowe i integracyjne
