# KSeF FastAPI Project Structure

## Overview

This document describes the complete structure and purpose of the KSeF FastAPI integration project. The project follows a clean architecture pattern with clear separation of concerns.

## Architecture Principles

- **Clean Architecture**: Business logic separated from infrastructure concerns
- **Domain-Driven Design**: Rich domain models with business logic
- **Dependency Injection**: Loose coupling through DI container
- **Testability**: All components are unit testable
- **SOLID Principles**: Single responsibility, open/closed, Liskov substitution, interface segregation, dependency inversion

## Directory Structure

```
project-root/
├── app/                           # Main application package
│   ├── main.py                    # FastAPI application entry point
│   ├── core/                      # Core application functionality
│   │   ├── config.py              # Environment settings and configuration
│   │   ├── security.py            # Security helpers and data protection
│   │   ├── logging.py             # Logging configuration and utilities
│   │   ├── exceptions.py          # Custom exceptions and error handling
│   │   └── constants.py            # System constants and enums
│   ├── api/                       # API layer
│   │   ├── deps.py                # Dependency injection setup
│   │   └── routers/               # FastAPI routers
│   │       ├── health_router.py      # Healthcheck endpoints
│   │       ├── ksef_auth_router.py   # KSeF authentication endpoints
│   │       ├── ksef_session_router.py # KSeF session management
│   │       ├── ksef_invoice_router.py # Invoice submission endpoints
│   │       ├── ksef_status_router.py  # Status monitoring endpoints
│   │       └── webhook_router.py      # Webhook and callback endpoints
│   ├── schemas/                   # Pydantic models for API
│   │   ├── common.py              # Common request/response models
│   │   ├── auth.py                # Authentication models
│   │   ├── sessions.py            # Session models
│   │   ├── invoices.py            # Invoice models
│   │   └── errors.py              # Error response models
│   ├── domain/                    # Business logic and domain models
│   │   ├── models/                # Domain entities
│   │   │   ├── invoice.py         # Invoice domain model
│   │   │   ├── session.py         # KSeF session domain model
│   │   │   ├── auth.py            # Authentication domain model
│   │   │   └── status.py          # Status enums and models
│   │   ├── builders/              # Domain builders
│   │   │   └── invoice_fa3_builder.py # FA(3) XML generation
│   │   ├── validators/            # Business validation
│   │   │   ├── invoice_validator.py    # Invoice validation
│   │   │   └── tax_identifier_validator.py # Tax ID validation
│   │   ├── mappers/               # Data transformation
│   │   │   ├── invoice_mapper.py      # ERP to domain mapping
│   │   │   └── ksef_response_mapper.py # KSeF response mapping
│   │   └── strategies/            # Strategy pattern implementations
│   │       ├── auth_strategy_base.py   # Base auth strategy
│   │       ├── xades_auth_strategy.py  # XAdES signature auth
│   │       └── token_auth_strategy.py  # Token-based auth
│   ├── services/                  # Application services
│   │   ├── auth_service.py        # Authentication orchestration
│   │   ├── session_service.py     # Session management
│   │   ├── invoice_service.py     # Invoice submission orchestration
│   │   ├── status_service.py      # Status monitoring
│   │   ├── retry_service.py       # Retry and polling logic
│   │   └── audit_service.py       # Audit logging
│   ├── infrastructure/            # External integrations
│   │   ├── http/                  # HTTP clients
│   │   │   ├── base_client.py     # Common HTTP functionality
│   │   │   └── ksef_http_client.py # KSeF API client
│   │   ├── crypto/                # Cryptographic operations
│   │   │   ├── encryption_service.py  # Encryption and hashing
│   │   │   └── certificate_loader.py   # Certificate handling
│   │   ├── persistence/           # Database layer
│   │   │   ├── db.py              # Database configuration
│   │   │   ├── models/            # SQLAlchemy models
│   │   │   │   ├── token_model.py      # Token storage
│   │   │   │   ├── session_model.py    # Session storage
│   │   │   │   ├── invoice_submission_model.py # Invoice records
│   │   │   │   └── audit_log_model.py  # Audit records
│   │   │   └── repositories/      # Data access layer
│   │   │       ├── token_repository.py     # Token CRUD
│   │   │       ├── session_repository.py   # Session CRUD
│   │   │       ├── invoice_repository.py   # Invoice CRUD
│   │   │       └── audit_log_repository.py # Audit CRUD
│   │   └── adapters/              # External system adapters
│   │       ├── erp_adapter.py     # ERP system integration
│   │       └── storage_adapter.py # File storage integration
│   ├── workers/                   # Background processing
│   │   ├── poll_ksef_statuses.py   # Status polling worker
│   │   └── retry_failed_submissions.py # Retry worker
│   ├── utils/                      # Utility functions
│   │   ├── xml_utils.py           # XML processing utilities
│   │   ├── hash_utils.py          # Hash and checksum utilities
│   │   └── datetime_utils.py      # Date/time utilities
│   └── tests/                      # Test suite
│       ├── unit/                  # Unit tests
│       │   ├── test_invoice_builder.py
│       │   ├── test_invoice_validator.py
│       │   ├── test_auth_service.py
│       │   ├── test_session_service.py
│       │   └── test_status_service.py
│       ├── integration/           # Integration tests
│       │   ├── test_ksef_http_client.py
│       │   ├── test_invoice_flow_online.py
│       │   └── test_auth_flow.py
│       └── fixtures/              # Test data
│           ├── sample_fa3.xml
│           ├── challenge_response.json
│           └── session_status_response.json
├── alembic/                       # Database migrations
│   ├── versions/                   # Migration files
│   └── env.py                      # Alembic environment
├── _docs/                         # Documentation
│   ├── architecture/              # Architecture documentation
│   │   ├── ksef_modules.md        # KSeF module overview
│   │   └── ksef_sequence_online.md # Online sequence diagram
│   └── api/                       # API documentation
│       └── internal_endpoints.md  # Internal API endpoints
├── scripts/                       # Utility scripts
│   ├── run_dev.sh                 # Development server startup
│   ├── run_worker.sh              # Worker process startup
│   └── generate_openapi_client.sh # Client SDK generation
├── pyproject.toml                 # Project configuration
├── .env.example                   # Environment variables template
└── README.md                      # Project documentation
```

