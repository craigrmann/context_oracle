import os
import hashlib
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer
import networkx as nx
import yaml
from tree_sitter import Language, Parser  # install language bindings as needed

class CodebaseContextOracle:
    def __init__(self, root_dir: str, embedding_model: str = "all-MiniLM-L6-v2"):
        self.root = Path(root_dir)
        self.chroma = chromadb.PersistentClient(path=str(self.root / ".oracle_index"))
        self.collection = self.chroma.get_or_create_collection("code_chunks")
        self.embedder = SentenceTransformer(embedding_model)
        self.graph = nx.DiGraph()  # symbol -> callers
        self.summaries = {}  # file -> summary
        self.parser = {}  # language -> parser (populate with tree-sitter languages)
        self._build_or_load_index()

    def _build_or_load_index(self):
        # Incremental: check .oracle_hash or mtime
        # For brevity: full build on first run, you can add git diff logic
        for file in self.root.rglob("*"):
            if file.suffix in {'.py', '.js', '.ts', '.go', ...}:  # extend
                self._index_file(file)

    def _index_file(self, file_path: Path):
        content = file_path.read_text()
        # Parse with Tree-sitter for chunks (functions/classes)
        # Simplified: chunk by functions or fixed size with overlap
        chunks = self._ast_chunk(content, file_path.suffix)  # implement with tree-sitter
        embeddings = self.embedder.encode([c['text'] for c in chunks])
        for i, chunk in enumerate(chunks):
            self.collection.add(
                documents=[chunk['text']],
                metadatas=[{"file": str(file_path), "symbol": chunk.get('symbol'), **chunk}],
                ids=[f"{file_path}:{i}"]
            )
        # Build graph, summaries, etc.
        # ... (add summary generation via LLM call once if you want)

    def query(self, natural_language_query: str, k: int = 8, depth: str = "snippet") -> dict:
        """Agent MUST call this for any understanding task."""
        results = self.collection.query(
            query_texts=[natural_language_query],
            n_results=k,
            include=["documents", "metadatas"]
        )
        # Enrich with graph if depth > snippet
        return {
            "query": natural_language_query,
            "results": results['documents'][0],
            "files": list(set(m['file'] for m in results['metadatas'][0])),
            "summary": "High-signal context retrieved. Use this to reason."  # add LLM summary if desired
        }

    def get_architecture_overview(self) -> str:
        return "Repo overview: [pre-generated or LLM-summarized from summaries]"

    def get_symbol_usages(self, symbol: str) -> dict:
        # Graph query
        return {"callers": list(self.graph.predecessors(symbol))}

    # Add: get_file_summary, targeted_read(lines), etc.

# CLI wrapper
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["query", "overview"])
    parser.add_argument("arg")
    # ... call oracle.query etc.
