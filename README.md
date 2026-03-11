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
