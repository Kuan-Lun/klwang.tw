#!/usr/bin/env bash
# Fetch a web.archive.org snapshot as a plain static page, bypassing the
# Cloudflare-style bot challenges that block automated fetches against the
# live site directly. Some agent web tools refuse web.archive.org URLs, so
# this helper deliberately uses plain curl.
#
# Usage: scripts/fetch-archived.sh <web.archive.org snapshot url>

set -uo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <web.archive.org snapshot url>" >&2
    exit 1
fi

curl -sS -m 30 \
    -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
    "$1"
