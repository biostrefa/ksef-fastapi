# SQLite Configuration

This project has been configured to use SQLite as the database.

## Database File
- **Location**: `./ksef.db` (in the project root)
- **Driver**: `sqlite+aiosqlite` (async SQLite support)

## Configuration Changes Made

1. **Dependencies**: Updated `pyproject.toml` to use `sqlalchemy[aiosqlite]` instead of `sqlalchemy[postgresql-asyncpg]`
2. **Environment**: Set `DATABASE_URL=sqlite+aiosqlite:///./ksef.db` in `.env`
3. **Migrations**: Updated Alembic configuration to work with SQLite

## Database Operations

### Create New Migration
```bash
uv run alembic revision --autogenerate -m "Description of changes"
```

### Run Migrations
```bash
uv run alembic upgrade head
```

### Reset Database
```bash
rm ksef.db
uv run alembic upgrade head
```

## SQLite Notes

- SQLite is file-based and doesn't require a separate server
- Perfect for development and small to medium applications
- Supports concurrent access but has locking limitations
- Database file will be created automatically on first run
