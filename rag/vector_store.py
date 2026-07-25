import os
import logging
import math

from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# ChromaDB is now always available (Docker has no size limits)
try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    logger.warning("ChromaDB not installed. Vector search will not work.")


class VectorStore:
    """
    Vector store using ChromaDB for semantic search.
    Generates embeddings via Gemini API (models/gemini-embedding-001).
    """

    def __init__(self):
        if not HAS_CHROMADB:
            raise ImportError(
                "ChromaDB is required. Install it with: pip install chromadb"
            )
        self.chroma_client = chromadb.Client()
        self.session_id = None
        self.collection_obj = None
        self.model = "models/gemini-embedding-001"
        self.chunks = []
        self.embeddings = []

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

    @property
    def collection(self):
        """Compatibility property for chunk counting in routes/upload.py."""
        class CollectionProxy:
            def __init__(self, store):
                self.store = store
            def count(self):
                return self.store.count()
        return CollectionProxy(self)
