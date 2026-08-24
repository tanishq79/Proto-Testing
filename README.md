# Component Atlas — Industrial Hardware Visual Retrieval

Component Atlas is a **full-stack local prototype** for finding visually similar industrial parts from a photograph. It preserves the audited notebook’s core methodology: DINOv2 CLS-token embeddings, L2-normalized vectors, exact inner-product search, and **maximum similarity across the rendered views of each physical part**.

> The original notebook remains unchanged in the source repository. The reusable FastAPI modules in `backend/app/` were extracted to support a web workflow without replacing the research implementation.

## What the prototype does

The browser accepts a PNG or JPEG component image, validates it, calls a real FastAPI inference service, and presents the returned **top five physical parts**. Each result is built from actual data: DINOv2 similarity, the highest-scoring CAD view, sparse metadata where available, and the part’s actual rendered views.

| Layer | Responsibility |
|---|---|
| React + TypeScript frontend | Blueprint-style upload flow, camera-capable file input, in-request feedback, results, error states, comparison cards, and multi-view CAD gallery. |
| Express bridge | Keeps the browser on one origin by proxying `/api/health` and `/api/search` to the local FastAPI service. |
| FastAPI service | Loads DINOv2, the processor, portable manifest, NumPy embeddings, and FAISS index once during startup. |
| Retrieval bundle | `backend/data/` stores the existing `dinov2_full.npy`, `gallery.faiss`, and a portable 427-row manifest aligned to both. |
| Managed gallery assets | The rendered CAD gallery is referenced by managed `/manus-storage/...` URLs, not original Mac filesystem paths and not a copied `data/raw` tree in this application. |

## Architecture

```text
Browser image upload
        │
        ▼
React client ─────── POST /api/search ───────► Express proxy
                                                   │
                                                   ▼
                                        FastAPI /api/search
                                                   │
          ┌────────────────────────────────────────┼────────────────────────────────────────┐
          ▼                                        ▼                                        ▼
  image validation                       DINOv2 preprocessing                   normalized CLS embedding
          │                                        │                                        │
          └────────────────────────────────────────┴──────────────► FAISS IndexFlatIP ◄──────┘
                                                                      │
                                                                      ▼
                                                          max score per `part_id`
                                                                      │
                                                                      ▼
                                                       top 5 physical-part results
```

## ML retrieval flow

The service uses the existing notebook behavior as its source of truth.

1. The API accepts PNG/JPEG uploads up to 12 MB and uses Pillow verification plus a 32-pixel minimum dimension check.
2. The reusable pipeline supports the notebook’s optional alpha-aware background removal, object-bound detection, crop, 10% padding, aspect-preserving Lanczos resize to 518×518, slight brightness/contrast normalization, and unsharp-mask enhancement.
3. The current portable service defaults optional `rembg` execution **off**. This retains the notebook’s documented opaque-image fallback and avoids an unbounded segmentation-model download in a small local or managed runtime. Enable it only after installing and validating a compatible `rembg` model bundle.
4. `facebook/dinov2-small` produces a 384-dimensional CLS-token vector. The vector is L2-normalized.
5. FAISS `IndexFlatIP` searches the existing 427 image embeddings exactly. Since vectors are normalized, inner product is cosine similarity.
6. Image matches are grouped by `part_id`; the highest similarity of the part’s views is retained. The top five **distinct physical parts** are returned.

## Local macOS setup

The prototype runs two local processes: the Node web application and FastAPI inference service.

### 1. Prerequisites

Install Node.js 22+, pnpm, Python 3.11+, and an environment able to run PyTorch. Then install dependencies:

