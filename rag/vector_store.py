import os
import math
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Optional heavy dependency: ChromaDB
try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

# Optional numpy dependency
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if HAS_NUMPY:
        v1 = np.array(vec1, dtype=np.float32)
        v2 = np.array(vec2, dtype=np.float32)
        norm = np.linalg.norm(v1) * np.linalg.norm(v2)
        if norm == 0:
            return 0.0
        return float(np.dot(v1, v2) / norm)

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 * norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class LightweightVectorStore:
    """
    Serverless-friendly, zero-C++ dependency vector store.
    Generates embeddings via Gemini API (text-embedding-004) and computes
    cosine similarity in memory.
    """

    def __init__(self):
        self.session_id = None
        self.chunks = []
        self.embeddings = []
        self.model = "models/gemini-embedding-001"
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    logger.warning("GEMINI_API_KEY environment variable is not set.")
                self._client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client for embeddings: {e}")
                self._client = None
        return self._client

    def create_collection(self, session_id: str):
        self.session_id = session_id
        self.chunks = []
        self.embeddings = []

    def _embed_text(self, text: str) -> List[float]:
        client = self._get_client()
        if not client:
            return []
        try:
            response = client.models.embed_content(
                model=self.model,
                contents=[text]
            )
            return response.embeddings[0].values
        except Exception as e:
            logger.error(f"Gemini embedding call failed: {e}")
            return []

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        if not chunks:
            return
        self.chunks = chunks
        self.embeddings = []
        for chunk in chunks:
            text = chunk.get("text", "")
            emb = self._embed_text(text)
            self.embeddings.append(emb)
        logger.info(f"LightweightVectorStore indexed {len(chunks)} chunks with Gemini embeddings.")

    def search(self, query: str, n_results: int = 20) -> List[Dict[str, Any]]:
        if not self.chunks or not self.embeddings:
            return []

        query_emb = self._embed_text(query)
        if not query_emb:
            return []

        scored = []
        for idx, chunk in enumerate(self.chunks):
            emb = self.embeddings[idx]
            if not emb:
                continue
            sim = _cosine_similarity(query_emb, emb)
            scored.append({
                "id": chunk["id"],
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "distance": 1.0 - sim,  # Distance measure for compatibility
                "similarity": sim
            })

        # Sort descending by similarity
        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:n_results]

    def count(self) -> int:
        return len(self.chunks)


class VectorStore:
    """
    VectorStore wrapper that dynamically selects ChromaDB (if available) or
    LightweightVectorStore (for serverless environments like Vercel).
    """

    def __init__(self):
        if HAS_CHROMADB:
            try:
                self._impl = ChromaDBStore()
                logger.info("Using ChromaDB VectorStore implementation.")
            except Exception as e:
                logger.warning(f"ChromaDB initialization failed: {e}. Falling back to LightweightVectorStore.")
                self._impl = LightweightVectorStore()
        else:
            logger.info("ChromaDB not installed. Using serverless LightweightVectorStore.")
            self._impl = LightweightVectorStore()

    def create_collection(self, session_id: str):
        return self._impl.create_collection(session_id)

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        return self._impl.add_chunks(chunks)

    def search(self, query: str, n_results: int = 20) -> List[Dict[str, Any]]:
        return self._impl.search(query, n_results=n_results)

    @property
    def collection(self):
        # Compatibility property for chunk counting in routes/upload.py
        class CollectionProxy:
            def __init__(self, store):
                self.store = store
            def count(self):
                if hasattr(self.store._impl, 'collection') and self.store._impl.collection:
                    return self.store._impl.collection.count()
                return self.store._impl.count()
        return CollectionProxy(self)


class ChromaDBStore:
    """ChromaDB implementation for environments with C++ native dependencies."""

    def __init__(self):
        self.chroma_client = chromadb.Client()
        self.session_id = None
        self.collection_obj = None
        self.model = "models/gemini-embedding-001"

    def create_collection(self, session_id: str):
        self.session_id = session_id
        self.chunks = []
        self.embeddings = []
        safe_session_id = "".join([c for c in session_id if c.isalnum() or c in "_-"])
        collection_name = f"session_{safe_session_id}"
        try:
            self.chroma_client.delete_collection(name=collection_name)
        except Exception:
            pass
        self.collection_obj = self.chroma_client.create_collection(name=collection_name)

    def _embed(self, texts: List[str]) -> List[List[float]]:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        res = []
        for t in texts:
            r = client.models.embed_content(model=self.model, contents=[t])
            res.append(r.embeddings[0].values)
        return res

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        if not self.collection_obj or not chunks:
            return
        ids = [c["id"] for c in chunks]
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        embeddings = self._embed(texts)
        self.chunks = chunks
        self.embeddings = embeddings
        self.collection_obj.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)

    def search(self, query: str, n_results: int = 20) -> List[Dict[str, Any]]:
        if not self.collection_obj:
            return []
        query_emb = self._embed([query])
        results = self.collection_obj.query(query_embeddings=query_emb, n_results=n_results)
        formatted = []
        if results["ids"] and len(results["ids"]) > 0:
            for i in range(len(results["ids"][0])):
                formatted.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0
                })
        return formatted

    def count(self) -> int:
        return self.collection_obj.count() if self.collection_obj else 0
