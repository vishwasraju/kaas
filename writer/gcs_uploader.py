"""
Google Cloud Storage (GCS) helper for storing output bundles.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def upload_to_gcs(file_path: str, destination_blob_name: str) -> Optional[str]:
    """
    Uploads a file to Google Cloud Storage if GCS_BUCKET_NAME env var is set.
    
    Args:
        file_path: Local path to the file to upload.
        destination_blob_name: Target path/name inside the GCS bucket.

    Returns:
        The GCS URI (e.g. gs://my-bucket/output.zip) if successful, or None.
    """
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        return None

    try:
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_filename(file_path)

        gcs_uri = f"gs://{bucket_name}/{destination_blob_name}"
        logger.info(f"Successfully uploaded {file_path} to GCS bucket '{bucket_name}': {gcs_uri}")
        return gcs_uri

    except Exception as e:
        logger.error(f"Failed to upload to GCS bucket '{bucket_name}': {e}", exc_info=True)
        return None
