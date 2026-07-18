"""
Calls Gemini to analyze the document and
returns a repository plan in JSON format.
"""

import logging
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from converter.dto import document_to_json
from converter.parser import parse_ai_response
from converter.prompt import SYSTEM_PROMPT
from models.document import Document

logger = logging.getLogger(__name__)

load_dotenv()

client = None


def _get_client():
    global client
    if client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please configure GEMINI_API_KEY in your Vercel Project Environment Variables."
            )
        client = genai.Client(api_key=api_key)
    return client

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "3"))

# Errors that should NOT trigger a retry (bad data, not transient)
_NON_RETRYABLE = (ValueError, TypeError, KeyError)


def analyze_document(document: Document) -> dict:
    """
    Sends the document to Gemini with retry logic.

    Only retries on transient API/network errors (503, 429, timeout).
    Parse and schema errors fail immediately.

    Returns:
        Parsed JSON dictionary from Gemini.
    """

    document_json = document_to_json(document)

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                f"Calling Gemini ({GEMINI_MODEL}), "
                f"attempt {attempt}/{MAX_RETRIES}"
            )

            response = _get_client().models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    SYSTEM_PROMPT,
                    document_json
                ],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                )
            )

            return parse_ai_response(response.text)

        except _NON_RETRYABLE as e:
            # Parse/schema errors — fail immediately, no retry
            logger.error(f"Non-retryable error: {e}")
            raise

        except Exception as e:
            last_error = e
            logger.warning(
                f"Gemini attempt {attempt}/{MAX_RETRIES} failed: {e}"
            )

            if attempt < MAX_RETRIES:
                wait = 2 ** attempt  # Exponential backoff: 2s, 4s
                logger.info(f"Retrying in {wait}s...")
                time.sleep(wait)

    raise RuntimeError(
        f"Gemini API failed after {MAX_RETRIES} attempts: {last_error}"
    ) from last_error