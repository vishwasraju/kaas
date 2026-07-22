import logging
from typing import List, Dict, Any

try:
    from flashrank import Ranker, RerankRequest
    HAS_FLASHRANK = True
except ImportError:
    HAS_FLASHRANK = False

from rag.vector_store import VectorStore
from rag.bm25_retriever import BM25Retriever

logger = logging.getLogger(__name__)

class HybridRetriever:
    def __init__(self, vector_store: VectorStore, bm25_retriever: BM25Retriever):
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever
        
        self.ranker = None
        if HAS_FLASHRANK:
            try:
                self.ranker = Ranker()
            except Exception as e:
                logger.error(f"Failed to initialize FlashRank Ranker: {e}")
                self.ranker = None

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search both vector store and BM25, combine with RRF, and optionally rerank.
        """
        # Fetch more candidates for reranking
        candidate_k = max(top_k * 3, 20)
        
        # 1. Get results from both retrievers
        vector_results = self.vector_store.search(query, n_results=candidate_k)
        bm25_results = self.bm25_retriever.search(query, n_results=candidate_k)
        
        # 2. Reciprocal Rank Fusion (RRF)
        # score(d) = sum(1 / (k + rank(d))) where k=60
        rrf_k = 60
        rrf_scores = {}
        chunk_map = {}
        source_map = {}
        
        # Process vector results
        for rank, res in enumerate(vector_results):
            doc_id = res["id"]
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0.0
                chunk_map[doc_id] = res
                source_map[doc_id] = ["vector"]
            else:
                source_map[doc_id].append("vector")
            rrf_scores[doc_id] += 1.0 / (rrf_k + rank + 1)
            
        # Process BM25 results
        for rank, res in enumerate(bm25_results):
            doc_id = res["id"]
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0.0
                chunk_map[doc_id] = res
                source_map[doc_id] = ["bm25"]
            else:
                if "bm25" not in source_map[doc_id]:
                    source_map[doc_id].append("bm25")
            rrf_scores[doc_id] += 1.0 / (rrf_k + rank + 1)
            
        # Sort by RRF score
        fused_results = []
        for doc_id, score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
            fused_results.append({
                "id": doc_id,
                "text": chunk_map[doc_id]["text"],
                "metadata": chunk_map[doc_id]["metadata"],
                "score": score,
                "search_type": source_map[doc_id]
            })
            
        # Limit to candidate_k
        fused_results = fused_results[:candidate_k]
        
        # 3. Rerank if available
        if self.ranker and fused_results:
            try:
                # Prepare passages for FlashRank
                passages = []
                for res in fused_results:
                    passages.append({
                        "id": res["id"],
                        "text": res["text"],
                        "meta": res["metadata"]
                    })
                    
                rerankrequest = RerankRequest(query=query, passages=passages)
                reranked_passages = self.ranker.rerank(rerankrequest)
                
                # Re-map to our format
                reranked_results = []
                # Flashrank returns sorted list of dicts, including 'score'
                for p in reranked_passages:
                    doc_id = p["id"]
                    original_res = next((r for r in fused_results if r["id"] == doc_id), None)
                    if original_res:
                        reranked_results.append({
                            "id": doc_id,
                            "text": p["text"],
                            "metadata": original_res["metadata"],
                            "score": float(p.get("score", 0.0)),
                            "search_type": original_res["search_type"] + ["reranked"]
                        })
                
                fused_results = reranked_results
            except Exception as e:
                logger.error(f"Reranking failed, falling back to RRF: {e}")
                
        # Return top_k
        return fused_results[:top_k]
