log() {
    local level="$1"
    shift
    local message="$*"

    case "$level" in
    INFO)
        echo -e "[\e[32mINFO\e[0m] $message"
        ;;
    WARN)
        echo -e "[\e[33mWARN\e[0m] $message"
        ;;
    ERROR)
        echo -e "[\e[31mERROR\e[0m] $message"
        ;;
    OK)
        echo -e "[\e[36mOK\e[0m] $message"
        ;;
    *)
        echo "[LOG] $message"
        ;;
    esac
}

run_apt_update_upgrade() {
    local password="$1"
    echo "$password" | sudo -S apt update -qq
    echo "$password" | sudo -S apt upgrade -y
}

auto_apt_update_upgrade() {
    local password="$1"

    local last_update
    last_update=$(find /var/lib/apt/lists/ -type f -printf '%T@\n' 2>/dev/null | sort -n | tail -1)
    last_update=${last_update%.*}
    last_update=${last_update:-}

    if [[ -z "$last_update" ]]; then
        log INFO "No apt list files found. Running apt update and upgrade..."
        run_apt_update_upgrade "$password"
        return
    fi

    local now
    now=$(date +%s)
    local one_day=$((24 * 60 * 60))

    if ((now - last_update > one_day)); then
        log INFO "More than one day has passed since the last update. Running apt update and upgrade..."
        run_apt_update_upgrade "$password"
    else
        log INFO "System updated within the last day; no update necessary."
    fi
}

ensure_packages_installed() {
    local password="$1"
    shift

    auto_apt_update_upgrade "$password"
    for pkg in "$@"; do
        if dpkg -s "$pkg" >/dev/null 2>&1; then
            log INFO "$pkg is already installed. Skipping."
        else
            log INFO "$pkg not found. Installing..."
            echo "$password" | sudo -S apt install -y "$pkg"
        fi
    done
}

ensure_zola_installed() {
    local password="$1"
    local deb_url="$2"

    if [ -z "$password" ] || [ -z "$deb_url" ]; then
        log ERROR "Missing required parameters: password and deb_url."
        return 1
    fi

    if ! command -v zola >/dev/null 2>&1; then
        log INFO "Zola not found, installing..."

        echo "$password" | sudo -S apt -qq install --yes wget >/dev/null 2>&1

        local tmpdir
        tmpdir=$(mktemp -d)
        local deb_file="$tmpdir/$(basename "$deb_url")"

        if ! wget -q "$deb_url" -O "$deb_file"; then
            log ERROR "Failed to download Zola package."
            log ERROR "URL might be outdated or unavailable: $deb_url"
            log INFO "Please check for updated releases at:"
            log INFO "https://github.com/barnumbirr/zola-debian/releases"
            rm -rf "$tmpdir"
            return 1
        fi

        echo "$password" | sudo -S dpkg -i "$deb_file"
        rm -rf "$tmpdir"

        log OK "Zola installed successfully."
    else
        log INFO "Zola is already installed. Skipping installation."
    fi
}

install_codeserver_extensions() {
    local extensions_file="$1"
    local installed=$(code-server --list-extensions)

    while IFS= read -r EXT || [[ -n "$EXT" ]]; do
        # Skip empty lines or comment lines
        [[ -z "$EXT" || "$EXT" =~ ^# ]] && continue

        if ! grep -q "^$EXT$" <<< "$installed"; then
            log INFO "Installing extension: $EXT"
        else
            log INFO "Updating extension: $EXT"
        fi

        code-server --install-extension "$EXT"
    done < "$extensions_file"
}
