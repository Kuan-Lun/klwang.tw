#!/usr/bin/env bash
# Write a news article markdown file with this repo's fixed TOML
# frontmatter shape. Keeps field order and TOML string-escaping out of
# the caller's hands — the caller only decides field values and the
# destination path (folder/filename are a judgment call made earlier).
#
# Usage:
#   scripts/write-news.sh --title "..." --slug "..." --date "YYYY-MM-DD" \
#       --link-to "https://web.archive.org/web/..." --tags "tag1,tag2" \
#       [--description "..."] <output-path>

set -uo pipefail

title=""
slug=""
date=""
link_to=""
tags=""
description=""
output=""

while [ $# -gt 0 ]; do
    case "$1" in
        --title) title="$2"; shift 2 ;;
        --slug) slug="$2"; shift 2 ;;
        --date) date="$2"; shift 2 ;;
        --link-to) link_to="$2"; shift 2 ;;
        --tags) tags="$2"; shift 2 ;;
        --description) description="$2"; shift 2 ;;
        -*) echo "Unknown flag: $1" >&2; exit 1 ;;
        *) output="$1"; shift ;;
    esac
done

if [ -z "$title" ] || [ -z "$slug" ] || [ -z "$date" ] || [ -z "$link_to" ] || [ -z "$tags" ] || [ -z "$output" ]; then
    echo "Usage: $0 --title T --slug S --date YYYY-MM-DD --link-to URL --tags 'a,b' [--description D] <output-path>" >&2
    exit 1
fi

if [ -e "$output" ]; then
    echo "Refusing to overwrite existing file: $output" >&2
    exit 1
fi

esc() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

mkdir -p "$(dirname "$output")"

{
    echo "+++"
    printf 'title = "%s"\n' "$(esc "$title")"
    if [ -n "$description" ]; then
        printf 'description = "%s"\n' "$(esc "$description")"
    fi
    printf 'slug = "%s"\n' "$(esc "$slug")"
    printf 'date = "%s"\n' "$date"
    echo
    echo "[extra]"
    printf 'link_to = "%s"\n' "$(esc "$link_to")"
    echo
    echo "[taxonomies]"
    IFS=',' read -ra tag_arr <<< "$tags"
    tag_json="["
    first=1
    for t in "${tag_arr[@]}"; do
        t_trimmed=$(printf '%s' "$t" | sed 's/^ *//; s/ *$//')
        if [ $first -eq 0 ]; then tag_json+=", "; fi
        tag_json+="\"$(esc "$t_trimmed")\""
        first=0
    done
    tag_json+="]"
    printf 'news_tags = %s\n' "$tag_json"
    echo "+++"
} > "$output"

echo "Wrote $output" >&2
