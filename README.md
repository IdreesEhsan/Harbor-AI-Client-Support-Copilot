# Harbor — AI Client Support Copilot

Harbor is an end-to-end AI client support system built as a DevOrbis capstone project. It combines a React customer/staff interface, FastAPI backend, JWT authentication, Supabase PostgreSQL + pgvector, MiniLM embeddings, Groq-powered RAG, LangGraph orchestration, persistent conversation memory, security guardrails, human-in-the-loop ticket approval, Monday.com integration, n8n Cloud automation, Gmail notifications, Supabase audit logging, and Snowflake reporting.

> **Project goal:** give customers grounded support answers with citations, preserve conversational context, escalate safely to humans when needed, and connect approved support tickets to real business systems without manual Postman steps.

---

## 1. Problem Statement

Traditional support workflows often split customer conversations, internal approvals, ticket systems, notifications, and analytics across disconnected tools.

Harbor connects the complete support workflow:

1. A customer authenticates and asks a support question.
2. Harbor retrieves relevant support knowledge using RAG.
3. The agent answers only when there is enough grounded evidence.
4. Conversation memory preserves useful context across turns.
5. Guardrails handle unsafe, sensitive, or escalation-worthy inputs.
6. When human help is required, Harbor creates an internal support ticket.
7. Authorized staff review the ticket and approve or reject it.
8. Approved tickets are executed safely and idempotently into Monday.com.
9. Harbor sends the completed event to n8n Cloud.
10. n8n handles notification, audit, and analytics through Gmail, Supabase, and Snowflake.

---

## 2. Core Features

### Customer Support
- React customer chat interface
- JWT authentication
- Grounded knowledge-base answers
- Source citations
- Contextual follow-up questions
- Persistent conversation memory
- Human escalation
- Customer-visible support ticket state

### AI / RAG
- Groq LLM integration
- `sentence-transformers/all-MiniLM-L6-v2`
- 384-dimensional embeddings
- Supabase PostgreSQL + pgvector
- Similarity retrieval
- Source/chunk metadata
- Grounded no-answer behavior

### LangGraph Agent
- Structured routing
- Knowledge-base answer path
- Conversation-memory answer path
- Clarification path
- Escalation path
- Blocked-input path
- Step/tool execution limits

### Guardrails & Security
- Prompt-injection detection
- PII/credential redaction
- Output guardrails
- Safe persistence
- Tool authorization
- Human approval before external writes
- JWT authentication
- RBAC
- API rate limiting
- LLM input limits
- Environment-based secrets

### Ticket Workflow
- Internal support tickets
- Severity classification
- `pending_approval` workflow
- Staff approval/rejection
- Staff-only execution
- Atomic execution claims
- Stale execution-lease recovery
- Deterministic idempotency

### Integrations
- Monday.com
- n8n Cloud
- Gmail
- Supabase audit logging
- Snowflake reporting

---

## 3. System Architecture

