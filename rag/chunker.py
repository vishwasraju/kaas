import uuid
from typing import List, Dict, Any
from models.document import Document

class RecursiveTextChunker:
    """
    A recursive text chunker that splits text into chunks of roughly `chunk_size` characters
    with a given `chunk_overlap`.
    """
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", " "]

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text based on separators."""
        if not text:
            return []
            
        if not separators:
            # If no separators left, split by raw length
            return [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size)]
            
        separator = separators[0]
        splits = text.split(separator)
        
        good_splits = []
        for s in splits:
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if separator != "":
                    # Try next separator
                    good_splits.extend(self._split_text(s, separators[1:]))
                else:
                    good_splits.append(s)
                    
        # Now merge small splits
        return self._merge_splits(good_splits, separator)
        
    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        docs = []
        current_doc = []
        length = 0
        
        for s in splits:
            if length + len(s) + (len(separator) if length > 0 else 0) > self.chunk_size:
                if length > 0:
                    doc = separator.join(current_doc)
                    docs.append(doc)
                    
                    # Manage overlap
                    while length > self.chunk_overlap or (length > 0 and length + len(s) > self.chunk_size):
                        if not current_doc:
                            break
                        popped = current_doc.pop(0)
                        length -= len(popped) + (len(separator) if length > 0 else 0)
                        
            current_doc.append(s)
            length += len(s) + (len(separator) if len(current_doc) > 1 else 0)
            
        if current_doc:
            doc = separator.join(current_doc)
            docs.append(doc)
            
        return docs

    def chunk_document(self, document: Document) -> List[Dict[str, Any]]:
        """Chunk a complete document object, trying to preserve page metadata."""
        chunks = []
        chunk_index = 0
        
        # We can either chunk page by page or chunk the whole text and map pages back.
        # Chunking page by page is easier to keep page metadata accurately,
        # but cross-page chunks might be missed. Let's do page by page for simplicity.
        if document.pages:
            for page in document.pages:
                page_text = page.normalized_text or page.raw_text or ""
                if not page_text.strip():
                    continue
                    
                page_chunks = self.chunk_text(page_text, doc_title=document.filename)
                for pc in page_chunks:
                    pc["id"] = f"chunk_{uuid.uuid4()}"
                    pc["metadata"]["page_number"] = page.page_number
                    pc["metadata"]["chunk_index"] = chunk_index
                    chunks.append(pc)
                    chunk_index += 1
        else:
            text = document.normalized_text or document.raw_text or ""
            doc_chunks = self.chunk_text(text, doc_title=document.filename)
            for c in doc_chunks:
                c["id"] = f"chunk_{uuid.uuid4()}"
                c["metadata"]["page_number"] = -1
                c["metadata"]["chunk_index"] = chunk_index
                chunks.append(c)
                chunk_index += 1
                
        return chunks

    def chunk_text(self, text: str, doc_title: str = "") -> List[Dict[str, Any]]:
        """Chunk arbitrary text."""
        raw_splits = self._split_text(text, self.separators)
        chunks = []
        for i, split in enumerate(raw_splits):
            if not split.strip():
                continue
            chunks.append({
                "id": f"chunk_{uuid.uuid4()}",
                "text": split.strip(),
                "metadata": {
                    "chunk_index": i,
                    "original_section_title": doc_title,
                    "page_number": -1
                }
            })
        return chunks
