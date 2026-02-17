#!/usr/bin/env python3
"""
CodebaseContextOracle - Memory-Aware, OpenAI-powered, multi-language
"""
import os
import json
from pathlib import Path
from datetime import datetime
import chromadb
import networkx as nx
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from tree_sitter_language_pack import get_parser

class Embedder:
    def __init__(self):
        self.openai_client = None
        self.local_embedder = None
        self.model = None
        if os.getenv("OPENAI_API_KEY"):
            self.openai_client = OpenAI()
            self.model = "text-embedding-3-large"
            print("✅ Using OpenAI text-embedding-3-large (highest quality)")
        else:
            self.local_embedder = SentenceTransformer("all-MiniLM-L6-v2")
            print("⚠️  Using local embeddings (set OPENAI_API_KEY for best results)")

    def embed(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        if self.openai_client:
            resp = self.openai_client.embeddings.create(
                input=texts, model=self.model, dimensions=1024
            )
            return [e.embedding for e in resp.data]
        return self.local_embedder.encode(texts).tolist()

class ProjectMemory:
    def __init__(self, chroma_client):
        self.collection = chroma_client.get_or_create_collection("project_memory")

    def log(self, query: str, returned_files: list, insight: str = ""):
        doc = f"Query: {query}\nReturned files: {', '.join(returned_files)}\nInsight: {insight}"
        self.collection.add(
            documents=[doc],
            metadatas=[{"timestamp": datetime.now().isoformat(), "query": query}],
            ids=[f"mem_{datetime.now().timestamp():.0f}"]
        )

    def get_project_state(self, k: int = 10):
        results = self.collection.query(query_texts=["project overview and decisions"], n_results=k)
        return {"recent_activity": results.get("documents", [[]])[0]}

class CodebaseContextOracle:
    EXT_TO_LANG = {
        '.py': 'python', '.pyi': 'python',
        '.rs': 'rust',
        '.go': 'go',
        '.cs': 'csharp',
        '.c': 'c', '.h': 'c',
        '.cpp': 'cpp', '.hpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
        '.hxx': 'cpp',
        '.java': 'java',
        '.js': 'javascript', '.jsx': 'javascript',
        '.ts': 'typescript', '.tsx': 'typescript',
    }

    def __init__(self, root_dir: str = "."):
        self.root = Path(root_dir).resolve()
        self.index_dir = self.root / ".oracle_index"
        self.index_dir.mkdir(exist_ok=True)

        self.chroma = chromadb.PersistentClient(path=str(self.index_dir))
        self.collection = self.chroma.get_or_create_collection("code_chunks")
        self.memory = ProjectMemory(self.chroma)

        self.embedder = Embedder()
        self.graph = nx.DiGraph()
        self.parsers = {}
        self._load_parsers()

        self.metadata_path = self.index_dir / "metadata.json"
        self.metadata = self._load_metadata()

    def _load_parsers(self):
        for lang_id in set(self.EXT_TO_LANG.values()):
            try:
                self.parsers[lang_id] = get_parser(lang_id)
            except Exception as e:
                print(f"⚠️ Could not load parser for {lang_id}: {e}")

    def _load_metadata(self):
        if self.metadata_path.exists():
            try:
                return json.loads(self.metadata_path.read_text())
            except:
                pass
        return {}

    def _save_metadata(self):
        self.metadata_path.write_text(json.dumps(self.metadata, indent=2))

    def build(self, force: bool = False):
        print(f"🔍 Building index for {self.root}")
        updated = 0
        for file_path in sorted(self.root.rglob("*")):
            if not file_path.is_file() or any(p.startswith('.') for p in file_path.parts):
                continue
            if self._should_index(file_path, force):
                self._index_file(file_path)
                updated += 1
                if updated % 30 == 0:
                    print(f"   Processed {updated} files...")
        self._save_metadata()
        print(f"✅ Index ready! {updated} files updated • {self.collection.count()} chunks")

    def _should_index(self, file_path: Path, force: bool) -> bool:
        if force:
            return True
        rel = str(file_path.relative_to(self.root))
        last_mtime = self.metadata.get(rel, {}).get("mtime")
        return not last_mtime or file_path.stat().st_mtime > last_mtime

    def _index_file(self, file_path: Path):
        suffix = file_path.suffix.lower()
        lang_id = self.EXT_TO_LANG.get(suffix)
        rel_path = str(file_path.relative_to(self.root))
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except:
            return

        if lang_id and lang_id in self.parsers:
            self._structured_chunk(file_path, content, lang_id, rel_path)
        else:
            self._fallback_chunk(file_path, content, rel_path)

        self.metadata[rel_path] = {
            "mtime": file_path.stat().st_mtime,
            "last_indexed": datetime.now().isoformat()
        }

    def _structured_chunk(self, file_path: Path, content: str, lang_id: str, rel_path: str):
        parser = self.parsers[lang_id]
        tree = parser.parse(bytes(content, "utf-8"))
        chunks = self._ast_extract_chunks(tree, content)
        if not chunks:
            return self._fallback_chunk(file_path, content, rel_path)
        texts = [c["text"] for c in chunks]
        embeddings = self.embedder.embed(texts)
        for i, chunk in enumerate(chunks):
            doc_id = f"{rel_path}:{i}"
            self.collection.add(
                documents=[chunk["text"]],
                metadatas=[{
                    "file": rel_path,
                    "symbol": chunk.get("symbol"),
                    "kind": chunk.get("kind"),
                    "language": lang_id,
                    "start_line": chunk.get("start_line")
                }],
                ids=[doc_id],
                embeddings=[embeddings[i]]
            )

    def _ast_extract_chunks(self, tree, content: str):
        chunks = []
        def walk(node):
            if any(kw in node.type for kw in [
                "function", "method", "class", "struct", "enum", "trait", "impl",
                "interface", "record", "namespace"
            ]):
                start = node.start_byte
                end = node.end_byte
                text = content[start:end].strip()
                if len(text) > 50:
                    name_node = node.child_by_field_name("name") or node.child_by_field_name("identifier")
                    symbol = name_node.text.decode("utf-8") if name_node else None
                    chunks.append({
                        "text": text,
                        "symbol": symbol,
                        "kind": node.type,
                        "start_line": node.start_point[0] + 1
                    })
            for child in node.children:
                walk(child)
        walk(tree.root_node)
        return chunks

    def _fallback_chunk(self, file_path: Path, content: str, rel_path: str, chunk_size=700):
        lines = content.splitlines()
        for i in range(0, len(lines), chunk_size - 80):
            chunk = "\n".join(lines[i:i + chunk_size])
            if len(chunk.strip()) < 60:
                continue
            doc_id = f"{rel_path}:fb_{i}"
            self.collection.add(
                documents=[chunk],
                metadatas=[{"file": rel_path, "kind": "fallback"}],
                ids=[doc_id]
            )

    def query(self, natural_language_query: str, k: int = 8):
        results = self.collection.query(
            query_texts=[natural_language_query],
            n_results=min(k, 20),
            include=["documents", "metadatas"]
        )
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        returned_files = sorted({m["file"] for m in metas})
        self.memory.log(natural_language_query, returned_files)
        return {
            "success": True,
            "query": natural_language_query,
            "results": [{"content": d, "metadata": m} for d, m in zip(docs, metas)],
            "files": returned_files,
            "memory_note": "Logged to project memory"
        }

    def overview(self):
        return {
            "status": "ready",
            "root": str(self.root),
            "total_chunks": self.collection.count(),
            "supported_languages": sorted(set(self.EXT_TO_LANG.values()))
        }

    def symbol_usages(self, symbol: str):
        results = self.collection.query(query_texts=[symbol], n_results=15, include=["metadatas"])
        return {
            "symbol": symbol,
            "found_in_files": sorted({m["file"] for m in results["metadatas"][0]})
        }

    def get_project_memory(self, k: int = 10):
        return self.memory.get_project_state(k)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build"], nargs="?", default="build")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    oracle = CodebaseContextOracle()
    oracle.build(force=args.force)