```text
Customer / Staff
      |
      v
React Frontend
      |
      v
FastAPI REST API
JWT Authentication + RBAC
      |
      v
LangGraph Support Agent
  |          |          |
  v          v          v
 RAG       Memory    Guardrails
  |          |          |
  v          v          v
Groq     Supabase      Tools
  |
  v
MiniLM Embeddings
      |
      v
Supabase pgvector
Knowledge Base
      |
      v
Escalation Decision
      |
      v
Internal Support Ticket
      |
      v
Human Approval / Rejection
      |
      v
Safe + Idempotent Execution
      |
      v
Monday.com
      |
      v
n8n Cloud
   |          |           |
   v          v           v
 Gmail   Supabase Audit  Snowflake
4. Technology Stack
Layer	Technology
Frontend	React, Vite, React Router, Axios
Backend	FastAPI, Python, Pydantic
Authentication	JWT, bcrypt
Database	Supabase PostgreSQL
Vector Search	pgvector
Embeddings	Sentence Transformers / MiniLM
LLM	Groq
Agent	LangGraph
Ticketing	Monday.com
Automation	n8n Cloud
Notification	Gmail
Audit	Supabase
Analytics	Snowflake
Containerization	Docker
Deployment	Railway
Testing	pytest + E2E testing
5. Repository Structure
Harbor/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── dependencies/
│   │   ├── guardrails/
│   │   ├── integrations/
│   │   ├── rag/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── tickets/
│   │   └── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .dockerignore
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── context/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── .dockerignore
│   └── .env.example
│
├── .gitignore
└── README.md
6. Local Setup
Backend
cd backend
python -m venv venv

Windows:

venv\\Scripts\\activate

Install dependencies:

pip install -r requirements.txt

Run:

uvicorn app.main:app --reload

Useful URLs:

Backend:   http://localhost:8000
Swagger:   http://localhost:8000/docs
Health:    http://localhost:8000/api/v1/health
Readiness: http://localhost:8000/api/v1/ready
Frontend
cd frontend
npm install
npm run dev

Frontend:

http://localhost:5173
7. Environment Variables
Backend
APP_NAME=Harbor API
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO
API_PREFIX=/api/v1

CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

GENERAL_RATE_LIMIT=120/minute
AGENT_RATE_LIMIT=20/minute
RAG_RATE_LIMIT=30/minute
AUTH_RATE_LIMIT=10/minute

LLM_MAX_INPUT_CHARACTERS=4000
LLM_REQUESTS_PER_USER_PER_MINUTE=20

SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=

JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile

MEMORY_BUFFER_SIZE=8
MEMORY_SUMMARY_THRESHOLD=12

MONDAY_API_TOKEN=
MONDAY_API_URL=https://api.monday.com/v2
MONDAY_BOARD_ID=
MONDAY_GROUP_ID=
MONDAY_HARBOR_TICKET_ID_COLUMN_ID=
MONDAY_STATUS_COLUMN_ID=
MONDAY_IDEMPOTENCY_KEY_COLUMN_ID=
MONDAY_DESCRIPTION_COLUMN_ID=
MONDAY_SEVERITY_COLUMN_ID=

N8N_TICKET_WEBHOOK_URL=
N8N_WEBHOOK_TIMEOUT_SECONDS=10
Frontend
VITE_API_BASE_URL=http://localhost:8000/api/v1

Never commit real .env files or secret values.

8. Authentication & Roles

Harbor supports:

customer
support_agent
admin

Public registration creates only customer accounts.

The backend RBAC layer is the authoritative security boundary. Frontend route guards are only UX controls.

9. RAG Design
Support Documents
      |
      v
Chunking
      |
      v
MiniLM Embeddings
      |
      v
Supabase pgvector
      |
      v
Similarity Retrieval
      |
      v
Grounded Prompt
      |
      v
Groq
      |
      v
Answer + Citations

Embedding model:

sentence-transformers/all-MiniLM-L6-v2

Embedding dimension:

384
10. LangGraph Workflow

Actions:

answer
clarify
escalate

Answer sources:

knowledge_base
conversation_memory
Input
  |
  v
Input Guardrail
  |
  +---- blocked ------> Safe Blocked Response
  |
  +---- escalate -----> Escalation
  |
  v
Decision Node
  |
  +---- answer + KB ----------> RAG Answer
  |
  +---- answer + memory ------> Memory Answer
  |
  +---- clarify -------------> Clarification
  |
  +---- escalate ------------> Human Escalation
11. Human-in-the-Loop Ticket Lifecycle
Customer conversation
      |
      v
Agent decides: escalate
      |
      v
Internal Harbor ticket
status = pending_approval
approval_status = pending
      |
      +---- Reject ----> rejected
      |
      v
Approve
status = approved
approval_status = approved
      |
      v
Atomic execution claim
status = executing
      |
      v
Monday.com lookup/create
      |
      v
Harbor finalization
status = open

External execution requires persisted human approval.

12. Idempotency & Execution Safety

Harbor uses:

deterministic ticket idempotency;
Monday.com lookup-before-create;
atomic execution claims;
execution claim ownership;
stale lease detection;
stale lease recovery;
claim-owned finalization.

If a Monday item already exists for the idempotency key, Harbor reuses it rather than creating a duplicate.

13. n8n Cloud Automation

After Harbor safely finalizes the Monday.com operation, it sends an event to n8n Cloud.

Example:

{
  "event_type": "ticket.executed",
  "ticket_id": "UUID",
  "monday_item_id": "123456789",
  "title": "Customer support escalation",
  "description": "Customer request details",
  "severity": "medium",
  "status": "open",
  "source": "harbor",
  "idempotency_key": "harbor-ticket-..."
}

Workflow:

Webhook
   |
   v
Validate / Normalize
   |
   v
Duplicate Check
   |
   v
Priority?
  / \\
 /   \\
High  Low/Medium
 |       |
 v       v
Priority Normal
Email    Email
   \\     /
    \\   /
     v v
Supabase Audit
      |
      v
Snowflake
14. API Overview
GET  /api/v1/health
GET  /api/v1/ready

POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/token
GET  /api/v1/auth/me

POST /api/v1/rag/ask
POST /api/v1/agent/chat

GET  /api/v1/tickets
GET  /api/v1/tickets/{ticket_id}
POST /api/v1/tickets/{ticket_id}/approval
POST /api/v1/tickets/{ticket_id}/execute

Protected endpoints require:

Authorization: Bearer <JWT>
15. Docker
Backend
cd backend
docker build -t harbor-backend .
docker run --env-file .env -p 8000:8000 harbor-backend
Frontend
cd frontend

docker build \\
  --build-arg VITE_API_BASE_URL=http://localhost:8000/api/v1 \\
  -t harbor-frontend .

docker run -p 8080:8080 harbor-frontend
16. Railway Deployment

Harbor is deployed as two Railway services:

Railway Project: Harbor

├── harbor-backend
│   └── Root Directory: /backend
│
└── harbor-frontend
    └── Root Directory: /frontend
Backend variables
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO

CORS_ORIGINS=https://<frontend-domain>

SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=

JWT_SECRET_KEY=
GROQ_API_KEY=

MONDAY_API_TOKEN=
MONDAY_BOARD_ID=
MONDAY_GROUP_ID=

N8N_TICKET_WEBHOOK_URL=

Healthcheck:

/api/v1/health
Frontend
VITE_API_BASE_URL=https://<backend-domain>/api/v1
17. Testing Strategy
Golden Path
Customer login.
Ask support question.
Grounded answer appears.
Citation is visible.
Ask contextual follow-up.
Conversation memory works.
Request human support.
LangGraph escalates.
Internal ticket is created.
Staff logs in.
Staff sees ticket.
Staff approves ticket.
Staff executes ticket.
Monday.com item is created/reused.
Harbor finalizes ticket.
Harbor posts to n8n.
Gmail notification is sent.
Supabase audit row is created.
Snowflake row/report is created.
Security / Failure Testing

Verify:

unauthorized access fails;
customers cannot perform staff actions;
rejected tickets cannot execute;
unapproved tickets cannot execute;
executed tickets do not duplicate;
active leases block competing workers;
stale leases recover safely;
prompt injection is blocked;
PII/credential sanitization works;
RAG no-answer remains grounded;
duplicate n8n events do not resend effects;
output guardrails block protected/internal content.
18. Demo Flow

Target: 5–8 minutes

1. Customer login
2. Support/refund question
3. Grounded answer + citation
4. Contextual follow-up
5. Memory example
6. Request human support
7. Show ticket creation
8. Staff login
9. Approve ticket
10. Execute ticket
11. Monday.com item
12. Gmail notification
13. Supabase audit
14. Snowflake report
19. Current Status
Implemented / Connected
FastAPI backend
Supabase PostgreSQL
pgvector
MiniLM embeddings
Groq grounded RAG
citations
LangGraph
conversation memory
guardrails
JWT / RBAC
internal tickets
human approval
execution claims
stale lease recovery
Monday.com integration
React customer chat
React staff console
escalation ticket feedback
n8n integration code
health/readiness endpoints
production configuration
Docker configuration
Railway deployment preparation
Final Verification Required
verify both n8n branches;
deploy backend/frontend on Railway;
configure production CORS;
run golden-path E2E tests;
run security/failure tests;
fix final issues;
capture screenshots;
complete demo.
20. Known Limitations

Currently out of scope:

voice agents;
QuickBooks;
elaborate dashboards;
password reset;
WebSockets;
advanced admin management;
extra AI agents;
enterprise distributed rate limiting.
21. Future Improvements
Vapi/Retell voice support
Redis-backed distributed rate limiting
durable event outbox/retry
richer staff dashboard
real-time ticket status
observability dashboard
automated prompt regression
deeper Snowflake analytics
QuickBooks integration
account recovery/password reset
22. Project Principle

Retrieve → Decide → Escalate → Approve → Execute → Automate → Audit

Harbor is designed as a production-shaped AI support workflow rather than a collection of disconnected AI demos.