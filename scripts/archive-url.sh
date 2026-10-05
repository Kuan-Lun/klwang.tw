#!/usr/bin/env bash
# Submit a URL to web.archive.org's Save Page Now service and print the
# resulting snapshot link, ready to paste into a news article's
# `link_to` field.
#
# Usage: scripts/archive-url.sh <url>

set -uo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <url>" >&2
    exit 1
fi

url="$1"

# Save Page Now is synchronous server-side: archive.org holds the
# connection open until the capture finishes, which can take well over a
# minute for heavier pages. A long timeout is needed so curl doesn't give
# up before the response arrives.
response=$(curl -sS -m 180 -D - -o /dev/null "https://web.archive.org/save/${url}")
curl_status=$?

if [ $curl_status -eq 0 ]; then
    location=$(printf '%s' "$response" | grep -i '^location:' | tr -d '\r' | awk '{print $2}')
    if [ -n "$location" ]; then
        echo "$location"
        exit 0
    fi
fi

# curl failed or returned no redirect (e.g. client-side timeout, or the
# HTTP 500 Save Page Now returns to anonymous clients). The capture job
# runs independently on archive.org's end, so it may have actually
# finished — look the snapshot up before declaring failure.
echo "Save request did not return a snapshot directly; checking availability..." >&2
sleep 5

# The "latest snapshot" redirect is the cheapest lookup and is not subject
# to the Availability API's rate limit.
latest=$(curl -sS -m 30 -o /dev/null -w '%{redirect_url}' "https://web.archive.org/web/2/${url}" 2>/dev/null)
case "$latest" in
    https://web.archive.org/web/[0-9]*)
        echo "$latest"
        exit 0
        ;;
esac

available=$(curl -sS -m 20 "https://archive.org/wayback/available?url=${url}")
snapshot=$(printf '%s' "$available" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    print(data["archived_snapshots"]["closest"]["url"])
except (json.JSONDecodeError, KeyError):
    pass
')

if [ -n "$snapshot" ]; then
    echo "$snapshot"
    exit 0
fi

echo "Failed to archive: no snapshot found" >&2
exit 1
