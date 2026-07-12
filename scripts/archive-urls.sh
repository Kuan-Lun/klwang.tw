#!/usr/bin/env bash
# Archive multiple URLs via Save Page Now, one at a time, retrying each
# once on failure (same retry-once policy as a single-URL run). Prints
# one structured line per URL so the caller can tell which succeeded
# and which need to be reported as failed, without any one URL's
# failure stopping the rest of the batch.
#
# Usage: scripts/archive-urls.sh <url> [url...]
#
# Output (one line per URL, in input order):
#   OK <url> <archived-url>
#   FAIL <url>

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <url> [url...]" >&2
    exit 1
fi

for url in "$@"; do
    archived=$("$SCRIPT_DIR/archive-url.sh" "$url" 2>/dev/null)
    if [ -z "$archived" ]; then
        echo "retrying archive for $url..." >&2
        archived=$("$SCRIPT_DIR/archive-url.sh" "$url" 2>/dev/null)
    fi

    if [ -n "$archived" ]; then
        echo "OK $url $archived"
    else
        echo "FAIL $url"
    fi
done
