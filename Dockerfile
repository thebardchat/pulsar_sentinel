# =============================================================================
# PULSAR SENTINEL - Post-Quantum Cryptography Security Framework
# Multi-stage Docker build with liboqs compiled from source
# Supports amd64 and arm64 architectures
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder - compile liboqs from source
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    libssl-dev \
    ninja-build \
    && rm -rf /var/lib/apt/lists/*

# Build liboqs (C library) from source
RUN git clone --depth 1 --branch main https://github.com/open-quantum-safe/liboqs.git /tmp/liboqs \
    && cd /tmp/liboqs \
    && mkdir build && cd build \
    && cmake -G Ninja \
        -DCMAKE_INSTALL_PREFIX=/usr/local \
        -DBUILD_SHARED_LIBS=ON \
        -DOQS_PERMIT_UNSUPPORTED_ARCHITECTURE=ON \
        -DOQS_BUILD_ONLY_LIB=ON \
        .. \
    && ninja \
    && ninja install \
    && ldconfig

# Install Python dependencies into a virtual env for clean copy
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /tmp/requirements.txt

# Install all requirements except liboqs-python (built separately with C lib)
RUN grep -vi 'liboqs-python' /tmp/requirements.txt > /tmp/requirements-filtered.txt \
    && pip install --no-cache-dir -r /tmp/requirements-filtered.txt

# Install liboqs-python now that the C library is available
RUN pip install --no-cache-dir liboqs-python

# ---------------------------------------------------------------------------
# Stage 2: Runtime - minimal image with compiled artifacts
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled liboqs shared libraries
COPY --from=builder /usr/local/lib/liboqs* /usr/local/lib/
COPY --from=builder /usr/local/include/oqs /usr/local/include/oqs
RUN ldconfig

# Copy Python virtual environment
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN groupadd --gid 1000 pulsar \
    && useradd --uid 1000 --gid pulsar --shell /bin/bash --create-home pulsar

WORKDIR /app

# Copy application code
COPY --chown=pulsar:pulsar src/ /app/src/
COPY --chown=pulsar:pulsar ui/ /app/ui/
COPY --chown=pulsar:pulsar config/ /app/config/

# Create persistent data directories
RUN mkdir -p /app/data/asr /app/logs \
    && chown -R pulsar:pulsar /app/data /app/logs

USER pulsar

WORKDIR /app/src

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
