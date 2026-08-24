from __future__ import annotations

import unittest

import faiss
import numpy as np

from backend.app.ml.retrieval import GalleryRecord, RetrievalService


class RetrievalGroupingTests(unittest.TestCase):
    def test_search_returns_unique_physical_parts_ranked_by_their_best_view(self) -> None:
        service = RetrievalService()
        service.ready = True
        service.records = [
            GalleryRecord("part-a", "/cad/a-front.png", "front", {"reference": "A"}),
            GalleryRecord("part-a", "/cad/a-iso.png", "iso", {"reference": "A"}),
            GalleryRecord("part-b", "/cad/b-front.png", "front", {"reference": "B"}),
        ]
        service.index = faiss.IndexFlatIP(2)
        service.index.add(np.asarray([[0.5, 0.0], [0.9, 0.0], [0.8, 0.0]], dtype="float32"))
        service.embed_image = lambda _: np.asarray([1.0, 0.0], dtype="float32")  # type: ignore[method-assign]

        result = service.search(object(), top_k=5)

        self.assertEqual([item["part_id"] for item in result["results"]], ["part-a", "part-b"])
        self.assertEqual(result["results"][0]["best_view"], "iso")
        self.assertAlmostEqual(result["results"][0]["similarity"], 0.9, places=6)
        self.assertEqual(len(result["results"][0]["available_views"]), 2)
