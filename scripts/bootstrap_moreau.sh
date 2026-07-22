#!/usr/bin/env bash
# Idempotent Moreau / public bootstrap for Linux and WSL2.
# Never prints credentials (MOREAU_LICENSE_KEY / extra-index URLs are redacted).
set -euo pipefail

PROFILE="${CONICSHIELD_BOOTSTRAP_PROFILE:-moreau-cpu}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

redact() {
  # stdin -> stdout with common secret patterns removed
  sed -E \
    -e 's#(https?://)[^/@[:space:]]+@#\1<REDACTED>@#g' \
    -e 's#(MOREAU_LICENSE_KEY=)[^[:space:]]+#\1<REDACTED>#g' \
    -e 's#(MOREAU_EXTRA_INDEX_URL=)[^[:space:]]+#\1<REDACTED>#g' \
    -e 's#(MOREAU_PIP_EXTRA_INDEX_URL=)[^[:space:]]+#\1<REDACTED>#g'
}

if ! command -v python >/dev/null 2>&1; then
  echo "python is required in PATH" >&2
  exit 1
fi

PY_VER="$(python - <<'PY'
import sys
print(f"{sys.version_info[0]}.{sys.version_info[1]}")
PY
)"
case "${PY_VER}" in
  3.11|3.12) ;;
  *)
    echo "Unsupported Python ${PY_VER}. Governed builds require 3.11 or 3.12." >&2
    echo "See docs/DEVENV.md and packaging/install_matrix.json." >&2
    exit 1
    ;;
esac

OS_NAME="$(uname -s | tr '[:upper:]' '[:lower:]')"

write_license_if_needed() {
  if [[ -z "${MOREAU_LICENSE_KEY:-}" ]]; then
    if [[ ! -f "${HOME}/.moreau/key" ]]; then
      echo "Set MOREAU_LICENSE_KEY or provide ${HOME}/.moreau/key before continuing." >&2
      exit 1
    fi
    return 0
  fi
  mkdir -p "${HOME}/.moreau"
  # Write without echoing the key.
  printf "%s" "${MOREAU_LICENSE_KEY}" > "${HOME}/.moreau/key"
  chmod 600 "${HOME}/.moreau/key"
  echo "Wrote license file to ~/.moreau/key (contents not printed)."
}

install_public() {
  python -m pip install --upgrade pip
  python -m pip install -e ".[dev,solver-public]" \
    -c packaging/constraints/solver-public.txt
  echo "Public solver profile installed (no CUDA, no vendor Moreau)."
}

install_moreau_cpu() {
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
  write_license_if_needed
  python -m pip install --upgrade pip
  python -m pip install -e ".[dev,solver-moreau-cpu]" \
    --extra-index-url "${MOREAU_EXTRA_INDEX_URL}"
  echo "Deprecated note: prefer -e '.[solver-moreau-cpu]' over legacy '.[solver]'."
}

install_moreau_cuda() {
  if [[ "${OS_NAME}" != "linux" ]]; then
    if [[ "${ALLOW_UNSUPPORTED_MOREAU_OS:-0}" != "1" ]]; then
      echo "Unsupported runtime for vendor Moreau CUDA bootstrap: ${OS_NAME}" >&2
      exit 1
    fi
  fi
  if [[ -z "${MOREAU_EXTRA_INDEX_URL:-}" ]]; then
    echo "MOREAU_EXTRA_INDEX_URL is required (vendor package source)." >&2
    exit 1
  fi
  write_license_if_needed
  python -m pip install --upgrade pip
  python -m pip install -e ".[dev,solver-moreau-cuda]" \
    --extra-index-url "${MOREAU_EXTRA_INDEX_URL}"
  echo "Installed solver-moreau-cuda profile (CUDA extras requested)."
}

case "${PROFILE}" in
  public|solver-public)
    install_public
    ;;
  moreau-cpu|solver-moreau-cpu|moreau)
    install_moreau_cpu
    ;;
  moreau-cuda|solver-moreau-cuda)
    install_moreau_cuda
    ;;
  *)
    echo "Unknown CONICSHIELD_BOOTSTRAP_PROFILE=${PROFILE}" >&2
    echo "Use: public | moreau-cpu | moreau-cuda" >&2
    exit 1
    ;;
esac

# Post-install doctor (never prints secrets).
if python -c "import conicshield" >/dev/null 2>&1; then
  DOCTOR_JSON="$(python -m conicshield.cli solver-doctor --json 2>/dev/null | redact || true)"
  if [[ -n "${DOCTOR_JSON}" ]]; then
    python -c 'import json,sys; d=json.loads(sys.argv[1]); a=(d.get("selected_solver_settings") or {}).get("auto_policy") or {}; print("solver-doctor summary:"); print("  python:", d.get("python_version")); print("  os/arch:", d.get("os_name"), d.get("arch")); print("  AUTO ->", a.get("auto_resolves_to")); print("  commit:", d.get("conicshield_commit"))' "${DOCTOR_JSON}" || true
  fi
fi

if [[ "${PROFILE}" == "public" || "${PROFILE}" == "solver-public" ]]; then
  echo "Public bootstrap succeeded (idempotent)."
  exit 0
fi

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

mod = __import__("moreau")
if not hasattr(mod, "CompiledSolver"):
    raise SystemExit(
        "Installed 'moreau' lacks CompiledSolver (wrong or incomplete package). "
        "Uninstall and reinstall via vendor extra-index with solver-moreau-cpu/cuda."
    )
print("cvxpy.MOREAU is available; CompiledSolver present.")
PY

echo "Vendor Moreau bootstrap succeeded (idempotent)."
