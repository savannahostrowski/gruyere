#!/bin/sh
set -e

# Determine OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case $ARCH in
    x86_64)
        ARCH="amd64"
        ;;
    aarch64)
        ARCH="arm64"
        ;;
    i386|i686)
        ARCH="386"
        ;;
esac

# Set latest release version
VERSION=$(curl -s "https://api.github.com/repos/savannahostrowski/gruyere/releases/latest" | grep '"tag_name":' | sed -E 's/.*"v([0-9.]+)".*/\1/')

# Construct download URL
DOWNLOAD_URL="https://github.com/savannahostrowski/gruyere/releases/download/v1.1.5/gruyere_${VERSION}_${OS}_${ARCH}.tar.gz"

# Create temporary directory
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# Download and extract
echo "Downloading gruyere ${VERSION} for ${OS} ${ARCH}..."
curl -L "$DOWNLOAD_URL" | tar -xz -C "$TMP_DIR"

# Install
INSTALL_DIR="/usr/local/bin"
echo "Installing gruyere to $INSTALL_DIR..."
sudo mv "$TMP_DIR/gruyere" "$INSTALL_DIR/"

echo "gruyere ${VERSION} has been installed successfully!"
echo "You can now use the 'gruyere' command."
