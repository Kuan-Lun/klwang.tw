#!/bin/bash

# Usage:
#   ./update-apollo.sh
#
# Update Apollo to the latest commit on the branch configured in .gitmodules.
# Review and commit the resulting submodule pointer change in this repository
# to share the updated theme version with other clones.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

git -C "$SCRIPT_DIR" submodule update --init --remote --recursive -- source-code/themes/apollo
git -C "$SCRIPT_DIR/source-code/themes/apollo" log -1 --format='Apollo: %h %s'
