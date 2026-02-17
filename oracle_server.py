#!/usr/bin/env python3
"""
CodebaseContextOracle FastAPI Server
Shared microservice for multi-agent workflows.
Works perfectly with OpenAI, Anthropic, xAI/Grok, LangChain, LlamaIndex, etc.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from codebase_context_oracle import CodebaseContextOracle  # ← your existing file

# ================== LIFESPAN (startup / shutdown) ==================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global oracle
    root = os.getenv("ORACLE_ROOT_DIR", ".")
    print(f"🚀 Starting Oracle server with root: {root}")
    oracle = CodebaseContextOracle(root)
    
    # Quick health check on index
    total = oracle.collection.count()
    if total == 0:
        print("⚠️  Index is empty! Run POST /build to index your codebase.")
    else:
        print(f"✅ Index ready — {total} chunks loaded")
    
    yield
    print("🛑 Oracle server shutting down...")

app = FastAPI(
    title="CodebaseContextOracle",
    description="Mandatory high-efficiency codebase understanding for agentic workflows",
    lifespan=lifespan,
    version="1.0.0"
)

# CORS — safe for local multi-agent and dev tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global oracle instance (shared across all requests)
oracle: CodebaseContextOracle = None

# ================== Pydantic Models ==================
class QueryRequest(BaseModel):
    natural_language_query: str
    k: int = 8

class BuildRequest(BaseModel):
    force: bool = False

class SymbolRequest(BaseModel):
    symbol: str

# ================== ENDPOINTS ==================
@app.get("/health")
async def health():
    return {"status": "healthy", "total_chunks": oracle.collection.count() if oracle else 0}

@app.get("/overview")
async def overview():
    return oracle.overview()

@app.post("/query")
async def query(request: QueryRequest):
    if oracle.collection.count() == 0:
        raise HTTPException(status_code=428, detail="Index is empty. Call /build first.")
    if request.k > 20:
        request.k = 20  # safety limit
    return oracle.query(request.natural_language_query, request.k)

@app.post("/symbol/usages")
async def symbol_usages(request: SymbolRequest):
    return oracle.symbol_usages(request.symbol)

@app.post("/build")
async def build(request: BuildRequest, background_tasks: BackgroundTasks):
    if oracle.collection.count() > 0 and not request.force:
        return {"status": "already_indexed", "message": "Use ?force=true to rebuild"}
    
    def do_build():
        oracle.build(force=request.force)
    
    background_tasks.add_task(do_build)
    return {
        "status": "started",
        "message": "Background indexing started. Check /health or /overview later."
    }

# ================== RUN ==================
if __name__ == "__main__":
    uvicorn.run(
        "oracle_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,          # auto-reload on code changes (dev only)
        log_level="info"
    )
