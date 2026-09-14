# Harbor — Phase 1: Project Setup & FastAPI Foundation

## 1. Objective

The objective of Phase 1 was to establish a clean and professional
foundation for the Harbor AI Client Support Copilot.

This phase focused on:

- Project organization
- Python environment setup
- FastAPI backend initialization
- Environment-based configuration
- API routing
- Health checks
- API documentation
- Git version control
- Secret protection

---

## 2. Technologies Used

- Python
- FastAPI
- Uvicorn
- Pydantic
- Pydantic Settings
- python-dotenv
- Git
- GitHub-ready repository structure
- Visual Studio Code

---

## 3. Project Structure

The initial Harbor project structure is:

Harbor/
├── backend/
├── frontend/
├── database/
├── knowledge_base/
├── scripts/
├── n8n/
├── docs/
├── .gitignore
└── README.md

Each directory has a specific responsibility.

### backend/

Contains the FastAPI backend and will later contain:

- Authentication
- JWT
- RAG
- LangChain
- LangGraph
- Memory
- Guardrails
- Business integrations

### frontend/

Reserved for the React frontend.

### database/

Contains version-controlled PostgreSQL database scripts.

### knowledge_base/

Stores development knowledge-base documents used for Harbor RAG.

### scripts/

Contains utility scripts such as document ingestion and evaluation
scripts.

### n8n/

Contains Harbor workflow automation documentation and exported
workflows.

### docs/

Contains technical documentation for each project phase.

---

## 4. Backend Structure

The Phase 1 backend structure is:

backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── health.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py
│   ├── __init__.py
│   └── main.py
├── .env
├── .env.example
├── requirements.txt
└── .venv/

---

## 5. Python Virtual Environment

A dedicated Python virtual environment was created:

python -m venv .venv

It is activated on Windows PowerShell using:

.venv\Scripts\Activate.ps1

The virtual environment isolates Harbor's Python dependencies from
other Python projects installed on the machine.

---

## 6. Backend Dependencies

The initial backend dependencies include:

- FastAPI
- Uvicorn
- Pydantic
- Pydantic Settings
- python-dotenv

Dependencies are stored in:

backend/requirements.txt

The requirements file allows the backend environment to be reproduced
using:

pip install -r requirements.txt

---

## 7. Environment Configuration

Harbor uses environment-based configuration.

The actual local configuration is stored in:

backend/.env

An example configuration is stored in:

backend/.env.example

Initial configuration includes:

APP_NAME=Harbor API
APP_ENV=development
API_PREFIX=/api/v1
DEBUG=true

The .env file is excluded from Git.

This becomes especially important in future phases when Harbor contains
credentials such as:

- Supabase credentials
- JWT secret
- LLM API keys
- n8n webhook secrets
- Monday.com credentials
- Snowflake credentials

Secrets must never be committed to the repository.

---

## 8. Centralized Configuration

Harbor uses Pydantic Settings to load application configuration.

The configuration module is located at:

backend/app/core/config.py

This allows the application to use configuration such as:

settings.app_name
settings.app_env
settings.api_prefix
settings.debug

instead of hardcoding environment-specific values throughout the
application.

---

## 9. FastAPI Application

The main FastAPI application is located at:

backend/app/main.py

It creates the Harbor API and registers application routers.

The application can be started using:

uvicorn app.main:app --reload

During local development, Harbor runs at:

http://127.0.0.1:8000

---

## 10. API Versioning

Harbor uses versioned API routes.

Current API prefix:

/api/v1

Future APIs will follow the same structure, for example:

/api/v1/auth/register
/api/v1/auth/login
/api/v1/conversations
/api/v1/chat
/api/v1/feedback

API versioning makes future API changes easier to manage.

---

## 11. Root Endpoint

Endpoint:

GET /

Purpose:

Confirms that the Harbor FastAPI application is running.

Example response:

{
    "message": "Harbor API is running",
    "environment": "development"
}

---

## 12. Health Endpoint

Endpoint:

GET /api/v1/health

Purpose:

Provides a lightweight application health check.

Example response:

{
    "status": "ok"
}

This endpoint can later be used by:

- Docker
- Railway
- Render
- Monitoring systems
- Load balancers

---

## 13. API Documentation

FastAPI automatically generates interactive API documentation.

Swagger UI:

http://127.0.0.1:8000/docs

ReDoc:

http://127.0.0.1:8000/redoc

Swagger will be used throughout Harbor development to manually test
backend endpoints.

---

## 14. Git Configuration

Git was initialized for Harbor.

The primary development branch is:

main

The .gitignore file excludes:

- .env files
- Python virtual environments
- Python cache files
- Node modules
- build output
- IDE configuration
- logs
- operating-system generated files

This reduces repository clutter and protects sensitive information.

---

## 15. Initial Git Commit

The Phase 1 implementation can be committed using:

git add .
git commit -m "feat: initialize Harbor FastAPI backend"

Each major Harbor phase will receive its own meaningful commits.

---

## 16. Phase 1 Architecture

Client / Browser
       |
       | HTTP
       v
    FastAPI
       |
       +-- GET /
       |
       +-- GET /api/v1/health
       |
       +-- Swagger /docs
       |
       +-- ReDoc /redoc

At this stage Harbor does not yet have a database, authentication,
LLM, RAG, LangGraph, or frontend.

Those components are intentionally introduced incrementally.

---

## 17. Security Decisions

The following security practices were established during Phase 1:

1. Secrets are stored using environment variables.
2. .env is excluded from Git.
3. .env.example contains only safe example values.
4. Application configuration is centralized.
5. API routes use versioning.
6. Dependencies are isolated using a virtual environment.

---

## 18. Phase 1 Completion Checklist

- [x] Harbor project structure created
- [x] Git repository initialized
- [x] main branch configured
- [x] .gitignore created
- [x] README created
- [x] Python virtual environment created
- [x] FastAPI installed
- [x] Uvicorn installed
- [x] Pydantic configuration created
- [x] Environment configuration added
- [x] Root endpoint implemented
- [x] Health endpoint implemented
- [x] API versioning established
- [x] Swagger documentation available
- [x] ReDoc documentation available
- [x] Secrets excluded from Git
- [x] Initial Git commit prepared

---

## 19. Next Phase

Phase 2 introduces Harbor's database foundation using:

- Supabase
- PostgreSQL
- pgvector
- users table
- conversations table
- messages table
- conversation summary storage
- FastAPI-to-Supabase connection
- readiness checks

After the database foundation is complete, Phase 3 will implement
authentication and authorization using password hashing and JWT.