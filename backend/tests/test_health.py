from __future__ import annotations

import unittest

import numpy as np
from fastapi.testclient import TestClient

from backend.app.main import app, service


class HealthEndpointTests(unittest.TestCase):
    def test_health_reports_the_loaded_service_contract(self) -> None:
        original_load = service.load
        original_ready = service.ready
        original_records = service.records
        original_embeddings = service.embeddings
        try:
            def load_stub() -> None:
                service.ready = True
                service.records = [object(), object()]
                service.embeddings = np.zeros((2, 384), dtype="float32")

            service.load = load_stub  # type: ignore[method-assign]
            with TestClient(app) as client:
                response = client.get("/api/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "ready")
            self.assertEqual(response.json()["gallery_images"], 2)
            self.assertEqual(response.json()["embedding_dimension"], 384)
        finally:
            service.load = original_load  # type: ignore[method-assign]
            service.ready = original_ready
            service.records = original_records
            service.embeddings = original_embeddings
