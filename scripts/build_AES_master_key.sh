#!/bin/bash

# How to run the script (will automatically set environment variable and output the key)
#   source <(./generate_aes_key.sh)
# Or
#   export SERVER_AES_MASTER_KEY=$(./generate_aes_key.sh)

# Generate 32-byte (256-bit) AES key and set as environment variable
export SERVER_AES_MASTER_KEY_ENV=$(openssl rand -base64 32)

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
