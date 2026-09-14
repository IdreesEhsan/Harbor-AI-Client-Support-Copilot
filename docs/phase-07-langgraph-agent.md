# Phase 7 — LangGraph Agent Orchestration

## Objective

Add controlled agent orchestration to Harbor using LangGraph.

## Workflow

User Request
→ Decision Node
→ Conditional Routing

Routes:

- answer
- clarify
- escalate

## Components

### Agent State

`HarborAgentState` stores request and workflow data during graph execution.

### Structured Router

Groq classifies requests into:

- answer
- clarify
- escalate

The result is validated using Pydantic.

### RAG Tool

The `search_knowledge_base` tool wraps Harbor's Phase 6 RAG service.

### Nodes

- decision node
- answer node
- clarification node
- escalation node

### LangGraph

The graph uses:

- StateGraph
- START
- END
- nodes
- normal edges
- conditional edges

### Security

The public agent API is protected using Harbor's existing JWT
authentication dependency.

Internal graph state is not returned directly to the frontend.

### Current Limitation

Conversation history and persistent memory are not yet loaded into the
graph. These are implemented in Phase 8.

Human escalations are currently represented in graph state only.
Persistent escalation workflows and Monday.com automation are added in
later phases.