"""
FastAPI app entry point.
Wires the WebSocket chat route, the REST ingest route, and the sessions
route; manages both the Postgres connection pool and the LangGraph
Postgres checkpointer ("memory saver") lifecycles via FastAPI's lifespan.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.db import init_db, close_db
from server.memory import init_memory, close_memory
from server.websocket_routes import router as websocket_router
from server.ingest_routes import router as ingest_router
from server.session_routes import router as session_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_memory()
    yield
    await close_memory()
    await close_db()


app = FastAPI(lifespan=lifespan)

# React dev server (Vite) needs CORS to call the REST endpoints.
# WebSocket connections are unaffected by CORS but this keeps /ingest and
# /sessions usable from the browser regardless of which Vite port is active.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5175"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(websocket_router)
app.include_router(ingest_router)
app.include_router(session_router)
