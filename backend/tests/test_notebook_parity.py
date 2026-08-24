from __future__ import annotations

import os
import unittest
from pathlib import Path

from backend.app.ml.preprocessing import validate_image_bytes
from backend.app.ml.retrieval import RetrievalService


class NotebookParityTests(unittest.TestCase):
    @unittest.skipUnless(os.getenv("RETRIEVAL_PARITY_IMAGE"), "Set RETRIEVAL_PARITY_IMAGE to a real PNG or JPEG query image.")
    def test_faiss_ranking_matches_notebook_style_direct_vector_scoring(self) -> None:
        service = RetrievalService()
        service.load()
        image_path = os.environ["RETRIEVAL_PARITY_IMAGE"]
        image, _ = validate_image_bytes(Path(image_path).read_bytes())
        query_vector = service.embed_image(image)
        assert service.embeddings is not None

        direct_scores = service.embeddings @ query_vector
        best_rows: dict[str, tuple[float, int]] = {}
        for row_id, score in enumerate(direct_scores):
            part_id = service.records[row_id].part_id
            if part_id not in best_rows or float(score) > best_rows[part_id][0]:
                best_rows[part_id] = (float(score), row_id)
        expected = [
            (service.records[row_id].part_id, service.records[row_id].view, round(score, 6))
            for score, row_id in sorted(best_rows.values(), reverse=True)[:5]
        ]

        actual = [
            (item["part_id"], item["best_view"], round(float(item["similarity"]), 6))
            for item in service.search(image, top_k=5)["results"]
        ]
        self.assertEqual(actual, expected)
