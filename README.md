# PDF to OKF

**Lossless PDF to Open Knowledge Format converter.**

Converts PDF documents into structured `.okf.md` knowledge units using AI-powered document analysis, preserving 100% of the original content.

## Architecture

```
PDF File
  │
  ├── Step 1: Extract (PyMuPDF) — text, paragraphs, tables, links, images
  ├── Step 2: Canonicalize — unicode, whitespace, line endings
  ├── Step 3: AI Analysis (Gemini) — identify knowledge units
  ├── Step 4: Generate — create OKF repository structure
  ├── Step 5: Validate — check IDs, titles, content integrity
  └── Step 6: Package — write .okf.md files into output.zip
```

## Quick Start

### Prerequisites

- Python 3.10+
- A Google Gemini API key

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd pdf_to_okf

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Running

```bash
# Start the web server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000) to upload a PDF.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | *(required)* | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model to use |
| `GEMINI_MAX_RETRIES` | `3` | Max retry attempts for Gemini API |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum upload file size in MB |
| `LOG_LEVEL` | `INFO` | Logging level |

## OKF Format

Each knowledge unit is a Markdown file with YAML frontmatter:

```yaml
---
id: sec_001
title: Neural Networks
type: concept
version: "1.0"
document_type: textbook
language: en
source:
  document: DeepLearning.pdf
  pages: 25-48
related:
  - type: prerequisite
    target: Linear Algebra
created: "2026-07-11"
updated: "2026-07-11"
author: PDF to OKF Converter
---

# Neural Networks

[Original content preserved verbatim...]
```

## Project Structure

```
pdf_to_okf/
├── app.py                  # FastAPI application
├── pipeline.py             # Central pipeline orchestrator
├── logging_config.py       # Logging configuration
├── canonicalizer/          # Text normalization
├── converter/              # AI document analysis (Gemini)
├── extractor/              # PDF reading (PyMuPDF)
├── generator/              # OKF repository generation
├── models/                 # Data classes
├── routes/                 # FastAPI route handlers
├── static/                 # CSS
├── templates/              # HTML templates
├── tester/                 # Integrity checking
├── validator/              # Repository validation
└── writer/                 # OKF file & ZIP writer
```

## License

MIT
