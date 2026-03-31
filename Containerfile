# StakeForge — reproducible CLI image for `task verify` and CI-style checks.
# Build: podman build -t localhost/stakeforge:dev -f Containerfile .

FROM docker.io/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STAKEFORGE_DOLT=off

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY examples ./examples
COPY docs ./docs
COPY spec ./spec
COPY why.md ./

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

ENTRYPOINT ["stakeforge"]
CMD ["--help"]
