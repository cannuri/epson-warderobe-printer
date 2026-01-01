#!/usr/bin/env python3
"""
Garderoben-Ticketsystem für FUNKHAUS
Druckt nummerierte Tickets auf Epson TM-T88V via USB-Fußpedal
"""

import json
import logging
import os
import sys
import configparser
from datetime import datetime
from pathlib import Path

try:
    from escpos.printer import Usb
    from evdev import InputDevice, categorize, ecodes, list_devices
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install python-escpos evdev")
    sys.exit(1)

# Paths
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.ini"
STATE_FILE = BASE_DIR / "state.json"
LOG_FILE = BASE_DIR / "error.log"

# Epson TM-T88V USB IDs
EPSON_VENDOR_ID = 0x04b8
EPSON_PRODUCT_ID = 0x0e02  # TM-T88V

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration manager"""
    def __init__(self):
        self.current_number = 500
        self.cut_mode = "partial"
        self.load()

    def load(self):
        if CONFIG_FILE.exists():
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            if 'general' in config:
                self.current_number = config.getint('general', 'current_number', fallback=500)
                self.cut_mode = config.get('general', 'cut_mode', fallback='partial')

    def save(self):
        config = configparser.ConfigParser()
        config['general'] = {
            'current_number': str(self.current_number),
            'cut_mode': self.cut_mode
        }
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)


class State:
    """Persistent state manager"""
    def __init__(self, config: Config):
        self.config = config
        self.current_number = config.current_number
        self.print_count = 0  # 0 or 1 (prints twice per number)
        self.load()

    def load(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.current_number = data.get('current_number', self.config.current_number)
                    self.print_count = data.get('print_count', 0)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load state: {e}")

    def save(self):
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump({
                    'current_number': self.current_number,
                    'print_count': self.print_count
                }, f)
        except IOError as e:
            logger.error(f"Could not save state: {e}")

    def next_print(self) -> int:
        """Get current number and advance state"""
        number = self.current_number
        self.print_count += 1
        if self.print_count >= 2:
            self.print_count = 0
            self.current_number += 1
        self.save()
        return number


class TicketPrinter:
    """Epson TM-T88V printer interface"""
    def __init__(self, config: Config):
        self.config = config
        self.printer = None

    def connect(self) -> bool:
        try:
            self.printer = Usb(EPSON_VENDOR_ID, EPSON_PRODUCT_ID)
            logger.info("Drucker verbunden")
            return True
        except Exception as e:
            logger.error(f"Drucker nicht erreichbar: {e}")
            self.printer = None
            return False

    def is_connected(self) -> bool:
        return self.printer is not None

    def print_ticket(self, number: int) -> bool:
        if not self.printer:
            if not self.connect():
                return False

        try:
            now = datetime.now()
            date_str = now.strftime("%d.%m.%Y  %H:%M")

            # Reset and center
            self.printer.set(align='center')

            # Header
            self.printer.set(align='center', bold=True, double_height=True, double_width=True)
            self.printer.text("FUNKHAUS\n")

            # Spacing
            self.printer.text("\n")

            # Date/time (small)
            self.printer.set(align='center', bold=False, double_height=False, double_width=False)
            self.printer.text(f"{date_str}\n")

            # Spacing
            self.printer.text("\n")

            # Number (large, bold)
            self.printer.set(align='center', bold=True, double_height=True, double_width=True)
            self.printer.text(f"{number}\n")

            # Spacing before cut
            self.printer.text("\n\n")

            # Cut
            if self.config.cut_mode == "full":
                self.printer.cut(mode='FULL')
            else:
                self.printer.cut(mode='PART')

            logger.info(f"Ticket gedruckt: {number}")
            return True

        except Exception as e:
            logger.error(f"Druckfehler: {e}")
            self.printer = None
            return False


def find_input_device() -> InputDevice | None:
    """Find input device (keyboard preferred, foot pedal as fallback)"""
    # Sort by path to get lower event numbers first (they tend to be the main interface)
    devices = sorted([InputDevice(path) for path in list_devices()], key=lambda d: d.path)

    # Priority 1: USB keyboard (skip foot pedal, HDMI, consumer/system control)
    for device in devices:
        name_lower = device.name.lower()
        caps = device.capabilities()
        if ecodes.EV_KEY not in caps:
            continue
        # Skip problematic devices
        if any(skip in name_lower for skip in ['hdmi', 'vc4', 'foot', 'pedal', 'consumer', 'system']):
            continue
        # Accept keyboards
        if 'keyboard' in name_lower:
            return device

    # Priority 2: Any HID device with keys (excluding above)
    for device in devices:
        name_lower = device.name.lower()
        caps = device.capabilities()
        if ecodes.EV_KEY not in caps:
            continue
        if any(skip in name_lower for skip in ['hdmi', 'vc4', 'consumer', 'system']):
            continue
        return device

    return None


def main():
    logger.info("Garderoben-Ticketsystem gestartet")

    config = Config()
    state = State(config)
    printer = TicketPrinter(config)

    # Find input device (foot pedal or keyboard)
    input_dev = find_input_device()
    if not input_dev:
        logger.error("Kein Eingabegerät gefunden! Verfügbare Geräte:")
        for path in list_devices():
            dev = InputDevice(path)
            logger.error(f"  {path}: {dev.name}")
        sys.exit(1)

    logger.info(f"Eingabegerät: {input_dev.name} ({input_dev.path})")

    # Grab device exclusively so desktop doesn't intercept
    try:
        input_dev.grab()
        logger.info("Gerät exklusiv übernommen")
    except Exception as e:
        logger.warning(f"Konnte Gerät nicht exklusiv übernehmen: {e}")

    # Initial printer connection
    printer.connect()

    logger.info(f"Bereit. Aktuelle Nummer: {state.current_number}, Drucke: {state.print_count}/2")
    logger.info("Drücken Sie eine beliebige Taste zum Drucken...")

    # Main event loop
    try:
        for event in input_dev.read_loop():
            if event.type == ecodes.EV_KEY:
                key_event = categorize(event)
                # Only trigger on key press (not release)
                if key_event.keystate == 1:  # Key down
                    if printer.is_connected() or printer.connect():
                        number = state.next_print()
                        printer.print_ticket(number)
                    else:
                        logger.warning("Druckauftrag ignoriert - Drucker nicht verbunden")
    except KeyboardInterrupt:
        logger.info("System beendet")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
