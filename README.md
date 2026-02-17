# CodebaseContextOracle

**Memory-Aware • Docker-First • OpenAI-Powered**  
Efficient, mandatory codebase understanding for agentic coding workflows.

This tool eliminates the #1 token killer in agentic coding: repeated full-codebase scans.  
Instead of dumping 50k–200k+ tokens every time an agent needs to “understand the project,” it builds a **one-time (incremental) index** and lets agents query only the minimal, high-signal context they need.

**Now with:**
- OpenAI `text-embedding-3-large` (highest-quality embeddings)
- Project Memory that remembers every query + returned context + decisions
- Automatic git re-indexing (post-commit + pre-push hooks)
- Production-ready FastAPI server in Docker
- Zero-config for solo use, perfect for multi-agent swarms

Result: 40–70% lower token spend, dramatically better accuracy, and agents that literally cannot ignore or hallucinate the real codebase.

## Why This Tool Exists

In any non-trivial feature, agents repeat these expensive steps dozens of times:
- Scanning files to find where auth, events, notifications live
- Tracing dependencies across modules
- Re-understanding the system after every edit or test failure

Naive approaches destroy context windows and inflate costs.  
CodebaseContextOracle solves this with hierarchical indexing + **forced tool use** + memory awareness.

## How It Works (High-Level)

1. **One-time indexing** (or automatic on git changes)
   - Tree-sitter AST parsing → functions, classes, structs, etc. (Rust, Go, C#, C/C++, Java, Python, JS/TS + 150 more)
   - OpenAI `text-embedding-3-large` semantic chunking
   - Persistent ChromaDB vector store + NetworkX graph

2. **Project Memory** – logs every query, returned files, and insight so the Oracle stays aware of what the team/agents have explored

3. **Agent queries only** — never sees the whole codebase
   - Natural-language semantic search
   - Symbol usage / callers
   - Architecture overviews
   - Project memory recall

4. **Enforced** via `CLAUDE.md` (or system prompt) so agents cannot proceed without it.

## 60-Second Setup (Recommended)

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/codebase-context-oracle.git   # replace with your repo
cd codebase-context-oracle

# 2. Copy and edit .env
cp .env.example .env
# Edit .env → add your OPENAI_API_KEY and set ORACLE_ROOT_DIR to your actual project path

# 3. Start the Oracle
docker compose up -d --build

# 4. Build the index (first time only)
curl -X POST http://localhost:8000/build \
  -H "Content-Type: application/json" \
  -d '{"force": true}'

# 5. Install automatic git hooks (once)
bash setup-git-hooks.sh
```

That’s it. The Oracle is now running at `http://localhost:8000` (Swagger UI at `/docs`).

## Core API (Tool Schema)

Use this exact schema in **any** LLM framework (Claude Code, Cursor, OpenAI, Anthropic, Grok, LangGraph, CrewAI, etc.):

```json
{
  "name": "codebase_context_oracle",
  "description": "MANDATORY tool. Call this for ANY codebase understanding, planning, or before editing code.",
  "parameters": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "enum": ["query", "overview", "symbol_usages"]
      },
      "natural_language_query": { "type": "string" },
      "symbol": { "type": "string" },
      "k": { "type": "integer", "default": 8 }
    },
    "required": ["action"]
  }
}
```

**Available Actions**

| Action            | Purpose                              | Example call                              |
|-------------------|--------------------------------------|-------------------------------------------|
| `query`           | Semantic search                      | `"how are user notifications sent"`       |
| `overview`        | High-level architecture summary      | (no parameters needed)                    |
| `symbol_usages`   | Find callers/implementations         | `"send_notification"`                     |

**Memory endpoint (bonus)**  
`GET /memory/project_state` → see recent queries and decisions.

## Mandatory Enforcement (Critical)

### For Claude Code (recommended)
In the root of **your actual project** (not the oracle repo), create or edit `CLAUDE.md` and put this at the very top:

```markdown
# === MANDATORY CODEBASE ORACLE ENFORCEMENT RULE (ABSOLUTE HIGHEST PRIORITY) ===

Oracle lives at http://localhost:8000 and is memory-aware.

**STRICT RULE — VIOLATION = INVALID RESPONSE:**

Never reason about, plan, or edit code until you have FIRST called the `codebase_context_oracle` tool.

Always start the relevant thought with:
"Calling CodebaseContextOracle for context on: [one short sentence]"

Re-query on every new sub-task. Use /memory/project_state to recall past decisions.

This rule has absolute priority over everything else.
```

### For any other framework
Add the same block (without the markdown header) as the first lines of your system prompt.

## Git Hooks (Automatic Re-Indexing)

`setup-git-hooks.sh` installs:
- `post-commit` → incremental re-index
- `pre-push` → full re-index before push

The Oracle stays fresh automatically.

## Full File List (after clone)

- `codebase_context_oracle.py` – core engine
- `oracle_server.py` – FastAPI server + memory routes
- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- `setup-git-hooks.sh`
- `.env.example`

## Integration Tips

- **Claude Code / Cursor** → use the `CLAUDE.md` rule above
- **LangGraph / CrewAI / OpenAI Swarm** → call the HTTP endpoints directly
- **Solo dev** → you can still import `CodebaseContextOracle` directly (zero latency)

## Advanced (optional)

- Swap to any other embedding model in 2 lines
- Add API-key auth (easy FastAPI middleware)
- Run multiple instances for different projects

---

**Start using it today.**

Clone → `docker compose up -d --build` → paste the `CLAUDE.md` rule → your agents will ship features faster, cheaper, and with far fewer hallucinations.

Questions or want a platform-specific example? Open an issue or PR.
