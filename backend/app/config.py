from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("RETRIEVAL_DATA_DIR", PROJECT_ROOT / "backend" / "data"))
MODEL_NAME = os.getenv("RETRIEVAL_MODEL_NAME", "facebook/dinov2-small")
IMAGE_SIZE = int(os.getenv("RETRIEVAL_IMAGE_SIZE", "518"))
PADDING_RATIO = float(os.getenv("RETRIEVAL_PADDING_RATIO", "0.10"))
ENABLE_BACKGROUND_REMOVAL = os.getenv("ENABLE_BACKGROUND_REMOVAL", "false").lower() == "true"
ENABLE_COLOR_CORRECTION = os.getenv("ENABLE_COLOR_CORRECTION", "true").lower() == "true"
ENABLE_ENHANCEMENT = os.getenv("ENABLE_ENHANCEMENT", "true").lower() == "true"
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(12 * 1024 * 1024)))
GALLERY_MANIFEST_PATH = DATA_DIR / "gallery_manifest.json"
EMBEDDINGS_PATH = DATA_DIR / "dinov2_full.npy"
FAISS_INDEX_PATH = DATA_DIR / "gallery.faiss"
