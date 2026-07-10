#!/usr/bin/env bash
# Submit a URL to web.archive.org's Save Page Now service and print the
# resulting snapshot link, ready to paste into a news article's
# `link_to` field.
#
# Usage: scripts/archive-url.sh <url>

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <url>" >&2
    exit 1
fi

url="$1"

response=$(curl -sS -m 60 -D - -o /dev/null "https://web.archive.org/save/${url}")

location=$(printf '%s' "$response" | grep -i '^location:' | tr -d '\r' | awk '{print $2}')

if [ -z "$location" ]; then
    echo "Failed to archive: no snapshot location returned" >&2
    echo "$response" >&2
    exit 1
fi

echo "$location"
