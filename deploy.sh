#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# 0) Check Docker
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found. Please install Docker first."
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: docker compose not available. Please install Docker Compose v2."
  exit 1
fi

# 1) Ensure .env exists
if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    echo "Copying .env from .env.example..."
    cp .env.example .env
    echo "Please edit .env and set SECRET_KEY and OPENVIKING_ROOT_API_KEY before running again."
    exit 1
  else
    echo "ERROR: .env.example not found."
    exit 1
  fi
fi

# 2) Ensure OpenViking config exists (local, not committed)
if [[ ! -f data/openviking/ov.conf ]]; then
  if [[ -f data/openviking/ov.conf.example ]]; then
    echo "Copying OpenViking config from example..."
    mkdir -p data/openviking
    cp data/openviking/ov.conf.example data/openviking/ov.conf
    echo "Please edit data/openviking/ov.conf and set API keys and root_api_key."
    exit 1
  else
    echo "ERROR: data/openviking/ov.conf.example not found."
    exit 1
  fi
fi

# 3) Start services
echo "Starting docker services..."
docker compose up -d --build

# 4) Show status
docker compose ps
