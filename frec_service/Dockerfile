# Paths in this file are based on the assumption that this file will be used
# in context of the docker-compose.yaml file placed in the parent 
# of this folder.

FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y \
    build-essential \
    cmake \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libboost-all-dev \
    && rm -rf /var/lib/apt/lists/*

COPY frec_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY frec_service/ .

CMD ["python", "run.py"]
