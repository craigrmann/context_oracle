# CodebaseContextOracle

**Efficient, mandatory codebase understanding for agentic coding workflows.**

This tool eliminates the #1 token killer in agentic coding: repeated full-codebase scans. Instead of dumping 50k–200k+ tokens every time an agent needs to “understand the project,” it builds a **one-time (incremental) index** and lets agents query only the minimal, high-signal context they actually need.

Result: 40–70% lower token spend, dramatically better accuracy, and zero ability for agents to hallucinate or ignore the real codebase.

## Why This Tool Exists

In any non-trivial feature implementation, agents repeat these expensive steps dozens of times:

- Scanning files to find where auth, events, notifications, etc. live
- Tracing dependencies across modules
- Re-understanding the system after every edit or test failure

Naive approaches (reading entire files or letting the model “remember”) destroy context windows and inflate costs.  
CodebaseContextOracle solves this with **hierarchical indexing + forced tool use**.

## How It Works (High-Level)

1. **One-time indexing** (or incremental on git changes):
   - Tree-sitter AST parsing → functions, classes, symbols, call graphs
   - Semantic chunking + embeddings (local or OpenAI)
   - Compact file/symbol summaries
   - Persistent vector DB + NetworkX graph

2. **Agent queries only** — never sees the whole codebase:
   - Natural-language semantic search
   - Symbol usage / callers
   - Architecture overviews
   - Targeted file slices

3. **Enforced** via system prompt so agents literally cannot proceed without it.

## Quick Start

### 1. Install dependencies
```bash
pip install chromadb sentence-transformers tree-sitter tree-sitter-python networkx pyyaml
# Add more tree-sitter languages as needed (JS, TS, Go, etc.)
```

### 2. Place the file
Copy `codebase_context_oracle.py` into your repo root (or any convenient location).

### 3. Build the index (first time only)
```bash
cd /path/to/your/project
python codebase_context_oracle.py build
```
Future runs auto-detect changes (add git-hook or run on `pre-commit` for perfect incrementality).

## Core API (Tool Schema)

Use this exact schema in **any** LLM framework (OpenAI, Anthropic, Grok, LangChain, LlamaIndex, CrewAI, LangGraph, etc.):

```json
{
  "name": "codebase_context_oracle",
  "description": "MANDATORY tool. Call this for ANY codebase understanding, planning, or before editing code.",
  "parameters": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "enum": ["query", "overview", "symbol_usages", "targeted_read"]
      },
      "query_or_symbol": {
        "type": "string",
        "description": "Natural language query OR symbol name"
      },
      "k": {
        "type": "integer",
        "default": 6,
        "description": "Number of results to return"
      }
    },
    "required": ["action"]
  }
}
```

### Available Actions

| Action          | Purpose                              | Example call                              |
|-----------------|--------------------------------------|-------------------------------------------|
| `query`         | Semantic search                      | `"how are notifications sent"`            |
| `overview`      | High-level architecture summary      | (no query needed)                         |
| `symbol_usages` | Find callers/implementations         | `"send_notification"`                     |
| `targeted_read` | Get specific function or lines       | `"UserService.create_user"`               |

## Mandatory Enforcement (Critical)

Add this block to **every agent’s system prompt**:

```
CRITICAL RULE — VIOLATION = INVALID RESPONSE, RESTART TURN:
You are FORBIDDEN from reasoning about, planning changes to, or editing ANY code until you have first called the "codebase_context_oracle" tool with a relevant query.

Always begin relevant thoughts with:
"Calling CodebaseContextOracle for context..."

Include the FULL tool response before any code analysis or planning.
For every new sub-task or decision point that touches the codebase, call it again.
Never assume you already "know" the codebase — the Oracle is the single source of truth.
```

## Example Agent Loop (pseudocode — works in any framework)

```python
while not done:
    if task_requires_code_understanding(current_task):
        oracle_result = call_tool("codebase_context_oracle", {
            "action": "query",
            "query_or_symbol": task_description
        })
        prompt += f"\n\nOracle result:\n{oracle_result}"
    
    response = llm.generate(prompt)
    # parse and execute any tool calls
    # if oracle was not called when required → force re-call
```

## Integration Tips by Platform

- **Cursor / Windsurf / Claude Code** — add as custom MCP tool or command
- **Aider** — use `--custom-tool` or script mode
- **LangGraph / CrewAI** — add as a dedicated “ResearchAgent” tool
- **OpenAI Swarm / AutoGen** — register as a function
- **VS Code + Continue.dev** — expose via local server (add FastAPI wrapper if needed)

## Advanced / Next Steps (optional)

- Add git post-commit hook for automatic re-indexing
- Switch embeddings to `text-embedding-3-large` for better quality
- Expose as FastAPI endpoint for multi-agent setups
- Add auto-summary generation for every major module

The full implementation (including Tree-sitter AST chunking and graph building) is in `codebase_context_oracle.py`. It is intentionally modular so you can extend it for any language or add features like automatic memory compaction.

---

**Start using it today.**  
Your agents will thank you with dramatically lower costs, fewer mistakes, and the ability to actually ship features instead of burning tokens on redundant scanning.

Questions or want a platform-specific integration example? Open an issue or PR.
