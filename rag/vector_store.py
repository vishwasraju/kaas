import os
import logging
from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

class GeminiEmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(self):
        try:
            from google import genai
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.warning("GEMINI_API_KEY not found, Gemini embeddings may fail.")
            self.client = genai.Client(api_key=api_key)
            self.model = "text-embedding-004"
            self.fallback_fn = embedding_functions.DefaultEmbeddingFunction()
        except ImportError:
            logger.error("google.genai not installed. Falling back to DefaultEmbeddingFunction.")
            self.client = None
            self.fallback_fn = embedding_functions.DefaultEmbeddingFunction()

    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        if not self.client:
            return self.fallback_fn(input)
            
        embeddings = []
        try:
            for text in input:
                response = self.client.models.embed_content(
                    model=self.model,
                    contents=[text]
                )
                embeddings.append(response.embeddings[0].values)
            return embeddings
        except Exception as e:
            logger.error(f"Gemini embedding failed: {e}. Using fallback.")
            return self.fallback_fn(input)

class VectorStore:
    def __init__(self):
        # In-memory client (ephemeral)
        self.chroma_client = chromadb.Client()
        self.embedding_fn = GeminiEmbeddingFunction()
        self.collection = None
        self.session_id = None

    def create_collection(self, session_id: str):
        """Create or reset a collection for a given session."""
        self.session_id = session_id
        # Collection names must meet certain criteria (e.g. alphanumeric)
        safe_session_id = "".join([c for c in session_id if c.isalnum() or c in "_-"])
        collection_name = f"session_{safe_session_id}"
        
        try:
            self.chroma_client.delete_collection(name=collection_name)
        except Exception:
            pass
            
        self.collection = self.chroma_client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )
        logger.info(f"Created ChromaDB collection: {collection_name}")

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        """Add chunks to the collection."""
        if not self.collection:
            raise ValueError("Collection not created. Call create_collection first.")
            
        if not chunks:
            return
            
        ids = [c["id"] for c in chunks]
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        
        self.collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas
        )
        logger.info(f"Added {len(chunks)} chunks to VectorStore.")

    def search(self, query: str, n_results: int = 20) -> List[Dict[str, Any]]:
        """Search the collection."""
        if not self.collection:
            raise ValueError("Collection not created. Call create_collection first.")
            
        try:
            # Query the collection
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            if results["ids"] and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    doc_id = results["ids"][0][i]
                    text = results["documents"][0][i]
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0.0
                    
                    formatted_results.append({
                        "id": doc_id,
                        "text": text,
                        "metadata": metadata,
                        "distance": distance
                    })
                    
            return formatted_results
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
