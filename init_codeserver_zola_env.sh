#!/bin/bash

# Usage:
#   git clone --recurse-submodules https://github.com/Kuan-Lun/klwang.tw.git klwang.tw.clone
#   cd klwang.tw.clone && ./init_codeserver_zola_env.sh
#
# Description:
#   This script sets up a Zola development environment inside a Code Server container.
#   It installs required packages and Code Server extensions, installs Zola,
#   and launches the Zola preview server.
#
# Required environment variables:
#   SUDO_TOKEN               Password/token used for running sudo commands non-interactively
#   ZOLA_PREVIEW_ROOT        Filesystem path to the Zola project root (passed to `zola serve --root`)
#   ZOLA_PREVIEW_INTERFACE   Network interface for preview server (e.g., 0.0.0.0)
#   ZOLA_PREVIEW_PORT        Port number to run Zola preview server on (e.g., 1111)
#   ZOLA_PREVIEW_BASE_URL    Base URL for the site, used as `--base-url $ZOLA_PREVIEW_BASE_URL`
#
# Required files:
#   extensions.txt           A list of Code Server extension IDs, one per line, to be installed

set -e # Exit immediately if any command fails

SCRIPT_PATH="$(readlink -f "$0")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"

# Zola .deb package URL
ZOLA_DEB_URL="https://github.com/barnumbirr/zola-debian/releases/download/v0.20.0-1/zola_0.20.0-1_amd64_bookworm.deb"

# Load shared shell functions
source "$SCRIPT_DIR/shell_lib/deps_installer.sh"

# Update and upgrade apt packages
auto_apt_update_upgrade "$SUDO_TOKEN"

# Ensure required packages are installed
ensure_packages_installed "$SUDO_TOKEN" "rsync" "python3" "python3-pip" "golang-go"

# Install Rust and its toolchain
curl https://sh.rustup.rs -sSf | sh -s -- -y
source $HOME/.cargo/env
ensure_packages_installed "$SUDO_TOKEN" "liblapack-dev"

# Install Code Server extensions listed in extensions.txt
install_codeserver_extensions "$SCRIPT_DIR/extensions.txt"

# Install Zola using the provided .deb URL
ensure_zola_installed "$SUDO_TOKEN" "$ZOLA_DEB_URL"

# Start the Zola preview server
zola --root "$ZOLA_PREVIEW_ROOT" serve \
    --interface "$ZOLA_PREVIEW_INTERFACE" \
    --port "$ZOLA_PREVIEW_PORT" \
    --base-url "$ZOLA_PREVIEW_BASE_URL"
