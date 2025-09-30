FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps: none required for runtime; keep slim
WORKDIR /app

# Ensure readline is available for interactive prompts
RUN apt-get update \
    && apt-get install -y --no-install-recommends libreadline8 \
    && rm -rf /var/lib/apt/lists/*

# Copy metadata first to leverage Docker layer caching
COPY pyproject.toml README.md /app/
COPY src /app/src

# Install the package so the `rcdtool` CLI entrypoint is available
RUN pip install --no-cache-dir .

# Use a dedicated working directory for user data (config, session, downloads)
WORKDIR /work

# Default command runs the CLI; pass args after image name
ENTRYPOINT ["rcdtool"]
CMD ["--help"]
