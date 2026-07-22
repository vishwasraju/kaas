import string
import logging
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

class BM25Retriever:
    def __init__(self):
        self.bm25 = None
        self.chunks = []
        
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization: lowercase and remove punctuation."""
        if not text:
            return []
        text = text.lower()
        # Remove punctuation
        text = text.translate(str.maketrans('', '', string.punctuation))
        return text.split()

    def index(self, chunks: List[Dict[str, Any]]):
        """Index chunks for BM25 retrieval."""
        self.chunks = chunks
        if not chunks:
            self.bm25 = None
            return
            
        tokenized_corpus = [self._tokenize(chunk["text"]) for chunk in self.chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)
        logger.info(f"Indexed {len(chunks)} chunks in BM25Retriever.")

    def search(self, query: str, n_results: int = 20) -> List[Dict[str, Any]]:
        """Search the indexed chunks using BM25."""
        if not self.bm25 or not self.chunks:
            return []
            
        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n_results]
        
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0.0:
                continue # Skip non-matching chunks
                
            chunk = self.chunks[idx]
            results.append({
                "id": chunk["id"],
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "score": score
            })
            
        return results
