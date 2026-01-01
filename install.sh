#!/bin/bash
# Install script for Garderoben-Ticketsystem

set -e

echo "=== Garderoben-Ticketsystem Installation ==="

# Create directory
mkdir -p /home/pi/garderobe

# Copy files
cp garderobe.py /home/pi/garderobe/
cp config.ini /home/pi/garderobe/
chmod +x /home/pi/garderobe/garderobe.py

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install python-escpos evdev

# Add user to required groups
echo "Adding pi to input and lp groups..."
sudo usermod -a -G input,lp pi

# Install systemd service
echo "Installing systemd service..."
sudo cp garderobe.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable garderobe.service

echo ""
echo "=== Installation complete ==="
echo ""
echo "Commands:"
echo "  sudo systemctl start garderobe   # Start service"
echo "  sudo systemctl status garderobe  # Check status"
echo "  sudo systemctl stop garderobe    # Stop service"
echo ""
echo "NOTE: Reboot recommended to apply group changes"
