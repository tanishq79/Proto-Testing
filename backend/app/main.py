from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import MAX_UPLOAD_BYTES
from backend.app.ml.preprocessing import ImageValidationError, validate_image_bytes
from backend.app.ml.retrieval import RetrievalInitializationError, RetrievalService

service = RetrievalService()


@asynccontextmanager
async def lifespan(_: FastAPI):
    service.load()
    yield


app = FastAPI(
    title="Industrial Hardware Visual Retrieval API",
    version="0.1.0",
    description="Real DINOv2 and FAISS part-level retrieval extracted from the validated notebook workflow.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, object]:
    return {
        "status": "ready" if service.ready else "starting",
        "model": service.model_name,
        "gallery_images": len(service.records),
        "embedding_dimension": int(service.embeddings.shape[1]) if service.embeddings is not None else None,
    }


@app.post("/api/search")
async def search(file: UploadFile = File(...)) -> dict[str, object]:
    if file.content_type not in {"image/png", "image/jpeg"}:
        raise HTTPException(status_code=415, detail="Please upload a PNG or JPEG image.")
    payload = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The image exceeds the 12 MB upload limit.")
    try:
        image, validation = validate_image_bytes(payload)
        result = service.search(image, top_k=5)
        return {"query": validation.__dict__, **result}
    except ImageValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RetrievalInitializationError as error:
        raise HTTPException(status_code=503, detail="The retrieval service is unavailable. Please try again shortly.") from error
    except Exception as error:  # pragma: no cover - protects browser users from an unhandled inference failure
        raise HTTPException(status_code=500, detail="The image could not be analyzed. Please try a different PNG or JPEG image.") from error
