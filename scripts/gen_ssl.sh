#!/usr/bin/env bash
set -euo >/dev/null 2>&1

# ======== Generate locally trusted SSL certificates ======== 
generate_ssl_certs() {
    local ssl_dir="${1:-$(pwd)/ssl}"
    if ! command -v openssl &> /dev/null; then
        error "Error: please install openssl first." >&2
    fi

    local ssl_password=$(openssl rand -base64 24 | tr -d '+/=' | cut -c1-32)
    export SSL_PASSWORD="$ssl_password"
    info "Note: Private key is encrypted with AES-256. Use ssl_password to decrypt."

    # Since SSL_PASSWORD is only a temporarily exported variable in the 
    # shell environment where the current docker compose command is 
    # executed (not written to configuration files), the SSL_PASSWORD
    # environment variable inside the container will be lost once the 
    # container is stopped or downed and then upped again. Therefore, 
    # delete this directory before up to ensure a new set of certificates 
    # and a new password are used for each startup.
    rm -rf "$ssl_dir"
    mkdir -p "$ssl_dir"

    local temp_key="$ssl_dir/private.unencrypted.key"
    if ! command -v mkcert &> /dev/null; then
        case "$(uname -s)" in
            MINGW*|MSYS*|CYGWIN*)
                openssl req -x509 -nodes -days 365 \
                -newkey rsa:2048 \
                -keyout "$temp_key" \
                -out "$ssl_dir/certificate.crt" \
                -subj "//CN=localhost"
                ;;
            *)
                openssl req -x509 -nodes -days 365 \
                -newkey rsa:2048 \
                -keyout "$temp_key" \
                -out "$ssl_dir/certificate.crt" \
                -subj "/CN=localhost"
                ;;
        esac
    else
        info "Generating certificate with mkcert..."
        mkcert -cert-file "$ssl_dir/certificate.crt" -key-file "$temp_key" localhost 127.0.0.1 ::1
    fi

    info "Encrypting private key with generated password..."
    openssl rsa -aes256 \
        -in "$temp_key" \
        -out "$ssl_dir/private.key" \
        -passout "pass:$ssl_password"

    rm -f "$temp_key"

    chmod 600 "$ssl_dir/private.key"
    chmod 644 "$ssl_dir/certificate.crt"
}