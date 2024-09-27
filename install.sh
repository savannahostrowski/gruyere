#!/usr/bin/env sh

set -e

# Determine OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case $ARCH in
    x86_64)
        ARCH="amd64"
        ;;
    aarch64|arm64)
        ARCH="arm64"
        ;;
    i386|i686)
        ARCH="386"
        ;;
	*)
		echo "Unsupported architecture: $ARCH"
		exit 1
		;;
esac

# Check for version argument
# Otherwise, set latest release version
if [ -z "$VERSION" ]; then
	VERSION=$(curl -s "https://api.github.com/repos/savannahostrowski/gruyere/releases/latest" | grep '"tag_name":' | sed -E 's/.*"v([0-9.]+)".*/\1/')
fi

# Construct download URL
DOWNLOAD_URL="https://github.com/savannahostrowski/gruyere/releases/download/v${VERSION}/gruyere_${VERSION}_${OS}_${ARCH}.tar.gz"

# Create temporary directory
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# Download and extract
echo "Downloading gruyere ${VERSION} for ${OS} ${ARCH}..."
curl -L -s "$DOWNLOAD_URL" | tar -xz -C "$TMP_DIR"

# Check if directory is writable by the current user
# If not, use sudo to install
INSTALL_DIR=${INSTALL_DIR:-/usr/local/bin}
if [ ! -w "$INSTALL_DIR" ]; then
	echo "Installing gruyere to $INSTALL_DIR..."
	sudo mkdir -p "$INSTALL_DIR"
	sudo mv "$TMP_DIR/gruyere" "$INSTALL_DIR/"
else
	echo "Installing gruyere to $INSTALL_DIR..."
	mkdir -p "$INSTALL_DIR"
	mv "$TMP_DIR/gruyere" "$INSTALL_DIR/"
fi

echo "gruyere ${VERSION} has been installed successfully!"
echo "Be sure that $INSTALL_DIR is in your PATH:"
printf "\n\texport PATH=\$PATH:%s\n\n" "$INSTALL_DIR"
echo "You can now use the 'gruyere' command."
