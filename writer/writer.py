"""
Writes the OKF bundle files and packages them into output.zip.
Produces spec-conformant output per OKF v0.1.
"""

import os
import shutil
import tempfile
import zipfile
from datetime import date

import yaml

from models.repository import Repository
from models.okf_file import OKFFile
from writer.graph_builder import build_graph_html


def build_index_file(repository: Repository) -> str:
    """
    Build the root index.md content.
    Per OKF spec §6, index files contain NO frontmatter.
    Uses standard markdown links (not wiki-links).
    """

    lines = [f"# {repository.title}", ""]

    # Group files by directory
    groups = {}
    for f in repository.files:
        parts = f.path.split("/")
        if len(parts) > 1:
            group_dir = parts[0]
            group_name = group_dir.replace("-", " ").title()
        else:
            group_dir = ""
            group_name = "General"
        groups.setdefault((group_dir, group_name), []).append(f)

    for (group_dir, group_name), files in groups.items():
        lines.append(f"## {group_name}")
        lines.append("")
        for f in files:
            desc = f" - {f.description}" if f.description else ""
            lines.append(f"* [{f.title}]({f.path}){desc}")
        lines.append("")

    return "\n".join(lines)


def build_subdir_index(group_name: str, files: list) -> str:
    """
    Build an index.md for a subdirectory.
    Per OKF spec §6, index files contain NO frontmatter.
    """

    lines = [f"# {group_name}", ""]

    for f in files:
        basename = f.path.split("/")[-1]
        desc = f" - {f.description}" if f.description else ""
        lines.append(f"* [{f.title}]({basename}){desc}")

    lines.append("")
    return "\n".join(lines)


def build_concept_file(okf: OKFFile) -> str:
    """
    Build the content for a single concept .md file.
    Frontmatter follows OKF spec §4.1.
    Body follows OKF spec §4.2 with cross-links per §5.
    """

    # Build frontmatter: required + recommended fields first
    frontmatter = {"type": okf.type}

    if okf.title:
        frontmatter["title"] = okf.title

    if okf.description:
        frontmatter["description"] = okf.description

    if okf.tags:
        frontmatter["tags"] = okf.tags

    if okf.timestamp:
        frontmatter["timestamp"] = okf.timestamp

    # Extension fields from metadata (§4.1: producers MAY include any keys)
    for key, value in okf.metadata.items():
        frontmatter[key] = value

    yaml_text = yaml.safe_dump(
        frontmatter,
        allow_unicode=True,
        sort_keys=False,
    )

    md = (
        "---\n"
        + yaml_text
        + "---\n\n"
        + "# "
        + okf.title
        + "\n\n"
        + okf.content
    )

    # Add cross-links section using standard markdown links (§5)
    if okf.relationships:
        md += "\n\n## Related Concepts\n\n"
        for rel in okf.relationships:
            rel_type = rel.get("type", "related")
            target = rel.get("target", "")
            target_path = rel.get("target_path")
            if target_path:
                # Bundle-relative absolute link (§5.1)
                md += f"- {rel_type}: [{target}](/{target_path})\n"
            else:
                md += f"- {rel_type}: {target}\n"

    # Add citations section for external sources (§8)
    if okf.citations:
        md += "\n# Citations\n\n"
        for i, cite in enumerate(okf.citations, 1):
            md += f"[{i}] [{cite['text']}]({cite['url']})\n"

    md += "\n"
    return md


def build_log_file(repository: Repository) -> str:
    """
    Build a log.md recording the conversion event.
    Per OKF spec §7, uses ISO 8601 date headings, newest first.
    """

    today = date.today().isoformat()

    lines = ["# Directory Update Log", ""]
    lines.append(f"## {today}")
    for f in repository.files:
        lines.append(f"* **Creation**: Created [{f.title}](/{f.path}).")
    lines.append("")

    return "\n".join(lines)


