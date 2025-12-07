# TE Evaluation Tool — API Reference (README-API.md)

This file documents the project's HTTP API which provides asynchronous endpoints for running model jobs, mapping FASTA headers, and computing evaluation metrics.

This document is derived from two authoritative sources in the repository:
- OpenAPI specification: `backend/src/config/swagger.yaml` (primary API spec)
- The runtime implementation: `backend/src/controllers/coreController.js` (source of truth for enforced behaviours)

Important: the OpenAPI spec (swagger.yaml) and `coreController` are mostly aligned — but there are a few behaviours the controller enforces unconditionally (server-side overrides). These are called out where relevant.

---

## Overview

Base server and docs (local container):

- Swagger UI: http://localhost:3002/api-docs (served by `backend/server.js`)
- API base path (swagger): `http://localhost:3002/api/v1`

The API design is asynchronous: endpoints accept multipart uploads and return 200 OK immediately when the job is queued. The server processes jobs sequentially in the background and will send notifications (if an email address is present in the request).

---

## Common notes (behaviour implemented by controller)

- File fields use multipart form uploads with specific field names:
  - `fastaFile` — expected for `POST /run` and `POST /map-labels` (single file)
  - `predictionsFile` — expected for `POST /map-labels` and `POST /evaluate` (single file)
- Controller defaults and forced fields (these can differ from OpenAPI defaults):
  - `output` — will be generated on the server if omitted. Directory names used by controller: `run_<timestamp>` (for /run) and `evaluation_<timestamp>` (for /evaluate).
  - **API-enforced**: `clean` (aka cleanTemp) = TRUE (controller sets `args.clean = true`) — temporary files will be cleaned by default for /run.
  - **API-enforced**: `verbose` = TRUE (`args.verbose = true`) — the controller forces verbose mode for jobs queued through the API.
  - **API-enforced**: `autoLabel` is forced TRUE in `coreController.run` (`args.autoLabel = true`). Note — swagger default for `autoLabel` is false; in practice the server overrides this and enables label mapping for API-run jobs.
  - `validateOnly` for `/map-labels` is normalized to a boolean (`'true'` strings are accepted) and when `validateOnly` is true the controller removes `output` to ensure no output is written.

- TERL model handling and quirks:
  - The controller will map `modelFile` short names `DS1..DS5` to the TERL models folder if `model === 'terl'` (path prefix: `CLI/src/models/TERL/Models/DS*`).
  - The `algorithm` parameter is **ignored** for TERL runs (TERL does not use hierarchical `algorithm` — the CLI and controller will not pass it through for `terl`).

- Notification email behaviour:
  - Swagger lists `notificationEmail` as a required property for many endpoints; the controller now rejects requests that do not include `notificationEmail` — the API responds with HTTP 400 and a clear message. When present, the background processor will attempt to send email notifications and, on success, the job queue service may perform additional post-job cleanup (see jobQueueService logic).

---

## /run — start classification (POST, asynchronous)

Purpose: queue a classification job that runs a runner (classifyte, terl, yoro). The request is multipart/form-data and must contain a `fastaFile` upload.

Required (by swagger and enforced by controller):
- `fastaFile` (file) — the FASTA to classify
- `notificationEmail` (string) — the recipient address (controller rejects requests without this field).

Important behaviour enforced by the controller:
- `clean` (temporary cleanup) is forced true — CLI runner will be told to clean temporary files.
- `verbose` is forced true — results and runner output will be verbose.
- `autoLabel` is forced true — the CLI will attempt automatic mapping back to FASTA headers to produce `Actual_Label`.

Common request body fields (swagger + controller usage):
- `model` — `classifyte`, `terl`, or `yoro` (default `classifyte`)
- `modelFile` — runner-specific model pointer (e.g. ClassifyTE_combined.pkl, DS3, or YORO HDF5 path)
- YORO-specific options: `window`, `threads`, `threshold`, `cycles`
- `output` — optional: directory path for outputs; if omitted the server will create `run_<timestamp>` under the configured base results dir
- `skipEvaluation` (boolean), `nodeFile`, `algorithm` (classifyte) — general options

Example curl (run with minimal fields):

```bash
curl -X POST "http://localhost:3002/api/v1/run" \
  -F "notificationEmail=user@example.com" \
  -F "fastaFile=@example.fasta" \
  -F "model=classifyte"
```

