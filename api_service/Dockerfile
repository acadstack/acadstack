# Paths in this file are based on the assumption that this file will be used
# in context of the docker-compose.yaml file placed in the parent 
# of this folder.

# Stage 1: Build the frontend
FROM node:22-alpine AS frontend_builder

ARG OAUTH_CLIENT_ID
ENV OAUTH_CLIENT_ID=${OAUTH_CLIENT_ID}

WORKDIR /frontend
COPY webapp/package*.json ./
RUN npm ci

COPY webapp/ .
RUN npm run build  # outputs to /frontend/dist

# Stage 2: Final runtime image
FROM python:3.13-slim-bookworm
ARG APP_PORT=5300
# Environment setup
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_PORT=${APP_PORT}

WORKDIR /app

# Copy backend source code
COPY api_service/ .

# Install Python dependencies
COPY api_service/requirements.txt api_service/constraints.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt -c constraints.txt

# System libraries WeasyPrint needs to render the PDF reports
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Copy built frontend assets into static folder
COPY --from=frontend_builder /frontend/dist /app/app

# Clean up unnecessary files (optional)
RUN apt-get purge -y --auto-remove && \
    rm -rf /root/.cache

EXPOSE ${APP_PORT}

CMD ["python", "main.py"]
