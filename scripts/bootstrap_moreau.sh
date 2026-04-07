#!/usr/bin/env bash
set -euo pipefail

if ! command -v python >/dev/null 2>&1; then
  echo "python is required in PATH" >&2
  exit 1
fi

OS_NAME="$(uname -s | tr '[:upper:]' '[:lower:]')"
if [[ "${OS_NAME}" != "linux" ]]; then
  if [[ "${ALLOW_UNSUPPORTED_MOREAU_OS:-0}" != "1" ]]; then
    echo "Unsupported runtime for vendor Moreau bootstrap: ${OS_NAME}" >&2
    echo "Use Ubuntu Linux or WSL2 Ubuntu. Set ALLOW_UNSUPPORTED_MOREAU_OS=1 to override." >&2
    exit 1
  fi
fi

if [[ -z "${MOREAU_EXTRA_INDEX_URL:-}" ]]; then
  echo "MOREAU_EXTRA_INDEX_URL is required (vendor package source)." >&2
  exit 1
fi

if [[ -z "${MOREAU_LICENSE_KEY:-}" ]]; then
  if [[ ! -f "${HOME}/.moreau/key" ]]; then
    echo "Set MOREAU_LICENSE_KEY or provide ${HOME}/.moreau/key before continuing." >&2
    exit 1
  fi
else
  mkdir -p "${HOME}/.moreau"
  printf "%s" "${MOREAU_LICENSE_KEY}" > "${HOME}/.moreau/key"
  chmod 600 "${HOME}/.moreau/key"
fi

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pip install "moreau[cuda]" --extra-index-url "${MOREAU_EXTRA_INDEX_URL}"

python -m moreau check
python - <<'PY'
import importlib.util
import sys

try:
    import cvxpy as cp
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"cvxpy import failed: {exc}") from exc

if not hasattr(cp, "MOREAU"):
    raise SystemExit("cvxpy.MOREAU is not registered; vendor installation incomplete.")

print("cvxpy.MOREAU is available.")
PY

echo "Vendor Moreau bootstrap succeeded."