def write_repository(repository: Repository, output_dir: str = "output"):
    """
    Write the entire OKF bundle to disk as a directory tree.
    """

    from pathlib import Path

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # Write root index.md (§6)
    with open(
        output / "index.md",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(build_index_file(repository))

    # Write root log.md (§7)
    with open(
        output / "log.md",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(build_log_file(repository))

    # Write root interactive graph visualizer
    with open(
        output / "visualize_graph.html",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(build_graph_html(repository))

    # Group files by directory for subdirectory indexes
    groups = {}
    for okf in repository.files:
        parts = okf.path.split("/")
        if len(parts) > 1:
            group_dir = parts[0]
            group_name = group_dir.replace("-", " ").title()
            groups.setdefault((group_dir, group_name), []).append(okf)

    # Write subdirectory indexes (§6)
    for (group_dir, group_name), files in groups.items():
        subdir = output / group_dir
        subdir.mkdir(parents=True, exist_ok=True)
        with open(
            subdir / "index.md",
            "w",
            encoding="utf-8",
        ) as f:
            f.write(build_subdir_index(group_name, files))

    # Write every concept document (§4)
    for okf in repository.files:
        filepath = output / okf.path
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(
            filepath,
            "w",
            encoding="utf-8",
        ) as f:
            f.write(build_concept_file(okf))


QUERY_RAG_SCRIPT = '''"""
Standalone RAG Retrieval & Q&A Script
Loads 'vector_db.json' and allows offline vector search and Q&A.

Usage:
    python query_rag.py "Your question here"
"""

import sys
import os
import json
import math
import time
from dotenv import load_dotenv

load_dotenv()

def cosine_similarity(v1, v2):
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    return dot / (norm1 * norm2) if norm1 * norm2 != 0 else 0.0

class OfflineRAG:
    def __init__(self, db_path="vector_db.json"):
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file '{db_path}' not found.")
        with open(db_path, "r", encoding="utf-8") as f:
            self.db = json.load(f)
        self.items = self.db.get("items", [])
        self.model = self.db.get("embedding_model", "models/gemini-embedding-001")
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Warning: GEMINI_API_KEY not found in environment.")
            self.client = None
        else:
            from google import genai
            self.client = genai.Client(api_key=api_key)

    def _call_api_with_retry(self, api_func, *args, **kwargs):
        from google.genai.errors import ClientError
        max_retries = 3
        delay = 2.0
        for attempt in range(max_retries):
            try:
                return api_func(*args, **kwargs)
            except ClientError as e:
                if e.code == 429:
                    if attempt < max_retries - 1:
                        recommended_delay = None
                        try:
                            if hasattr(e, 'details') and isinstance(e.details, dict):
                                err_details = e.details.get('error', {}).get('details', [])
                                for detail in err_details:
                                    if detail.get('@type') == 'type.googleapis.com/google.rpc.RetryInfo':
                                        delay_str = detail.get('retryDelay', '')
                                        if delay_str.endswith('s'):
                                            recommended_delay = float(delay_str[:-1])
                        except Exception:
                            pass
                        
                        sleep_time = delay
                        if recommended_delay is not None:
                            sleep_time = min(recommended_delay, 45.0)
                        
                        print(f"Rate limit hit (429 RESOURCE_EXHAUSTED). Retrying in {sleep_time:.1f}s... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(sleep_time)
                        delay *= 2
                        continue
                raise e

    def search(self, question, top_k=3):
        if not self.client:
            raise ValueError("GEMINI_API_KEY is required to convert query into vector.")
        res = self._call_api_with_retry(
            self.client.models.embed_content,
            model=self.model,
            contents=[question]
        )
        q_emb = res.embeddings[0].values
        
        scored = []
        for item in self.items:
            sim = cosine_similarity(q_emb, item["embedding"])
            scored.append({
                "similarity_score": round(sim, 4),
                "text": item["text"],
                "metadata": item["metadata"]
            })
        scored.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored[:top_k]

    def answer(self, question):
        results = self.search(question, top_k=3)
        if not results:
            return "No matching context found.", []
            
        context = "\\n\\n".join([
            f"--- Source {i+1} (Page {r['metadata'].get('page_number', 'N/A')}) ---\\n{r['text']}"
            for i, r in enumerate(results)
        ])
        
        prompt = f"Context:\\n{context}\\n\\nQuestion: {question}\\n\\nAnswer based strictly on context:"
        
        from google.genai import types
        candidate_models = ["gemini-2.5-flash", "gemini-1.5-flash"]
        
        last_exception = None
        for model in candidate_models:
            try:
                res = self._call_api_with_retry(
                    self.client.models.generate_content,
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction="You are a helpful assistant answering questions based strictly on context.",
                        temperature=0.0
                    )
                )
                return res.text, results
            except Exception as e:
                from google.genai.errors import ClientError
                if isinstance(e, ClientError) and e.code == 429:
                    print(f"Model '{model}' hit rate limit. Trying fallback model...")
                    last_exception = e
                    continue
                raise e
                
        if last_exception:
            raise last_exception

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python query_rag.py \\"Your question here\\"")
        sys.exit(1)
        
    question = sys.argv[1]
    print(f"\\nSearching vector_db.json for: '{question}'\\n")
    
    try:
        rag = OfflineRAG()
        answer, sources = rag.answer(question)
        
        print("Answer:\\n", answer)
        print("\\nSources:")
        for i, s in enumerate(sources, 1):
            print(f"[{i}] Page {s['metadata'].get('page_number', 'N/A')} (Score: {s['similarity_score']}): {s['text'][:120]}...")
    except Exception as e:
        from google.genai.errors import ClientError
        if isinstance(e, ClientError):
            print(f"\\n[Client Error] Gemini API Client Error (Status Code: {e.code})")
            print(f"Details: {e.message}")
            if e.code == 429:
                print("\\n[Tip] You have exceeded your Gemini API rate limit or quota. If you are on the Free Tier, wait a moment before trying again, check your rate limits, or set up a billing profile for higher limits.")
        else:
            print(f"\\n[Error] {e}")
        sys.exit(1)
'''

RAG_README_CONTENT = '''# Offline Vector RAG Package

This ZIP archive contains your converted document, the exported Vector Database (`vector_db.json`), and standalone Python code for querying it.

## Quick Start

1. Install requirements:
   ```bash
   pip install google-genai python-dotenv
   ```

2. Set your Gemini API key in your terminal or `.env` file:
   ```bash
   export GEMINI_API_KEY="your_gemini_api_key_here"
   ```

3. Run the query script:
   ```bash
   python query_rag.py "What is the main topic of this document?"
   ```

## Package Contents
- `vector_db.json`: Portable vector database containing chunks, page metadata, and pre-computed Gemini vector embeddings.
- `query_rag.py`: Standalone Python script to convert queries to vectors, search `vector_db.json`, and synthesize answers.
- `index.md` & concept `.md` files: OKF knowledge modules.
'''


def write_zip(repository: Repository = None, output_dir: str = None, rag_pipeline=None) -> str:
    """
    Write the OKF bundle and/or RAG Vector Database into a ZIP archive.

    Args:
        repository: Optional OKF Repository object.
        output_dir: Directory to write output.zip to.
        rag_pipeline: Optional RAGPipeline object containing vector embeddings.

    Returns:
        Absolute path to the generated output.zip.
    """

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="pdf_to_okf_")

    os.makedirs(output_dir, exist_ok=True)

    zip_path = os.path.join(output_dir, "output.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:

        if repository:
            # Write root index.md (§6)
            zf.writestr("index.md", build_index_file(repository))

            # Write root log.md (§7)
            zf.writestr("log.md", build_log_file(repository))

            # Write root interactive graph visualizer
            zf.writestr("visualize_graph.html", build_graph_html(repository))

            # Group files by directory for subdirectory indexes
            groups = {}
            for f in repository.files:
                parts = f.path.split("/")
                if len(parts) > 1:
                    group_dir = parts[0]
                    group_name = group_dir.replace("-", " ").title()
                    groups.setdefault((group_dir, group_name), []).append(f)

            # Write subdirectory index.md files (§6)
            for (group_dir, group_name), files in groups.items():
                zf.writestr(
                    f"{group_dir}/index.md",
                    build_subdir_index(group_name, files),
                )

            # Write each concept file (§4)
            for okf in repository.files:
                zf.writestr(
                    okf.path,
                    build_concept_file(okf),
                )

        # Include RAG vector database & query code if rag_pipeline provided
        if rag_pipeline:
            import json
            vector_db_data = rag_pipeline.export_vector_db_data()
            zf.writestr("vector_db.json", json.dumps(vector_db_data, indent=2))
            zf.writestr("query_rag.py", QUERY_RAG_SCRIPT)
            zf.writestr("RAG_README.md", RAG_README_CONTENT)

    return zip_path


def cleanup_temp_dir(zip_path: str) -> None:
    """
    Remove the temporary directory containing the ZIP file.
    Should be called after the ZIP has been sent to the client.
    """

    temp_dir = os.path.dirname(zip_path)
    if temp_dir and os.path.basename(temp_dir).startswith("pdf_to_okf_"):
        shutil.rmtree(temp_dir, ignore_errors=True)