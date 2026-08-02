#!/usr/bin/env bash
# Queue any given URLs into the news queue file (source-code/content/
# news/toadd-news.txt), then archive every URL currently sitting in
# that queue via Save Page Now, one at a time, retrying each once on
# failure (same retry-once policy as a single-URL run). This means the
# batch processed on any given run isn't just the command-line arguments — it's
# whatever's left over from earlier runs too, which is what lets a
# failed URL get picked up again next time without the caller having
# to track it separately.
#
# Before archiving, skips any URL that's already been turned into an
# article in an earlier run: an article's `link_to` is an archive.org
# snapshot URL that embeds the original URL as a trailing substring,
# so a plain substring grep across existing `link_to` fields is enough
# to catch it without re-archiving to compare.
#
# Usage: scripts/archive-urls.sh [url...]
#
# Output (one line per queued URL, in queue order):
#   OK <url> <archived-url>
#   DUP <url> <existing-file>
#   FAIL <url>

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NEWS_DIR="$REPO_ROOT/source-code/content/news"
QUEUE_FILE="$NEWS_DIR/toadd-news.txt"

touch "$QUEUE_FILE"

for url in "$@"; do
    grep -qxF -- "$url" "$QUEUE_FILE" || echo "$url" >> "$QUEUE_FILE"
done

first=1
while IFS= read -r url; do
    [ -z "$url" ] && continue

    match=$(grep -rlF --include="*.md" -- "$url" "$NEWS_DIR" 2>/dev/null | head -1)
    if [ -n "$match" ]; then
        echo "DUP $url ${match#"$REPO_ROOT"/}"
        continue
    fi

    # Space out requests to Save Page Now so a burst of URLs doesn't
    # trip its rate limiting and turn transient throttling into
    # spurious FAILs.
    if [ $first -eq 0 ]; then
        sleep 2
    fi
    first=0

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
done < "$QUEUE_FILE"
