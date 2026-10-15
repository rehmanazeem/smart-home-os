#!/usr/bin/env bash
# Minimal script to create a virtualenv and install requirements
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$ROOT_DIR/requirements.txt"

echo "Virtualenv created at $VENV_DIR. Activate with: source $VENV_DIR/bin/activate"
