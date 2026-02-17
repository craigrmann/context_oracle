#!/usr/bin/env python3
"""
CodebaseContextOracle FastAPI Server - Memory-Aware
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from codebase_context_oracle import CodebaseContextOracle

@asynccontextmanager
async def lifespan(app: FastAPI):
    global oracle
    root = os.getenv("ORACLE_ROOT_DIR", ".")
    print(f"🚀 Starting Oracle at root: {root}")
    oracle = CodebaseContextOracle(root)
    total = oracle.collection.count()
    print(f"✅ Index ready — {total} chunks | Memory ready")
    yield
    print("🛑 Oracle shutting down")

app = FastAPI(title="CodebaseContextOracle", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

oracle: CodebaseContextOracle = None

class QueryRequest(BaseModel):
    natural_language_query: str
    k: int = 8

class BuildRequest(BaseModel):
    force: bool = False

class SymbolRequest(BaseModel):
    symbol: str

@app.get("/health")
async def health():
    return {"status": "healthy", "chunks": oracle.collection.count() if oracle else 0}

@app.get("/overview")
async def overview():
    return oracle.overview()

@app.post("/query")
async def query(request: QueryRequest):
    if oracle.collection.count() == 0:
        raise HTTPException(428, "Index empty — call /build first")
    return oracle.query(request.natural_language_query, request.k)

@app.post("/symbol/usages")
async def symbol_usages(request: SymbolRequest):
    return oracle.symbol_usages(request.symbol)

@app.post("/build")
async def build(request: BuildRequest, background_tasks: BackgroundTasks):
    def do_build():
        oracle.build(force=request.force)
    background_tasks.add_task(do_build)
    return {"status": "started", "message": "Indexing in background"}

@app.get("/memory/project_state")
async def project_state(k: int = Query(10, ge=1, le=50)):
    return oracle.get_project_memory(k)

if __name__ == "__main__":
    uvicorn.run("oracle_server:app", host="0.0.0.0", port=8000, reload=True)
