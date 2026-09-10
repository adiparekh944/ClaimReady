# ClaimReady backend: Flask API + perception pipeline.
#
# Build context is this directory, so the vision/ package lives at
# backend/vision/ rather than the repository root — otherwise COPY could not
# reach it. See docs/deployment.md.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Perception mode: FAST, BALANCED or ACCURATE. FAST is the default here
# because the container is CPU-only; every threshold is overridable at runtime
# via CR_VISION_* environment variables.
ENV CR_VISION_MODE=FAST

# GEMINI_API_KEY is intentionally NOT baked in. A previous revision had a real
# key in a commented-out ENV line here; that key is in git history and should
# be rotated. Pass it at run time with `-e GEMINI_API_KEY=...`.

WORKDIR /app

# System libraries.
#
# Runtime only: build-essential, gfortran, git and the -dev headers were
# removed because every Python dependency installs from a prebuilt wheel, so
# nothing is compiled from source. libgl1/libglib2.0-0 remain for
# opencv-python-headless, which still links libGL even though it draws no
# windows. libgomp1 remains for the OpenMP runtime torch requires.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libopenblas0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies, in their own layer so code changes do not reinstall torch.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download model weights at build time so the first request does not wait
# on a download. Both are cached in the image layer.
#   yolo11x-seg.pt  segmentation checkpoint for the image pipeline
#   yolo11l.pt      detection checkpoint for the video tracking path
RUN python -c "from ultralytics import YOLO; YOLO('yolo11x-seg.pt'); YOLO('yolo11l.pt')"

# Pre-download the CLIP encoder used for proposal deduplication and video
# re-identification. Cold-loading it on first request cost roughly 35 s when
# measured locally.
RUN python -c "import open_clip; open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')"

COPY . .

EXPOSE 8080

# geminiserver.py serves /api/analyze-image and /api/analyze-multiple-images,
# which are the routes the frontend calls. Its main() warms up the models
# before binding the port.
CMD ["python", "geminiserver.py"]
