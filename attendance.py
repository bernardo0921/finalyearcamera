#!/usr/bin/env python3
"""
AS608 Fingerprint Scanner for Raspberry Pi
Captures fingerprint images and saves them to disk

Wiring:
- Red (VCC) -> 3.3V (Pin 1 or Pin 17)
- Black (TX) -> GPIO 15 (Pin 10) - RX on Pi
- Yellow (RX) -> GPIO 14 (Pin 8) - TX on Pi  
- Green (GND) -> Ground (Pin 6, 9, 14, 20, 25, 30, 34, or 39)

Requirements:
pip install pyserial pillow adafruit-circuitpython-fingerprint
"""

import serial
import time
import struct
from PIL import Image
import board
import busio
import adafruit_fingerprint
from datetime import datetime
import os

class AS608FingerprintScanner:
    def __init__(self, uart_port='/dev/ttyS0', baud_rate=57600):
        """
        Initialize the AS608 fingerprint scanner
        
        Args:
            uart_port: Serial port (default: /dev/ttyS0 for Pi's built-in UART)
            baud_rate: Communication speed (default: 57600)
        """
        self.uart_port = uart_port
        self.baud_rate = baud_rate
        self.finger = None
        self.setup_uart()
        
    def setup_uart(self):
        """Setup UART communication with the fingerprint sensor"""
        try:
            # Setup serial connection
            uart = busio.UART(board.TX, board.RX, baudrate=self.baud_rate)
            self.finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
            
            # Test connection
            if self.finger.verify_password():
                print("✅ AS608 Fingerprint sensor connected successfully!")
                print(f"📊 Sensor info: {self.finger.read_sysparam()}")
            else:
                print("❌ Failed to connect to fingerprint sensor")
                return False
                
        except Exception as e:
            print(f"❌ UART setup failed: {e}")
            print("\n🔧 Troubleshooting tips:")
            print("1. Check wiring connections")
            print("2. Enable serial interface: sudo raspi-config -> Interface Options -> Serial")
            print("3. Disable serial console but enable serial port hardware")
            return False
            
        return True
    
    def wait_for_finger(self):
        """Wait for a finger to be placed on the sensor"""
        print("👆 Please place your finger on the sensor...")
        
        while True:
            if self.finger.get_image() == adafruit_fingerprint.OK:
                print("✅ Finger detected!")
                return True
            time.sleep(0.1)
    
    def capture_fingerprint_template(self):
        """Capture fingerprint and convert to template"""
        try:
            # Get fingerprint image
            if self.finger.get_image() != adafruit_fingerprint.OK:
                return False, "Failed to get fingerprint image"
            
            # Convert image to template
            if self.finger.image_2_tz(1) != adafruit_fingerprint.OK:
                return False, "Failed to convert image to template"
                
            print("✅ Fingerprint template created successfully")
            return True, "Success"
            
        except Exception as e:
            return False, f"Error capturing fingerprint: {e}"
    
    def save_fingerprint_image(self, filename=None):
        """
        Save the fingerprint image to a file
        
        Args:
            filename: Output filename (auto-generated if None)
        """
        try:
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"fingerprint_{timestamp}.bmp"
            
            # Create output directory if it doesn't exist
            output_dir = "fingerprint_images"
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, filename)
            
            # Get the raw image data from sensor
            if self.finger.get_image() != adafruit_fingerprint.OK:
                print("❌ Failed to capture fingerprint image")
                return False
            
            # Download the image data
            if self.finger.download_image() != adafruit_fingerprint.OK:
                print("❌ Failed to download image data")
                return False
            
            # The image data is now in finger.image_buffer
            # AS608 produces 256x288 8-bit grayscale images
            width, height = 256, 288
            
            # Convert raw data to PIL Image
            img = Image.new('L', (width, height))
            img.putdata(self.finger.image_buffer)
            
            # Save the image
            img.save(filepath)
            print(f"💾 Fingerprint image saved: {filepath}")
            
            # Also save as PNG for better compatibility
            png_filepath = filepath.replace('.bmp', '.png')
            img.save(png_filepath)
            print(f"💾 PNG version saved: {png_filepath}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving fingerprint image: {e}")
            return False
    
    def scan_and_save_fingerprint(self):
        """Complete workflow: scan fingerprint and save image"""
        print("\n🔍 Starting fingerprint capture...")
        
        # Wait for finger placement
        if not self.wait_for_finger():
            print("❌ No finger detected")
            return False
        
        # Capture the fingerprint
        success, message = self.capture_fingerprint_template()
        if not success:
            print(f"❌ {message}")
            return False
        
        # Save the image
        if self.save_fingerprint_image():
            print("✅ Fingerprint capture and save completed successfully!")
            return True
        else:
            print("❌ Failed to save fingerprint image")
            return False
    
    def get_sensor_status(self):
        """Get sensor status and information"""
        try:
            params = self.finger.read_sysparam()
            print("\n📊 Sensor Status:")
            print(f"   Status Address: {params.status_reg}")
            print(f"   System ID: {params.system_id}")
            print(f"   Storage Capacity: {params.storage_capacity}")
            print(f"   Security Level: {params.security_level}")
            print(f"   Device Address: {params.device_address}")
            print(f"   Packet Length: {params.packet_length}")
            print(f"   Baud Rate: {params.baud_rate}")
            
        except Exception as e:
            print(f"❌ Error getting sensor status: {e}")

def main():
    """Main function to run the fingerprint scanner"""
    print("🔐 AS608 Fingerprint Scanner")
    print("=" * 40)
    
    # Initialize scanner
    scanner = AS608FingerprintScanner()
    
    if scanner.finger is None:
        print("❌ Failed to initialize scanner. Exiting.")
        return
    
    # Get sensor status
    scanner.get_sensor_status()
    
    # Main loop
    while True:
        print("\n" + "=" * 40)
        print("Options:")
        print("1. Capture and save fingerprint")
        print("2. Get sensor status")
        print("3. Exit")
        
        try:
            choice = input("\nSelect an option (1-3): ").strip()
            
            if choice == '1':
                scanner.scan_and_save_fingerprint()
                
            elif choice == '2':
                scanner.get_sensor_status()
                
            elif choice == '3':
                print("👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice. Please select 1, 2, or 3.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Exiting... Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()