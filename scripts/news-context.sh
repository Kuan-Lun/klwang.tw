#!/usr/bin/env bash
# Print the repo lookups needed to pick a slug/tag/folder for a new news
# article, in one shot instead of three separate grep/ls calls.
#
# Usage: scripts/news-context.sh

set -uo pipefail

NEWS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/source-code/content/news"

echo "=== existing slugs ==="
grep -rh '^slug' "$NEWS_DIR" --include="*.md"

echo
echo "=== existing news_tags ==="
grep -rh '^news_tags' "$NEWS_DIR" --include="*.md"

echo
echo "=== category folders ==="
ls "$NEWS_DIR"
