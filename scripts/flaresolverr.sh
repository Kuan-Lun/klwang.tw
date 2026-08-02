#!/usr/bin/env bash
# Manage a local FlareSolverr container and fetch pages through it.
#
# FlareSolverr runs a real headless browser to clear Cloudflare-style
# "Just a moment..." challenges that block plain curl or agent web tools.
# It's meant to be ephemeral here: start it right before you need it,
# stop it right after — don't leave a browser-in-a-box idling.
#
# Usage:
#   scripts/flaresolverr.sh start          # start the container, wait until ready
#   scripts/flaresolverr.sh stop           # stop + remove the container
#   scripts/flaresolverr.sh status         # print "running" or "stopped"
#   scripts/flaresolverr.sh fetch <url>    # start if needed, print rendered HTML to stdout
#
# Reads FLARESOLVERR_URL (default http://localhost:8191/v1) and
# FLARESOLVERR_PORT (default 8191) from the environment.

set -uo pipefail

CONTAINER_NAME="flaresolverr"
IMAGE="ghcr.io/flaresolverr/flaresolverr:latest"
API_URL="${FLARESOLVERR_URL:-http://localhost:8191/v1}"
PORT="${FLARESOLVERR_PORT:-8191}"

is_running() {
    docker ps --filter "name=^/${CONTAINER_NAME}\$" --filter "status=running" -q | grep -q .
}

cmd_start() {
    if is_running; then
        echo "flaresolverr already running" >&2
        return 0
    fi

    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
    if ! docker run -d --name "$CONTAINER_NAME" -p "${PORT}:8191" "$IMAGE" >/dev/null; then
        echo "failed to start flaresolverr container" >&2
        return 1
    fi

    echo "waiting for flaresolverr to become ready..." >&2
    for _ in $(seq 1 30); do
        if curl -sS -m 2 -o /dev/null "$API_URL" 2>/dev/null; then
            echo "flaresolverr ready at $API_URL" >&2
            return 0
        fi
        sleep 1
    done

    echo "flaresolverr did not become ready in time" >&2
    return 1
}

cmd_stop() {
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
    echo "flaresolverr stopped" >&2
}

cmd_status() {
    if is_running; then
        echo "running"
    else
        echo "stopped"
    fi
}

cmd_fetch() {
    local target="$1"

    if ! is_running; then
        cmd_start || return 1
    fi

    local payload
    payload=$(python3 -c 'import json,sys; print(json.dumps({"cmd":"request.get","url":sys.argv[1],"maxTimeout":60000}))' "$target")

    curl -sS -m 90 -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "$payload" \
    | python3 -c '
import json, sys
data = json.load(sys.stdin)
if data.get("status") != "ok":
    print(data.get("message", "flaresolverr request failed"), file=sys.stderr)
    sys.exit(1)
print(data["solution"]["response"])
'
}

case "${1:-}" in
    start)  cmd_start ;;
    stop)   cmd_stop ;;
    status) cmd_status ;;
    fetch)
        if [ $# -ne 2 ]; then
            echo "Usage: $0 fetch <url>" >&2
            exit 1
        fi
        cmd_fetch "$2"
        ;;
    *)
        echo "Usage: $0 {start|stop|status|fetch <url>}" >&2
        exit 1
        ;;
esac
