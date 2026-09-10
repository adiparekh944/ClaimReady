# Deployment audit and entrypoint reconciliation

## The problem found during the audit

Three deployment descriptors disagreed about what the backend is.

| Descriptor | Claimed entrypoint | Port |
| --- | --- | --- |
| `backend/Dockerfile` | `python geminiserver.py` | 8080 |
| `backend/docker-compose.yml` | image default (`geminiserver.py`) | 8080 |
| `render.yaml` | `cd backend && python api.py` | 8000 |

`render.yaml` also set `dockerfilePath: ./Dockerfile`, and **no Dockerfile
exists at the repository root** — only `backend/Dockerfile` and
`frontend/Dockerfile`.

## Which one is correct

`geminiserver.py`. The evidence is the frontend:

- `frontend/src/app/upload/page.tsx`
- `frontend/src/app/test/page.tsx`
- `frontend/src/app/debug/page.tsx`

all call `${NEXT_PUBLIC_BACKEND_URL}/api/analyze-image` and
`/api/analyze-multiple-images`. Those routes exist **only** in
`geminiserver.py`. `api.py` serves an entirely different, job-based API
(`/api/create-job`, `/api/process-video`, `/api/upload-and-process`) that no
frontend code path invokes.

The failure was silent because **both servers expose `/health`**. A Render
deployment running `api.py` would pass its health check indefinitely while
serving an API the frontend never calls, so the misconfiguration produced a
healthy-looking service and 404s in the browser rather than a failed deploy.

## What was changed

`render.yaml` now points at `backend/Dockerfile` with `dockerContext: ./backend`,
and its `startCommand` was **removed** rather than corrected. The image's own
`CMD` is already right, so deleting the override leaves exactly one definition
of how the service starts instead of two that can drift apart again. `PORT` was
aligned to 8080 to match `EXPOSE`.

This is a fix to a descriptor that could not have been working — the referenced
Dockerfile path does not exist, so a Render deploy from this file would fail at
build. It does not change the behaviour of the Docker or compose paths, which
were already correct.

## Why `vision/` lives under `backend/`

The Docker build context is `backend/`:

- `backend/docker-compose.yml` uses `build: .` from within `backend/`
- `backend/push-to-ecr.sh` runs `docker build -t ... .` from `backend/`

`COPY` cannot reach outside its build context, so a package at the repository
root would never enter the image. Placing it at `backend/vision/` keeps the
existing build working unchanged. The alternative — moving the context to the
repository root — would have meant editing the Dockerfile, both compose files
and the ECR script, i.e. changing a working deployment to satisfy a directory
preference.

Tooling outside the container (`benchmarks/`, `tests/`) adds `backend/` to
`sys.path`, so `import vision` works from the repository root.

## Secrets found in the repository

The audit found committed credentials in seven places. **All are in git history
and this change cannot un-leak them; they need rotating.**

| Location | Credential | Status |
| --- | --- | --- |
| `backend/geminiserver.py` | Gemini API key as an `os.environ.get` default | removed; server now fails at startup if unset |
| `backend/Dockerfile` | Gemini API key in a commented-out `ENV` | removed |
| `backend/test_gemini.py` | Gemini API key, hardcoded | removed; read from environment |
| `backend/app.py` | Supabase **service_role** key, hardcoded | removed; read from environment |
| `backend/supaDB.py` | same **service_role** key | removed; read from environment |
| `backend/FileUploader.py` | same **service_role** key | removed; read from environment |
| `backend/InventoryUploader.py` | same **service_role** key | removed; read from environment |

The same Supabase `service_role` key was duplicated across four files, so
rotating it requires no code change now that all four read the environment.

The Supabase key is the serious one: a `service_role` key bypasses row-level
security, so anyone with it has full read/write access to every user's data.

Rotate all three, then set them in the environment:

```bash
GEMINI_API_KEY=...
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_KEY=...
```

`.gitignore` already excludes `.env*`.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | *(required)* | Item identification and pricing |
| `PORT` | `8080` | Listen port |
| `FLASK_DEBUG` | unset | Enables the reloader; warmup is skipped in the parent process |
| `CR_VISION_MODE` | `FAST` in Docker, `BALANCED` in code | `FAST`, `BALANCED` or `ACCURATE` |
| `YOLO_MODEL_PATH` | `yolo11x-seg.pt` | Image-pipeline weights |
| `VIDEO_MODEL_PATH` | `yolo11l.pt` | Video-tracking weights |
| `VIDEO_TARGET_FPS` | `20` | Video frame sampling rate |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | *(required by `api.py`)* | Legacy job path only |
| `CR_VISION_*` | see `vision/config.py` | Overrides any single perception threshold |

Every field on `VisionConfig` is overridable with a `CR_VISION_` prefix, so
production can be retuned without redeploying code. Examples:

```bash
CR_VISION_MODE=BALANCED
CR_VISION_MAX_PROPOSALS=200
CR_VISION_EMBEDDING_SIMILARITY_THRESHOLD=0.94
CR_VISION_SCALES="640 960"
```

`GET /api/vision-config` returns the resolved configuration, so the active
settings of a running instance can be confirmed rather than inferred.

## Mode choice and container sizing

`FAST` is the container default because the Render free tier and a plain
`docker run` are CPU-only. `BALANCED` adds a second inference scale and a CLIP
forward pass over every surviving proposal; `ACCURATE` adds a third scale plus
a tiled pass whose cost grows with tile count. On CPU those are appropriate for
batch work, not for a user waiting on an upload.

Set `CR_VISION_MODE=BALANCED` when running on a GPU instance or when latency is
not user-facing. See `docs/computer_vision_pipeline.md` for the measured
per-stage latency breakdown.

## A note on gunicorn

`gunicorn` is in `requirements.txt` but the image runs the Flask development
server. Switching to gunicorn would be a genuine improvement, but each worker
process loads its own copy of YOLO11-x-seg and CLIP, so worker count has to be
chosen against container memory rather than CPU count. That sizing has not been
measured here, so the entrypoint was left as-is rather than changed on a guess.
