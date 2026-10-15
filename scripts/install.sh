#!/usr/bin/env bash
# Installer to deploy smarthome-os under /opt and enable systemd service
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEST_DIR="/opt/smarthome-os"
SERVICE_NAME="smarthome.service"

echo "Copying files to $DEST_DIR (requires sudo)"
sudo mkdir -p "$DEST_DIR"
sudo rm -rf "$DEST_DIR"
sudo cp -R "$ROOT_DIR" "$DEST_DIR"
sudo chown -R root:root "$DEST_DIR"

echo "Creating virtualenv and installing requirements"
sudo "$DEST_DIR/scripts/setup_venv.sh"

echo "Installing systemd service"
sudo cp "$DEST_DIR/scripts/smarthome.service" /etc/systemd/system/$SERVICE_NAME
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

echo "Installation finished. Service: $SERVICE_NAME"
echo "Logs: sudo journalctl -u $SERVICE_NAME -f"
