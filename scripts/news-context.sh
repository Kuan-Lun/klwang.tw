#!/usr/bin/env bash
# Print the repo lookups needed to pick a slug/tag/folder for a new news
# article in one shot.
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
echo "=== category folders (tag -> relative path) ==="
while IFS= read -r -d '' index_file; do
    # Transparent Zola sections are this repo's tag-backed categories.
    # Non-transparent nested sections are editorial groupings rather than
    # folders whose name must also be an article tag.
    if grep -Eq '^transparent[[:space:]]*=[[:space:]]*true([[:space:]]*)$' "$index_file"; then
        folder=${index_file%/_index.md}
        printf '%s -> %s\n' "${folder##*/}" "${folder#"$NEWS_DIR"/}"
    fi
done < <(find "$NEWS_DIR" -type f -name '_index.md' -print0) | sort
