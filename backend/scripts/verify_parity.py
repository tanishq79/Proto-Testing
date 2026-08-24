from __future__ import annotations

import argparse
import json

import numpy as np

from backend.app.ml.preprocessing import validate_image_bytes
from backend.app.ml.retrieval import RetrievalService


def direct_notebook_style_ranking(service: RetrievalService, vector: np.ndarray, top_k: int) -> list[dict[str, object]]:
    assert service.embeddings is not None
    scores = service.embeddings @ vector
    best: dict[str, tuple[float, int]] = {}
    for row_id, score in enumerate(scores):
        part_id = service.records[row_id].part_id
        if part_id not in best or float(score) > best[part_id][0]:
            best[part_id] = (float(score), row_id)
    return [
        {
            "part_id": service.records[row_id].part_id,
            "best_view": service.records[row_id].view,
            "similarity": round(score, 6),
        }
        for score, row_id in sorted(best.values(), reverse=True)[:top_k]
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify FastAPI result parity with the notebook's direct normalized-vector scoring.")
    parser.add_argument("image")
    args = parser.parse_args()

    service = RetrievalService()
    service.load()
    image, _ = validate_image_bytes(open(args.image, "rb").read())
    query = service.embed_image(image)
    api_style = service.search(image, top_k=5)["results"]
    direct = direct_notebook_style_ranking(service, query, top_k=5)
    normalized_api = [
        {"part_id": row["part_id"], "best_view": row["best_view"], "similarity": round(float(row["similarity"]), 6)}
        for row in api_style
    ]
    output = {"match": normalized_api == direct, "api_style": normalized_api, "notebook_style_direct": direct}
    print(json.dumps(output, indent=2))
    if not output["match"]:
        raise SystemExit("Parity check failed: FAISS-backed and direct notebook-style rankings differ.")


if __name__ == "__main__":
    main()
