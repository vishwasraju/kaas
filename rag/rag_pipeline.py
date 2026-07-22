import os
import uuid
import time
import logging
from typing import Dict, Any, List

from google import genai
from google.genai import types

from models.document import Document
from models.repository import Repository
from rag.chunker import RecursiveTextChunker
from rag.vector_store import VectorStore
from rag.bm25_retriever import BM25Retriever
from rag.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        self.chunker = RecursiveTextChunker()
        self.vector_store = VectorStore()
        self.bm25_retriever = BM25Retriever()
        self.hybrid_retriever = None
        self.session_id = None
        
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            logger.warning("GEMINI_API_KEY not found. Querying will fail.")
            self.client = None
            
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def index_document(self, document: Document, session_id: str):
        """Index a document by chunking it directly."""
        self.session_id = session_id
        
        # 1. Chunk
        chunks = self.chunker.chunk_document(document)
        
        # 2. Vector Store
        self.vector_store.create_collection(session_id)
        self.vector_store.add_chunks(chunks)
        
        # 3. BM25
        self.bm25_retriever.index(chunks)
        
        # 4. Hybrid
        self.hybrid_retriever = HybridRetriever(self.vector_store, self.bm25_retriever)
        
        return len(chunks)

    def index_repository(self, repository: Repository, document: Document, session_id: str):
        """Index an OKF repository. Uses OKF concept files as chunks."""
        self.session_id = session_id
        
        chunks = []
        chunk_index = 0
        
        for file in repository.files:
            # We skip index.md or other structural files if they don't have good content,
            # but usually OKF files have content. We'll use the title and content.
            if not file.content or not file.content.strip():
                continue
                
            text = f"Title: {file.title}\nDescription: {file.description}\n\n{file.content}"
            
            chunks.append({
                "id": f"okf_{uuid.uuid4()}",
                "text": text,
                "metadata": {
                    "chunk_index": chunk_index,
                    "original_section_title": file.title,
                    "page_number": -1,
                    "type": file.type
                }
            })
            chunk_index += 1
            
        # 2. Vector Store
        self.vector_store.create_collection(session_id)
        self.vector_store.add_chunks(chunks)
        
        # 3. BM25
        self.bm25_retriever.index(chunks)
        
        # 4. Hybrid
        self.hybrid_retriever = HybridRetriever(self.vector_store, self.bm25_retriever)
        
        return len(chunks)

    def query(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        """Query the indexed data and generate an answer."""
        if not self.hybrid_retriever:
            raise ValueError("No data indexed in this session.")
            
        if not self.client:
            raise ValueError("Gemini client not initialized (missing API key).")

        query_start = time.time()

        # Retrieve chunks
        sources = self.hybrid_retriever.search(question, top_k=top_k)
        
        if not sources:
            return {
                "answer": "I don't have enough context to answer this question.",
                "sources": [],
                "stats": {"retrieved": 0, "vector_results": 0, "bm25_results": 0, "reranked": 0, "latency_ms": 0}
            }

        # Compute search type stats
        vector_count = sum(1 for s in sources if "vector" in s.get("search_type", []))
        bm25_count = sum(1 for s in sources if "bm25" in s.get("search_type", []))
        reranked_count = sum(1 for s in sources if "reranked" in s.get("search_type", []))

        # Build prompt
        context_parts = []
        for i, source in enumerate(sources):
            page_info = ""
            page_num = source["metadata"].get("page_number", -1)
            if page_num != -1:
                page_info = f" (Page {page_num})"
            context_parts.append(f"--- Source {i+1}{page_info} ---\n{source['text']}\n")
            
        context_str = "\n".join(context_parts)
        
        system_prompt = (
            "You are a helpful assistant answering questions based on the provided document excerpts. "
            "Please answer the user's question based strictly on the provided context. "
            "Cite your sources using the source number (e.g. [1]). "
            "If the provided context does not contain the answer, say 'I don't have enough context'."
        )
        
        user_content = f"Context:\n{context_str}\n\nQuestion: {question}"
        
        # Call Gemini with retry logic
        answer = "Sorry, an error occurred while generating the answer."
        max_retries = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.0
                    )
                )
                answer = response.text
                break
            except Exception as e:
                logger.warning(f"Gemini generation attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)

        latency_ms = int((time.time() - query_start) * 1000)

        return {
            "answer": answer,
            "sources": sources,
            "stats": {
                "retrieved": len(sources),
                "vector_results": vector_count,
                "bm25_results": bm25_count,
                "reranked": reranked_count,
                "latency_ms": latency_ms
            }
        }

    def export_vector_db_data(self) -> dict:
        """Export chunks, metadata, and pre-computed embeddings as a JSON-serializable dict."""
        store = self.vector_store._impl
        
        items = []
        chunks = getattr(store, "chunks", [])
        embeddings = getattr(store, "embeddings", [])

        if not chunks and hasattr(store, "collection_obj") and store.collection_obj:
            try:
                data = store.collection_obj.get(include=["documents", "metadatas", "embeddings"])
                if data and data.get("ids"):
                    for i in range(len(data["ids"])):
                        items.append({
                            "id": data["ids"][i],
                            "text": data["documents"][i] if data.get("documents") else "",
                            "metadata": data["metadatas"][i] if data.get("metadatas") else {},
                            "embedding": data["embeddings"][i] if data.get("embeddings") is not None else []
                        })
                    return {
                        "session_id": self.session_id,
                        "total_chunks": len(items),
                        "embedding_model": "models/gemini-embedding-001",
                        "items": items
                    }
            except Exception as e:
                logger.error(f"Failed to export ChromaDB collection: {e}")

        for idx, chunk in enumerate(chunks):
            emb = embeddings[idx] if idx < len(embeddings) else []
            items.append({
                "id": chunk.get("id", f"chunk_{idx}"),
                "text": chunk.get("text", ""),
                "metadata": chunk.get("metadata", {}),
                "embedding": emb
            })
            
        return {
            "session_id": self.session_id,
            "total_chunks": len(items),
            "embedding_model": "models/gemini-embedding-001",
            "items": items
        }

# Global dictionary to store RAG sessions
_sessions: Dict[str, RAGPipeline] = {}