```bash
pnpm install
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

The model `facebook/dinov2-small` downloads from Hugging Face at the FastAPI service’s first start unless it is already cached locally.

### 2. Configure the local service

This managed project does **not** commit a literal `.env.example` file. The project platform reserves environment-file management for secure settings, and no application secret is required for the local retrieval flow. The equivalent placeholder-only template is [`config/retrieval-config.template.txt`](config/retrieval-config.template.txt). Use those values in your own untracked local environment file or shell session:

```bash
RETRIEVAL_MODEL_NAME=facebook/dinov2-small
RETRIEVAL_DATA_DIR=backend/data
ENABLE_BACKGROUND_REMOVAL=false
ENABLE_COLOR_CORRECTION=true
ENABLE_ENHANCEMENT=true
MAX_UPLOAD_BYTES=12582912
INFERENCE_PORT=8001
```

Do not add Google OAuth credentials, tokens, database credentials, or other secrets to the frontend or to version control.

### 3. Start the services

In terminal one, start the API:

```bash
ENABLE_BACKGROUND_REMOVAL=false pnpm inference:dev
```

In terminal two, start the web application:

```bash
pnpm dev
```

Open the Node development URL displayed by the command. The client uses `/api/search`, which the Node process forwards to FastAPI at `http://127.0.0.1:8001` by default. Override the target only with server-side `INFERENCE_API_ORIGIN` configuration.

## API reference

| Route | Method | Behavior |
|---|---|---|
| `/api/health` | `GET` | Reports whether the FastAPI service is ready, model identifier, gallery image count, and embedding dimension. |
| `/api/search` | `POST` | Accepts a multipart `file` field containing a PNG/JPEG image and returns actual top-five physical-part matches. |

The search response includes `rank`, `part_id`, raw `similarity`, actual `similarity_percentage`, `best_view`, `preview_image`, all available rendered views, and only metadata present in the portable manifest.

## Tests and validation

Run TypeScript and frontend helper tests:

```bash
pnpm check
pnpm test
```

Run Python preprocessing, grouping, health-handler, and full parity tests against a real query image:

```bash
ENABLE_BACKGROUND_REMOVAL=false \
RETRIEVAL_PARITY_IMAGE="/absolute/path/to/query.png" \
python3 -m unittest discover -s backend/tests -v
```

The committed validation run used the repository’s `real_data/image copy.png` query image. The FAISS-backed service and direct notebook-style normalized-matrix scoring produced the same top five rows:

| Rank | Part ID | Best view | Similarity |
|---:|---|---|---:|
| 1 | `189576496-34-tec_6` | `iso` | 0.810104 |
| 2 | `189576276-34-jb_zq_4321-2006_14` | `front` | 0.363541 |
| 3 | `189576900-114-mini-excavator_yellow` | `right` | 0.313037 |
| 4 | `189576454-34-633-40-m5-16-dsg` | `iso` | 0.270429 |
| 5 | `189576667-114-2m02` | `back` | 0.262868 |

## Security and credential hygiene

The audited source repository contains tracked OAuth-related files and an inactive `_gitignore.txt`. **Do not copy those files into this application.** The application’s `.gitignore` excludes credential and token patterns, local environment files, virtual environments, and generated upload/report paths.

Credential remediation should be completed by the repository owner: revoke or rotate exposed OAuth credentials, create a valid `.gitignore`, remove credentials from the active repository and relevant history through an approved security process, and use a secret manager or server-side environment configuration thereafter. This project deliberately does not read, print, or return credential values.

## Known limitations

The gallery contains rendered CAD-like images while user submissions can be real photographs. This **render-to-photo domain gap** can lower retrieval quality because lighting, backgrounds, occlusions, perspectives, scale, and material appearance differ from the gallery. The reported similarity is a cosine similarity from the current embedding space, not a calibrated probability or an engineering-fit guarantee.

The first implementation keeps the current exact FAISS search and current max-over-views grouping. It does not retrain DINOv2, regenerate gallery embeddings at request time, infer unavailable metadata, or add a STEP/GLB viewer because the audited source contains rendered images rather than browser-ready 3D assets.

The FastAPI + PyTorch runtime is designed as a local prototype. A low-memory serverless deployment may be unsuitable for the model and optional segmentation model without dedicated resource validation.

## Repository layout

```text
backend/
  app/                 FastAPI, preprocessing, DINOv2, FAISS retrieval
  data/                portable manifest + existing embeddings/index
  scripts/             manifest construction, FastAPI runner, parity verification
  tests/               preprocessing, grouping, health, and parity tests
client/
  src/pages/Home.tsx   blueprint-style user interface
  src/lib/             result-display formatting helpers and tests
server/
  inferenceProxy.ts    browser-facing proxy to the local FastAPI service
```