## Module Responsibilities

### Core Layer (`app/core/`)
- **config.py**: Centralized configuration management using Pydantic settings
- **security.py**: Security utilities including data masking and validation
- **logging.py**: Structured logging with sensitive data filtering
- **exceptions.py**: Custom exception hierarchy and error mapping
- **constants.py**: System-wide constants and enumerations

### API Layer (`app/api/`)
- **deps.py**: FastAPI dependency injection setup for services and repositories
- **routers/**: FastAPI router modules organized by functional domain
  - Each router handles specific endpoint groups with proper error handling
  - Follows RESTful conventions where applicable

### Schemas Layer (`app/schemas/`)
- **Pydantic models** for request/response validation
- **Data serialization/deserialization** for API contracts
- **Common models** for shared patterns like pagination and responses

### Domain Layer (`app/domain/`)
- **models/**: Rich domain entities with business logic
- **builders/**: Complex object construction (e.g., XML generation)
- **validators/**: Business rule validation
- **mappers/**: Data transformation between layers
- **strategies/**: Strategy pattern for different authentication methods

### Services Layer (`app/services/`)
- **Orchestration** of domain operations
- **Business workflows** spanning multiple domain objects
- **Transaction management** and consistency
- **External service coordination**

### Infrastructure Layer (`app/infrastructure/`)
- **http/**: HTTP client implementations with retry logic
- **crypto/**: Cryptographic operations and certificate handling
- **persistence/**: Database models, repositories, and configuration
- **adapters/**: External system integrations (ERP, storage)

### Workers Layer (`app/workers/`)
- **Background processing** for long-running operations
- **Polling mechanisms** for status updates
- **Retry logic** for failed operations
- **Decoupled processing** from request-response cycle

### Utils Layer (`app/utils/`)
- **XML processing** utilities for FA(3) format handling
- **Hash and checksum** utilities for data integrity
- **Date/time** utilities for timezone handling and formatting

## Data Flow Patterns

### Invoice Submission Flow
1. **API Layer** receives invoice request
2. **Service Layer** orchestrates the submission process
3. **Domain Layer** validates and builds the invoice
4. **Infrastructure Layer** handles HTTP communication and storage
5. **Workers Layer** monitors status and handles retries

### Authentication Flow
1. **API Layer** handles auth endpoints
2. **Service Layer** manages auth lifecycle
3. **Domain Layer** implements auth strategies
4. **Infrastructure Layer** handles cryptographic operations

## Testing Strategy

### Unit Tests (`app/tests/unit/`)
- Test individual components in isolation
- Mock external dependencies
- Focus on business logic validation

### Integration Tests (`app/tests/integration/`)
- Test component interactions
- Use real database and external services (when possible)
- Validate end-to-end workflows

### Fixtures (`app/tests/fixtures/`)
- Sample data for consistent testing
- Mock responses for external services
- Reference XML and JSON formats

## Configuration Management

### Environment Variables
- All sensitive data loaded from environment
- Separate configurations for development, testing, production
- Validation of required variables at startup

### Database Configuration
- SQLAlchemy ORM with async support
- Connection pooling and timeout configuration
- Migration management through Alembic

## Security Considerations

### Data Protection
- Sensitive data masking in logs
- Encryption of stored credentials
- Certificate-based authentication support

### Input Validation
- Pydantic models for API validation
- Domain-level business rule validation
- SQL injection prevention through ORM

## Deployment Considerations

### Containerization
- Multi-stage Docker builds
- Environment-specific configurations
- Health checks and monitoring

### Background Processing
- Separate worker processes
- Queue management for retry logic
- Graceful shutdown handling

## Development Workflow

### Local Development
- Hot reload support through uvicorn
- Database migrations for schema changes
- Test fixtures for consistent development data

### Code Quality
- Type hints throughout the codebase
- Comprehensive test coverage
- Documentation for all public interfaces

This structure provides a solid foundation for building a maintainable, scalable KSeF integration service while following best practices for FastAPI applications and clean architecture principles.
