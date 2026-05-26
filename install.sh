#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
INSTALL_DIR="${MCP_SKELETON_HOME:-$HOME/.mcp-skeleton}"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$HOME/.local/bin"
COMMAND_PATH="$BIN_DIR/mcp-skeleton"
MARKER_FILE="$INSTALL_DIR/.mcp-skeleton-install"
MODE="install"
SETUP_SHELL=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --update)
      MODE="update"
      ;;
    --uninstall)
      MODE="uninstall"
      ;;
    --setup-shell)
      SETUP_SHELL=1
      ;;
    -h|--help)
      echo "MCP-Skeleton macOS installer"
      echo ""
      echo "Usage:"
      echo "  sh install.sh                 install MCP-Skeleton"
      echo "  sh install.sh --setup-shell   install and add ~/.local/bin to ~/.zshrc for future terminals"
      echo "  sh install.sh --update        refresh the installed command from this checkout"
      echo "  sh install.sh --uninstall     remove the installed command and managed venv"
      exit 0
      ;;
    *)
      echo "error: unknown installer option: $1" >&2
      echo "try: sh install.sh --help" >&2
      exit 2
      ;;
  esac
  shift
done

if [ "$MODE" = "uninstall" ]; then
  echo "MCP-Skeleton uninstaller"
  echo ""
  echo "Command:     $COMMAND_PATH"
  echo "Install dir: $INSTALL_DIR"
  echo ""
  if [ -L "$COMMAND_PATH" ] || [ -f "$COMMAND_PATH" ]; then
    rm -f "$COMMAND_PATH"
    echo "Removed command: $COMMAND_PATH"
  else
    echo "Command already absent: $COMMAND_PATH"
  fi
  if [ -f "$MARKER_FILE" ]; then
    rm -rf "$INSTALL_DIR"
    echo "Removed managed install dir: $INSTALL_DIR"
  elif [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/pyvenv.cfg" ]; then
    rm -rf "$VENV_DIR"
    rmdir "$INSTALL_DIR" 2>/dev/null || true
    echo "Removed managed virtual environment: $VENV_DIR"
  else
    echo "Install dir was not removed because it is not marked as MCP-Skeleton-managed."
  fi
  echo ""
  echo "Uninstalled successfully."
  exit 0
fi

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

if [ "$MODE" = "update" ]; then
  echo "MCP-Skeleton macOS updater"
else
  echo "MCP-Skeleton macOS installer"
fi
echo ""
echo "Install dir: $INSTALL_DIR"
echo "Command:     $COMMAND_PATH"
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

if [ "$MODE" = "update" ] && [ -d "$VENV_DIR" ]; then
  echo "Refreshing virtual environment..."
  rm -rf "$VENV_DIR"
else
  echo "Creating virtual environment..."
fi
echo "Using Python: $PYTHON_BIN"
"$PYTHON_BIN" -m venv "$VENV_DIR"

if [ "$MODE" = "update" ]; then
  echo "Updating MCP-Skeleton..."
else
  echo "Installing MCP-Skeleton..."
fi
"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV_DIR/bin/python" -m pip install "$ROOT_DIR[context-metrics]" >/dev/null

printf '%s\n' "managed-by=mcp-skeleton" "source=$ROOT_DIR" > "$MARKER_FILE"
ln -sf "$VENV_DIR/bin/mcp-skeleton" "$COMMAND_PATH"

SHELL_PROFILE="$HOME/.zshrc"
SHELL_PROFILE_STATUS="not requested"
if [ "$SETUP_SHELL" = "1" ]; then
  mkdir -p "$(dirname "$SHELL_PROFILE")"
  touch "$SHELL_PROFILE"
  if grep -q "mcp-skeleton PATH" "$SHELL_PROFILE"; then
    SHELL_PROFILE_STATUS="already configured"
  else
    {
      echo ""
      echo "# >>> mcp-skeleton PATH >>>"
      echo "export PATH=\"$BIN_DIR:\$PATH\""
      echo "# <<< mcp-skeleton PATH <<<"
    } >> "$SHELL_PROFILE"
    SHELL_PROFILE_STATUS="updated"
  fi
  PATH="$BIN_DIR:$PATH"
  export PATH
fi

echo ""
if [ "$MODE" = "update" ]; then
  echo "Updated successfully."
else
  echo "Installed successfully."
fi
echo ""
echo "MCP-Skeleton Install Ready"
echo ""
if "$COMMAND_PATH" version >/dev/null 2>&1; then
  echo "Command check: OK"
else
  echo "Command check: unable to run $COMMAND_PATH version"
fi
if command -v mcp-skeleton >/dev/null 2>&1; then
  echo "PATH status: ready - mcp-skeleton is available on PATH"
  HANDOFF_COMMAND="mcp-skeleton handoff"
  QUICK_COMMAND="mcp-skeleton quick"
  VERSION_COMMAND="mcp-skeleton version"
else
  echo "PATH status: needs shell setup - $BIN_DIR is not currently on PATH"
  HANDOFF_COMMAND="$COMMAND_PATH handoff"
  QUICK_COMMAND="$COMMAND_PATH quick"
  VERSION_COMMAND="$COMMAND_PATH version"
fi
echo "Shell profile: $SHELL_PROFILE_STATUS"
if [ "$SETUP_SHELL" = "1" ]; then
  echo "Shell profile file: $SHELL_PROFILE"
  echo "Restart your terminal or run: export PATH=\"$BIN_DIR:\$PATH\""
fi
echo ""
echo "Copy/paste next:"
echo "  $HANDOFF_COMMAND"
echo ""
echo "Optional full bundle command:"
echo "  $QUICK_COMMAND"
echo ""
echo "First run self-check:"
echo "  $VERSION_COMMAND"
echo "  $COMMAND_PATH doctor"
echo ""
echo "Self-check command:"
echo "  $VERSION_COMMAND"
echo ""
echo "If command is not found later:"
echo "  Restart your terminal, or run:"
echo "    export PATH=\"$BIN_DIR:\$PATH\""
echo "PATH fix command:"
echo "  sh install.sh --setup-shell"
echo ""
echo "Useful checks:"
echo "  $VERSION_COMMAND"
echo "  $COMMAND_PATH doctor"
echo ""
if ! printf '%s' "$PATH" | grep -q "$BIN_DIR"; then
  echo "Note: $BIN_DIR is not currently in PATH."
  echo "One-command future shell setup:"
  echo "  sh install.sh --setup-shell"
  echo "Add this to your shell profile:"
  echo "  export PATH=\"$BIN_DIR:\$PATH\""
fi
