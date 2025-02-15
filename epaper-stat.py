#!/usr/bin/env python3
"""
E-Paper System Statistics Display
A comprehensive system monitoring tool for Waveshare 2.13inch V4 E-Paper display.
"""

import os
import sys
import time
import logging
import psutil
import socket
import subprocess
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import waveshare_epd.epd2in13_V4 as epd_module


class SystemMonitor:
    """
    SystemMonitor class handles system statistics collection and display
    on a Waveshare 2.13inch V4 E-Paper display using partial updates.
    """

    # Display dimensions
    DISPLAY_WIDTH = 250
    DISPLAY_HEIGHT = 122

    # Update configuration
    FULL_REFRESH_INTERVAL = 3600  # Full refresh every 12 updates
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1  # seconds

    def __init__(self):
        """Initialize the SystemMonitor with display and font configuration."""
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s: %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('epaper_stats.log')
            ]
        )

        # Initialize instance variables
        self.epd = None
        self.last_image = None
        self.update_count = 0
        self.fonts = {}
        self.first_run = True  # Add flag for first run

        # Initialize display and fonts
        self.init_display()
        self.setup_fonts()

    def init_display(self):
        """Initialize the e-Paper display."""
        try:
            self.epd = epd_module.EPD()
            self.epd.init()
            self.epd.Clear()
            logging.info("Display initialized successfully")
            self.last_image = Image.new('1', (self.DISPLAY_WIDTH, self.DISPLAY_HEIGHT), 255)
        except Exception as e:
            logging.error(f"Failed to initialize display: {e}")
            raise

    def setup_fonts(self):
        """Setup fonts with fallback options."""
        script_dir = sys.path[0]

        font_paths = [
            os.path.join(script_dir, "pic", "Font.ttc"),
            os.path.join(script_dir, "Font.ttc"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf"
        ]

        # Find first available font
        font_path = next((path for path in font_paths if os.path.exists(path)), None)

        if font_path:
            logging.info(f"Using font: {font_path}")
            try:
                self.fonts = {
                    'tiny': ImageFont.truetype(font_path, 10),
                    'small': ImageFont.truetype(font_path, 12),
                    'normal': ImageFont.truetype(font_path, 16),
                    'large': ImageFont.truetype(font_path, 20)
                }
                return
            except Exception as e:
                logging.error(f"Error loading font: {e}")

        # Fallback to default font
        logging.warning("Using default font as fallback")
        default_font = ImageFont.load_default()
        self.fonts = {
            'tiny': default_font,
            'small': default_font,
            'normal': default_font,
            'large': default_font
        }

    def get_network_info(self):
        """Collect network-related information."""
        info = {
            'lan_ip': 'N/A',
            'wifi_signal': 'N/A',
            'internet': 'Disconnected'
        }

        # Get LAN IP
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                info['lan_ip'] = s.getsockname()[0]
        except Exception as e:
            logging.error(f"Error getting LAN IP: {e}")

        # Check internet connection
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            info['internet'] = "Connected"
        except Exception:
            pass

        # Get WiFi signal strength
        try:
            output = subprocess.check_output(
                ["iwconfig", "wlan0"],
                universal_newlines=True,
                stderr=subprocess.DEVNULL
            )
            for line in output.split("\n"):
                if "Signal level" in line:
                    info['wifi_signal'] = line.split("Signal level=")[1].split()[0]
        except Exception as e:
            logging.debug(f"Error getting WiFi strength: {e}")

        return info

    def get_system_metrics(self):
        """Collect system metrics."""
        metrics = {}

        # CPU Usage
        try:
            metrics['cpu'] = f"{psutil.cpu_percent()}%"
        except Exception:
            metrics['cpu'] = "N/A"

        # Memory Usage
        try:
            metrics['memory'] = f"{psutil.virtual_memory().percent}%"
        except Exception:
            metrics['memory'] = "N/A"

        # Disk Usage
        try:
            metrics['disk'] = f"{psutil.disk_usage('/').percent}%"
        except Exception:
            metrics['disk'] = "N/A"

        # CPU Temperature
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
                metrics['temp'] = f"{temp:.1f}°C"
        except Exception:
            metrics['temp'] = "N/A"

        # System Uptime
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                days = int(uptime_seconds // (24 * 3600))
                hours = int((uptime_seconds % (24 * 3600)) // 3600)
                metrics['uptime'] = f"{days}d {hours}h"
        except Exception:
            metrics['uptime'] = "N/A"

        return metrics

    def _draw_content(self, draw, network_info, system_metrics):
        """Draw all content on the image."""
        # Get current time and date
        current_time = datetime.now().strftime("%H:%M")
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Draw header
        draw.text((5, 2), socket.gethostname(), font=self.fonts['large'], fill=0)
        draw.text((90, 2), f"{current_date} {current_time}",
                  font=self.fonts['small'], fill=0)
        draw.line([(0, 23), (250, 23)], fill=0, width=1)

        # Network section
        network_y = 30
        draw.text((5, network_y), "Network Info:", font=self.fonts['normal'], fill=0)
        draw.text((10, network_y + 20), f"IP: {network_info['lan_ip']}",
                  font=self.fonts['small'], fill=0)
        draw.text((130, network_y + 20), f"WiFi: {network_info['wifi_signal']}",
                  font=self.fonts['small'], fill=0)
        draw.text((130, network_y), f"Net: {network_info['internet']}",
                  font=self.fonts['small'], fill=0)

        # System metrics section
        system_y = 75
        draw.line([(0, system_y - 10), (250, system_y - 10)], fill=0, width=1)

        # Draw system metric boxes
        metrics_display = [
            ("CPU", system_metrics['cpu']),
            ("TEMP", system_metrics['temp']),
            ("MEM", system_metrics['memory']),
            ("DISK", system_metrics['disk']),
            ("UP", system_metrics['uptime'])
        ]

        box_width = 47
        spacing = 3
        start_x = 2

        for i, (label, value) in enumerate(metrics_display):
            x = start_x + i * (box_width + spacing)
            # Draw box
            draw.rectangle([(x, system_y), (x + box_width, system_y + 40)], outline=0)
            # Draw label
            draw.text((x + 5, system_y + 2), label, font=self.fonts['tiny'], fill=0)
            # Draw value
            draw.text((x + 5, system_y + 15), value, font=self.fonts['small'], fill=0)

    def _partial_update(self, new_image):
        """Perform partial update of the display."""
        try:
            self.epd.displayPartial(self.epd.getbuffer(new_image))
            return True
        except Exception as e:
            logging.error(f"Partial update failed: {e}")
            return False

    def display_info(self):
        """Update the display with current system information."""
        try:
            # Create new image
            new_image = Image.new('1', (self.DISPLAY_WIDTH, self.DISPLAY_HEIGHT), 255)
            draw = ImageDraw.Draw(new_image)

            # Collect system information
            network_info = self.get_network_info()
            system_metrics = self.get_system_metrics()

            # Draw content
            self._draw_content(draw, network_info, system_metrics)

            # Update display
            if self.epd:
                if self.first_run or self.update_count >= self.FULL_REFRESH_INTERVAL:
                    # Perform full refresh
                    logging.info("Performing full refresh")
                    self.epd.init()
                    self.epd.display(self.epd.getbuffer(new_image))
                    self.update_count = 0
                    self.first_run = False  # Reset first run flag
                else:
                    # Perform partial update
                    if not self._partial_update(new_image):
                        # If partial update fails, try full refresh
                        self.epd.init()
                        self.epd.display(self.epd.getbuffer(new_image))
                    self.update_count += 1

                self.last_image = new_image

        except Exception as e:
            logging.error(f"Error updating display: {e}")
            # Attempt to recover
            try:
                self.init_display()
            except Exception as reinit_error:
                logging.error(f"Failed to recover display: {reinit_error}")

    def cleanup_display(self):
        """Clean up display resources."""
        try:
            if self.epd:
                self.epd.init()
                self.epd.Clear()
                self.epd.sleep()
                logging.info("Display cleanup completed")
        except Exception as e:
            logging.error(f"Error during display cleanup: {e}")


def main():
    """Main program loop."""
    update_interval = 1  # in seconds

    try:
        monitor = SystemMonitor()

        logging.info("Starting system monitoring...")
        while True:
            try:
                monitor.display_info()
                time.sleep(update_interval)
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                time.sleep(5)  # Wait before retry

    except KeyboardInterrupt:
        logging.info("Monitoring stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
    finally:
        if 'monitor' in locals():
            monitor.cleanup_display()


if __name__ == "__main__":
    main()
