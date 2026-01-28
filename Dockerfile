# ===============================
# 1️⃣ Build Client
# ===============================
FROM node:20-alpine AS frontend-builder

WORKDIR /client
COPY client/package*.json ./
RUN npm ci
COPY client/ .
RUN npm run build

# ===============================
# 2️⃣ Python Server builder stage
# ===============================
FROM python:3.11.13-slim-bookworm AS server-builder

# Install build deps (only for packages needing compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary
COPY --from=ghcr.io/astral-sh/uv:0.7.20 /uv /uvx /bin/

WORKDIR /pkg

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Install dependencies into container’s Python env
RUN uv sync --frozen --no-cache --python=/usr/local/bin/python3.11


# ===============================
# 3️⃣ Runtime stage
# ===============================
FROM python:3.11.13-slim-bookworm AS runtime

# Runtime deps only (drop build-essential etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary
COPY --from=ghcr.io/astral-sh/uv:0.7.20 /uv /uvx /bin/

WORKDIR /pkg

# Copy **everything under /usr/local/** from builder
COPY --from=server-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=server-builder /usr/local/bin /usr/local/bin

COPY --from=frontend-builder /client/dist ./client/dist

COPY pyproject.toml uv.lock ./
# Copy backend code
COPY artifacts/ ./artifacts
COPY main.py ./
COPY internal/ ./internal
COPY server/ ./server

EXPOSE 8000


CMD ["uv", "run", "python", "main.py"]

