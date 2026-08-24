from __future__ import annotations

import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=int(os.getenv("INFERENCE_PORT", "8001")),
        reload=os.getenv("INFERENCE_RELOAD", "false").lower() == "true",
    )
