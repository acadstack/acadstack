# Paths in this file are based on the assumption that this file will be used
# in context of the docker-compose.yaml file placed in the parent
# of this folder.

# Stage 1: compile dlib (used by face_recognition) into wheels
FROM python:3.13-slim AS builder

RUN apt-get update && \
    apt-get install -y \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

COPY frec_service/requirements.txt .
RUN pip wheel --no-cache-dir -r requirements.txt -w /wheels

# Stage 2: runtime image, without the compiler toolchain
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY frec_service/requirements.txt .
RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels \
    pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt

COPY frec_service/ .

CMD ["python", "run.py"]
