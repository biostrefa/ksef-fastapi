# ksef-fastapi

## work in progress

## Setup
```
uv init
```


```
uv add alembic alembic-utils "fastapi[standard]" "psycopg[binary]" pydantic-settings python-dotenv python-keycloak requests slowapi "sqlalchemy[postgresql-asyncpg]" --dev httpx pytest pytest-asyncio ruff
```

```
uv run alembic init -t async migrations
```
## Get the certificates

```
uv run python scripts/download_mf_certificate.py
```
It is saved in `certyficates/mf_public_encryption_cert.pem`
