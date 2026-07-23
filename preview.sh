#!/bin/bash

# Usage:
#   ./preview.sh
#
# Description:
#   Local-only helper to preview the Zola site before committing.
#   Installs zola via Homebrew if missing, then runs `zola serve`
#   against source-code/ so you can eyeball the result in a browser.
#
# Optional environment variables (defaults shown):
#   ZOLA_PREVIEW_INTERFACE   127.0.0.1
#   ZOLA_PREVIEW_PORT        1111
#   ZOLA_PREVIEW_BASE_URL    http://127.0.0.1:1111

set -e # Exit immediately if any command fails

SCRIPT_PATH="$(readlink -f "$0")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"

ZOLA_PREVIEW_INTERFACE="${ZOLA_PREVIEW_INTERFACE:-127.0.0.1}"
ZOLA_PREVIEW_PORT="${ZOLA_PREVIEW_PORT:-1111}"
ZOLA_PREVIEW_BASE_URL="${ZOLA_PREVIEW_BASE_URL:-http://${ZOLA_PREVIEW_INTERFACE}}"

if ! command -v zola >/dev/null 2>&1; then
    echo "zola not found, installing via Homebrew..."
    brew install zola
fi

zola --root "$SCRIPT_DIR/source-code" serve \
    --drafts \
    --interface "$ZOLA_PREVIEW_INTERFACE" \
    --port "$ZOLA_PREVIEW_PORT" \
    --base-url "$ZOLA_PREVIEW_BASE_URL"
