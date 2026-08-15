#!/bin/bash

# How to run the script (will automatically set environment variable and output the key)
#   source <(./generate_aes_key.sh)
# Or
#   export SERVER_AES_MASTER_KEY=$(./generate_aes_key.sh)

# Reuse an already-configured key if present (env var or .env file), so that
# repeated invocations (setup.sh, manage_service.sh) never generate a new key
# that would invalidate previously encrypted API keys (issue #1236).
if [ -z "${SERVER_AES_MASTER_KEY_ENV:-}" ]; then
    SERVER_AES_MASTER_KEY_ENV="${SERVER_AES_MASTER_KEY:-}"
fi
if [ -z "${SERVER_AES_MASTER_KEY_ENV:-}" ] && [ -f ".env" ]; then
    AES_KEY_LINE=$(grep '^SERVER_AES_MASTER_KEY=' ".env" 2>/dev/null | head -n 1)
    if [ -n "$AES_KEY_LINE" ]; then
        SERVER_AES_MASTER_KEY_ENV=$(echo "$AES_KEY_LINE" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    fi
fi

# Generate 32-byte (256-bit) AES key and set as environment variable
if [ -z "${SERVER_AES_MASTER_KEY_ENV:-}" ]; then
    SERVER_AES_MASTER_KEY_ENV=$(openssl rand -base64 32)
fi
export SERVER_AES_MASTER_KEY_ENV

# Output the key
echo "$SERVER_AES_MASTER_KEY_ENV"

# Verify key length (optional)
if command -v openssl >/dev/null 2>&1; then
    decoded_key=$(echo "$SERVER_AES_MASTER_KEY_ENV" | openssl base64 -d 2>/dev/null)
elif echo | base64 -d >/dev/null 2>&1; then
    decoded_key=$(echo "$SERVER_AES_MASTER_KEY_ENV" | base64 -d 2>/dev/null)
else
    decoded_key=$(echo "$SERVER_AES_MASTER_KEY_ENV" | base64 --decode 2>/dev/null)
fi

byte_count=$(echo -n "$decoded_key" | wc -c)

if [ "$byte_count" -eq 32 ]; then
    exit 0
else
    echo "Error: Generated key length is incorrect (got $byte_count bytes, expected 32)" >&2
    exit 1
fi
