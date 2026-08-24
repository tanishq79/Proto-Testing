from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

from backend.app.config import EMBEDDINGS_PATH, FAISS_INDEX_PATH, GALLERY_MANIFEST_PATH, MODEL_NAME
from backend.app.ml.preprocessing import preprocess_image

VIEW_ORDER = ("front", "back", "left", "right", "top", "bottom", "iso", "unknown")


class RetrievalInitializationError(RuntimeError):
    """Raised when a validated gallery bundle cannot be loaded safely."""


@dataclass(frozen=True)
class GalleryRecord:
    part_id: str
    image_url: str
    view: str
    metadata: dict[str, Any]


class RetrievalService:
    """Loads the existing DINOv2 gallery once and performs exact part-level similarity search."""

    def __init__(
        self,
        manifest_path: Path = GALLERY_MANIFEST_PATH,
        embeddings_path: Path = EMBEDDINGS_PATH,
        index_path: Path = FAISS_INDEX_PATH,
        model_name: str = MODEL_NAME,
    ) -> None:
        self.manifest_path = manifest_path
        self.embeddings_path = embeddings_path
        self.index_path = index_path
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else ("mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu")
        self.processor: Any | None = None
        self.model: Any | None = None
        self.records: list[GalleryRecord] = []
        self.embeddings: np.ndarray | None = None
        self.index: Any | None = None
        self.ready = False

    def load(self) -> None:
        if self.ready:
            return
        missing = [str(path) for path in (self.manifest_path, self.embeddings_path, self.index_path) if not path.exists()]
        if missing:
            raise RetrievalInitializationError(f"Required retrieval artifacts are missing: {', '.join(missing)}")
        try:
            raw_records = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            self.records = [
                GalleryRecord(
                    part_id=item["part_id"],
                    image_url=item["image_url"],
                    view=item.get("view", "unknown"),
                    metadata={key: value for key, value in item.items() if key not in {"part_id", "image_url", "asset_key", "view"} and value not in (None, "")},
                )
                for item in raw_records
            ]
            self.embeddings = np.load(self.embeddings_path).astype("float32")
            self.index = faiss.read_index(str(self.index_path))
            if len(self.records) != len(self.embeddings) or self.index.ntotal != len(self.records):
                raise RetrievalInitializationError(
                    "The portable manifest, embedding matrix, and FAISS index have incompatible row counts."
                )
            self.processor = AutoImageProcessor.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name).to(self.device).eval()
            self.ready = True
        except RetrievalInitializationError:
            raise
        except Exception as error:  # pragma: no cover - external model/download failures vary by environment
            raise RetrievalInitializationError("The DINOv2 model or retrieval bundle could not be loaded.") from error

    def embed_image(self, image: Image.Image) -> np.ndarray:
        if not self.ready or self.processor is None or self.model is None:
            raise RetrievalInitializationError("The retrieval service is not ready.")
        processed = preprocess_image(image, mode="full")
        with torch.inference_mode():
            batch = self.processor(images=[processed], return_tensors="pt").to(self.device)
            vector = self.model(**batch).last_hidden_state[:, 0, :].cpu().numpy()[0]
        norm = np.linalg.norm(vector)
        if norm <= 0:
            raise RetrievalInitializationError("The model produced an invalid zero-length embedding.")
        return (vector / norm).astype("float32")

    def search(self, image: Image.Image, top_k: int = 5) -> dict[str, Any]:
        if not self.ready or self.index is None:
            raise RetrievalInitializationError("The retrieval service is not ready.")
        query_vector = self.embed_image(image)
        # IndexFlatIP is exact. Querying all images preserves the notebook's max-over-views grouping.
        similarities, identifiers = self.index.search(query_vector.reshape(1, -1), len(self.records))
        best_by_part: dict[str, tuple[float, GalleryRecord]] = {}
        for similarity, identifier in zip(similarities[0], identifiers[0]):
            if identifier < 0:
                continue
            record = self.records[int(identifier)]
            score = float(similarity)
            if record.part_id not in best_by_part or score > best_by_part[record.part_id][0]:
                best_by_part[record.part_id] = (score, record)

        records_by_part: dict[str, list[GalleryRecord]] = defaultdict(list)
        for record in self.records:
            records_by_part[record.part_id].append(record)

        ranked = sorted(best_by_part.values(), key=lambda item: item[0], reverse=True)[: max(1, min(top_k, 5))]
        results: list[dict[str, Any]] = []
        for rank, (score, record) in enumerate(ranked, start=1):
            available_views = [
                {"view": view_record.view, "image_url": view_record.image_url}
                for view_record in sorted(records_by_part[record.part_id], key=lambda item: VIEW_ORDER.index(item.view) if item.view in VIEW_ORDER else len(VIEW_ORDER))
            ]
            results.append(
                {
                    "rank": rank,
                    "part_id": record.part_id,
                    "similarity": score,
                    "similarity_percentage": round(score * 100, 1),
                    "best_view": record.view,
                    "preview_image": record.image_url,
                    "available_views": available_views,
                    "metadata": record.metadata,
                }
            )
        return {
            "model": self.model_name,
            "embedding_dimension": int(query_vector.shape[0]),
            "results": results,
        }