Server response (on success):

```json
{ "message": "Classificação enfileirada...", "jobId": "JOB-170...", "status": "QUEUED", "outputDir": "/app/data/results/run_170..." }
```

Notes and gotchas:
- Although the OpenAPI spec sets `autoLabel: false` by default, the controller forces it on for `/run` requests — resulting outputs will attempt label mapping.
- The server forcibly sets `clean:true` and `verbose:true` for jobs queued through the API — this differs from CLI behaviour where `clean` and `verbose` are optional.

---

## /map-labels — attach FASTA labels to predictions (POST, asynchronous)

Purpose: merge FASTA header labels into a predictions CSV or validate FASTA headers without writing an output when `validateOnly` is true.

Request fields:
- `fastaFile` (multipart file) — required
- `predictionsFile` (multipart file) — optional (if missing, the command will only validate headers or act on the UI-provided CSV)
- `validateOnly` (boolean|string) — when true, the controller will not write output files; it sets `args.validateOnly` properly and does not generate an `output` path.
- `treeFile` — optional: path to a hierarchy file (default `src/nodes/tree.txt` set by controller)

Example curl (map + provide predictions):

```bash
curl -X POST "http://localhost:3002/api/v1/map-labels" \
  -F "notificationEmail=user@example.com" \
  -F "fastaFile=@headers.fasta" \
  -F "predictionsFile=@pred.csv"
```

Controller behaviour notes:
- The controller forces `verbose=true` for map-labels jobs.
- If `validateOnly=true` (string or boolean), the controller explicitly removes `args.output` so no results file is written.

---

## /evaluate — compute metrics from predictions (POST, asynchronous)

Purpose: accept a predictions CSV (must include `Actual_Label` and `Predicted label`) and queue a metrics computation job.

Request fields:
- `predictionsFile` (multipart file) — required
- `output` — optional, controller will auto-generate `evaluation_<timestamp>` if omitted
- `hierarchy` — optional, default `src/nodes/tree.txt` set by controller
- `format` — `summary`, `detailed`, or `json`

Example curl (evaluate):

```bash
curl -X POST "http://localhost:3002/api/v1/evaluate" \
  -F "notificationEmail=user@example.com" \
  -F "predictionsFile=@predictions_with_labels.csv" \
  -F "format=detailed"
```

Controller behaviour notes:
- `verbose` is forced to true by the controller for evaluate jobs.
- Output folder is either the user-provided path or `evaluation_<timestamp>` under `BASE_RESULTS_DIR`.

---

## Special / implementation details & differences to watch

- The OpenAPI schema marks `notificationEmail` as required for these endpoints; the controller now enforces this requirement and will return HTTP 400 if the field is missing. The frontend and API users must provide `notificationEmail` for requests to succeed.
- `coreController.run` sets `args.autoLabel = true` which overrides any submitted value — the API always attempts automatic mapping for /run jobs.
- The controller normalizes and maps `modelFile` short names for TERL to the TERL models dir when `model === 'terl'` (e.g. `DS3` -> `CLI/src/models/TERL/Models/DS3`). If a full path is given, it is left as-is.
- The CLI (local usage) and API differ in default flags and strictness; the API enforces clean/verbose/autoLabel as described above. If you need behavior identical to CLI, run CLI commands directly in `/app/CLI` or adjust how the API queues jobs.

---

## Where to look for the implementation

- OpenAPI spec: `backend/src/config/swagger.yaml` (authoritative API contract)
- Controller implementation: `backend/src/controllers/coreController.js` (actual runtime behaviour)
- Job & cleanup behaviour (mailer + job queue): `backend/src/services/jobQueueService.js`, `backend/src/services/mailerService.js`, `backend/src/services/fileService.js`

---

If you want, I can:
- Generate cross-reference excerpts showing exact parameter mapping from swagger → controller → CLI arguments, or
- Add examples that demonstrate the differences between `autoLabel` being true for API runs vs CLI runs, or
- Update swagger.yaml so the defaults match the `coreController` behaviour (e.g., set autoLabel default to true, document that clean and verbose are enforced) and add better inline notes.

Which of those would you like me to do next? (I can do the swagger edits + examples or make the API docs more detailed.)
