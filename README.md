# Cortex

Cortex is a full-stack hybrid RAG application built with FastAPI, WebSockets, LangGraph, PostgreSQL, and a React + Vite frontend. It lets users upload documents, retrieve relevant content, and ask questions through a grounded, streaming AI workflow.

## What it does

- Uploads raw documents from the frontend
- Loads, chunks, embeds, and indexes content for hybrid retrieval
- Runs queries through a LangGraph pipeline with routing, retrieval, reranking, guardrails, and fallback generation
- Stores chat sessions and conversation turns in PostgreSQL
- Streams progress and responses back to the browser in real time
- Includes a session explorer UI for browsing saved chats and history

## Tech stack

- Backend: Python, FastAPI, LangGraph, asyncpg, PostgreSQL
- Retrieval: Chroma, Hugging Face Inference API, BM25, RRF fusion, reranking
- Frontend: React, Vite
- Optional: OpenRouter for summarization

## How the app works

1. Users upload files from the frontend.
2. The backend ingests, chunks, embeds, and indexes the documents for dense and sparse retrieval.
3. A WebSocket chat endpoint receives a query and runs it through the LangGraph workflow.
4. The workflow performs input checking, query classification, retrieval, reranking, grounding validation, and answer generation.
5. Generated responses are streamed back to the client and persisted as conversation turns in PostgreSQL.

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment

Set up the required variables in `backend/config.py` or your environment:

- `HUGGINGFACE_API_KEY`
- `DATABASE_URL`
- `OPENROUTER_API_KEY` (optional)

## Notes

- Docker is not currently configured in this repository.
- This project is focused on a practical hybrid RAG workflow with persistent session history and a clean frontend experience.
# Cortex
# Cortex
# Cortex
# Cortex-RagBot
