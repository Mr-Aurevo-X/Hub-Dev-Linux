#!/usr/bin/env bash
# Hub Dev — lanceur local
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"
export WEBKIT_DISABLE_DMABUF_RENDERER="${WEBKIT_DISABLE_DMABUF_RENDERER:-1}"
export WEBKIT_DISABLE_COMPOSITING_MODE="${WEBKIT_DISABLE_COMPOSITING_MODE:-1}"
unset GTK_MODULES GTK3_MODULES
if [[ -z "${GDK_BACKEND:-}" && "${XDG_SESSION_TYPE-}" == "wayland" ]]; then
  export GDK_BACKEND=x11
fi
exec python3 "${ROOT}/main.py" "$@"
