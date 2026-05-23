#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
INSTALL_DIR="${MCP_SKELETON_HOME:-$HOME/.mcp-skeleton}"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$HOME/.local/bin"
if [ "${PYTHON:-}" ]; then
  PYTHON_BIN="$PYTHON"
else
  PYTHON_BIN=""
  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
      then
        PYTHON_BIN="$candidate"
        break
      fi
    fi
  done
fi

echo "MCP-Skeleton macOS installer"
echo ""
echo "Install dir: $INSTALL_DIR"
echo "Command:     $BIN_DIR/mcp-skeleton"
echo ""

if [ -z "$PYTHON_BIN" ] || ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "error: Python 3.10+ was not found. Install Python 3.10+ first, or rerun with PYTHON=/path/to/python3.11 sh install.sh." >&2
  exit 2
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("error: MCP-Skeleton requires Python 3.10+")
PY

mkdir -p "$INSTALL_DIR" "$BIN_DIR"

echo "Creating virtual environment..."
echo "Using Python: $PYTHON_BIN"
"$PYTHON_BIN" -m venv "$VENV_DIR"

echo "Installing MCP-Skeleton..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV_DIR/bin/python" -m pip install "$ROOT_DIR[context-metrics]" >/dev/null

ln -sf "$VENV_DIR/bin/mcp-skeleton" "$BIN_DIR/mcp-skeleton"

echo ""
echo "Installed successfully."
echo ""
echo "Try it now:"
echo "  $BIN_DIR/mcp-skeleton quick --input-dir ."
echo ""
if ! printf '%s' "$PATH" | grep -q "$BIN_DIR"; then
  echo "Note: $BIN_DIR is not currently in PATH."
  echo "Add this to your shell profile:"
  echo "  export PATH=\"$BIN_DIR:\$PATH\""
fi
