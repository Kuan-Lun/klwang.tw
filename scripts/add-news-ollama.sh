#!/usr/bin/env bash
# One-shot add-news runner backed by a local Ollama model (no coding agent).
#
# Usage:
#   scripts/add-news-ollama.sh [options] [url ...]
#   scripts/add-news-ollama.sh --help
#
# Archives the URLs, reads each article, asks the local model for the
# metadata, writes the news entries, updates the queue, prints the bucketed
# report, and unloads the model when done.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/add_news_ollama.py" "$@"
