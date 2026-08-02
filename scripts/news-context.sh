#!/usr/bin/env bash
# Agent-neutral entry point for the deterministic news context report.
#
# Usage:
#   scripts/news-context.sh
#   scripts/news-context.sh --check-slug <slug>
#   scripts/news-context.sh --all-slugs

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/news-context.py" "$@"
