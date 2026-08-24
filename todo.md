# Project TODO

- [x] Preserve the audited source notebook and original ML prototype without modification.
- [x] Document a portable gallery-asset mapping that removes machine-specific paths while retaining current manifest/index row alignment.
- [x] Extract the notebook’s validated image validation and full preprocessing behavior into reusable Python inference modules.
- [x] Extract DINOv2 CLS-token embedding, L2 normalization, vector scoring, and max-per-part aggregation into reusable Python modules.
- [x] Add a FastAPI service that loads the model, processor, manifest, embedding matrix, and FAISS index once at startup.
- [x] Implement real `GET /api/health` and `POST /api/search` endpoints with safe upload validation and no fabricated response data.
- [x] Return real top-five physical-part retrieval results with similarity values, metadata, best view, preview, and available rendered views.
- [x] Verify managed asset delivery for committed CAD-render images without committing or duplicating the source dataset inside the application project.
- [x] Add automated backend coverage for `GET /api/health` and package the notebook-parity verification into the repeatable test workflow.
- [x] Build a responsive royal-blue blueprint-style frontend with image drop, file browse, supported-device camera capture, preview, replace/remove controls, and the exact `Find My Part` action.
- [x] Add live analysis feedback, API loading behavior, graceful error states, and a real result-detail multi-view CAD gallery.
- [x] Add an approved non-secret local configuration-template artifact, correct secret exclusions, and security documentation without exposing credential contents.
- [x] Write macOS/local setup, architecture, ML flow, test, security-rotation, and domain-gap documentation.
- [x] Validate backend startup, live search with a repository query image, result parity, error handling, desktop rendering, and mobile rendering.
- [x] Commit the completed Component Atlas prototype and push it to the connected GitHub repository.
