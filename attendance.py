#!/usr/bin/env python3
"""
ZA620_M5 Fingerprint Scanner for Raspberry Pi
Generic fingerprint sensor interface that works with ZA620_M5 and similar modules

Wiring:
- Red (VCC) -> 3.3V (Pin 1 or Pin 17)
- Black (TX) -> GPIO 15 (Pin 10) - RX on Pi
- Yellow (RX) -> GPIO 14 (Pin 8) - TX on Pi  
- Green (GND) -> Ground (Pin 6, 9, 14, 20, 25, 30, 34, or 39)

Requirements:
pip install pyserial pillow
"""

import serial
import time
import struct
from PIL import Image
from datetime import datetime
import os

class ZA620FingerprintScanner:
    def __init__(self, uart_port='/dev/ttyS0', baud_rate=57600):
        """
        Initialize the ZA620_M5 fingerprint scanner
        
        Args:
            uart_port: Serial port (default: /dev/ttyS0 for Pi's built-in UART)
            baud_rate: Communication speed (try: 9600, 57600, 115200)
        """
        self.uart_port = uart_port
        self.baud_rate = baud_rate
        self.serial = None
        self.connected = False
        
        # Common fingerprint sensor command packets
        self.commands = {
            'header': [0xEF, 0x01],
            'address': [0xFF, 0xFF, 0xFF, 0xFF],
            'verify_pwd': 0x13,
            'get_image': 0x01,
            'img_2_tz': 0x02,
            'read_sys_param': 0x0F,
            'template_count': 0x1D
        }
        
        self.setup_connection()
        
    def setup_connection(self):
        """Setup serial connection and test different configurations"""
        baud_rates = [57600, 9600, 19200, 38400, 115200]
        ports = ['/dev/ttyS0', '/dev/ttyAMA0', '/dev/serial0']
        
        print("🔍 Scanning for ZA620_M5 fingerprint sensor...")
        
        for port in ports:
            if not os.path.exists(port):
                continue
                
            print(f"   Trying port: {port}")
            
            for baud in baud_rates:
                try:
                    print(f"      Testing baud rate: {baud}")
                    ser = serial.Serial(port, baud, timeout=2)
                    time.sleep(0.5)  # Give sensor time to initialize
                    
                    # Test connection with multiple methods
                    if self.test_connection(ser):
                        self.serial = ser
                        self.uart_port = port
                        self.baud_rate = baud
                        self.connected = True
                        print(f"✅ ZA620_M5 connected successfully!")
                        print(f"   Port: {port}, Baud Rate: {baud}")
                        return True
                    
                    ser.close()
                    
                except Exception as e:
                    pass
        
        print("❌ Could not establish connection to ZA620_M5")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check wiring connections")
        print("2. Verify sensor power (stable 3.3V)")
        print("3. Enable serial interface: sudo raspi-config -> Interface Options -> Serial")
        print("4. Try different baud rates manually")
        return False
    
    def test_connection(self, ser):
        """Test if sensor responds to commands"""
        try:
            # Clear any existing data
            ser.flushInput()
            ser.flushOutput()
            
            # Test 1: Try basic handshake/verify password command
            packet1 = self.build_packet(0x01, [self.commands['verify_pwd'], 0x00, 0x00, 0x00, 0x00])
            ser.write(bytes(packet1))
            time.sleep(0.2)
            
            response1 = ser.read(20)
            if len(response1) > 0:
                print(f"      Response 1: {len(response1)} bytes - {response1.hex()}")
                return True
            
            # Test 2: Try get image command
            packet2 = self.build_packet(0x01, [self.commands['get_image']])
            ser.write(bytes(packet2))
            time.sleep(0.2)
            
            response2 = ser.read(20)
            if len(response2) > 0:
                print(f"      Response 2: {len(response2)} bytes - {response2.hex()}")
                return True
            
            # Test 3: Try system parameter command
            packet3 = self.build_packet(0x01, [self.commands['read_sys_param']])
            ser.write(bytes(packet3))
            time.sleep(0.2)
            
            response3 = ser.read(30)
            if len(response3) > 0:
                print(f"      Response 3: {len(response3)} bytes - {response3.hex()}")
                return True
                
            return False
            
        except Exception as e:
            return False
    
    def build_packet(self, packet_type, data):
        """Build a command packet for the fingerprint sensor"""
        packet = (self.commands['header'] + 
                 self.commands['address'] + 
                 [packet_type] + 
                 [(len(data) + 2) >> 8, (len(data) + 2) & 0xFF] + 
                 data)
        
        # Calculate checksum
        checksum = sum(packet[6:])
        packet.extend([(checksum >> 8) & 0xFF, checksum & 0xFF])
        
        return packet
    
    def send_command(self, packet_type, data):
        """Send command and read response"""
        if not self.connected:
            return None, None
            
        try:
            self.serial.flushInput()
            self.serial.flushOutput()
            
            packet = self.build_packet(packet_type, data)
            self.serial.write(bytes(packet))
            time.sleep(0.1)
            
            # Read response header first
            header = self.serial.read(9)
            if len(header) < 9:
                return None, None
            
            # Check for valid header
            if header[0] != 0xEF or header[1] != 0x01:
                return None, None
            
            response_type = header[6]
            length = (header[7] << 8) | header[8]
            
            # Read remaining data
            data = self.serial.read(length)
            if len(data) >= 2:
                return response_type, list(data[:-2])  # Remove checksum
            
            return response_type, []
            
        except Exception as e:
            print(f"❌ Command error: {e}")
            return None, None
    
    def wait_for_finger(self, timeout=30):
        """Wait for a finger to be placed on the sensor"""
        print("👆 Please place your finger on the sensor...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Try to get an image
            response_type, data = self.send_command(0x01, [self.commands['get_image']])
            
            if response_type == 0x07 and data and len(data) > 0:
                if data[0] == 0x00:  # Success
                    print("✅ Finger detected!")
                    return True
                elif data[0] == 0x02:  # No finger
                    pass  # Continue waiting
                else:
                    print(f"   Sensor status: 0x{data[0]:02x}")
            
            time.sleep(0.1)
        
        print("⏰ Timeout waiting for finger")
        return False
    
    def capture_fingerprint(self):
        """Capture a fingerprint and convert to template"""
        try:
            # Step 1: Get image
            response_type, data = self.send_command(0x01, [self.commands['get_image']])
            
            if not (response_type == 0x07 and data and data[0] == 0x00):
                return False, "Failed to capture fingerprint image"
            
            print("✅ Fingerprint image captured")
            
            # Step 2: Convert image to template
            response_type, data = self.send_command(0x01, [self.commands['img_2_tz'], 0x01])
            
            if not (response_type == 0x07 and data and data[0] == 0x00):
                return False, "Failed to convert image to template"
            
            print("✅ Fingerprint template created")
            return True, "Success"
            
        except Exception as e:
            return False, f"Error: {e}"
    
    def get_sensor_info(self):
        """Get sensor system parameters"""
        try:
            response_type, data = self.send_command(0x01, [self.commands['read_sys_param']])
            
            if response_type == 0x07 and data and len(data) > 16:
                print("\n📊 ZA620_M5 Sensor Information:")
                print(f"   Status Register: 0x{(data[1] << 8 | data[2]):04x}")
                print(f"   System ID: 0x{(data[3] << 8 | data[4]):04x}")
                print(f"   Storage Capacity: {(data[5] << 8 | data[6])}")
                print(f"   Security Level: {(data[7] << 8 | data[8])}")
                print(f"   Device Address: 0x{(data[9] << 24 | data[10] << 16 | data[11] << 8 | data[12]):08x}")
                print(f"   Packet Length: {(data[13] << 8 | data[14])}")
                print(f"   Baud Rate: {(data[15] << 8 | data[16]) * 9600}")
                return True
            else:
                print("📊 Basic sensor connection confirmed")
                print(f"   Port: {self.uart_port}")
                print(f"   Baud Rate: {self.baud_rate}")
                return False
                
        except Exception as e:
            print(f"❌ Error getting sensor info: {e}")
            return False
    
    def save_test_image(self):
        """Save a test fingerprint image pattern"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"za620_test_{timestamp}"
            
            output_dir = "fingerprint_images"
            os.makedirs(output_dir, exist_ok=True)
            
            # Create a test pattern (since real image download requires specific protocol)
            width, height = 256, 288
            img = Image.new('L', (width, height))
            
            # Generate a fingerprint-like pattern
            pixels = []
            for y in range(height):
                for x in range(width):
                    # Create concentric circles pattern
                    center_x, center_y = width//2, height//2
                    distance = ((x - center_x)**2 + (y - center_y)**2)**0.5
                    value = int((128 + 127 * (distance % 20) / 20)) % 256
                    pixels.append(value)
            
            img.putdata(pixels)
            
            # Save files
            bmp_path = os.path.join(output_dir, f"{filename}.bmp")
            png_path = os.path.join(output_dir, f"{filename}.png")
            
            img.save(bmp_path)
            img.save(png_path)
            
            print(f"💾 Test image saved: {bmp_path}")
            print(f"💾 PNG version saved: {png_path}")
            print("⚠️  Note: This is a test pattern. Real image capture requires")
            print("    specific protocol implementation for your sensor model.")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving test image: {e}")
            return False
    
    def manual_command_test(self):
        """Manual command testing interface"""
        if not self.connected:
            print("❌ Not connected to sensor")
            return
        
        print("\n🔧 Manual Command Test Mode")
        print("Enter hex commands (e.g., '01' for get_image, '0F' for read_sys_param)")
        print("Type 'quit' to exit")
        
        while True:
            try:
                cmd_input = input("\nCommand (hex): ").strip().lower()
                
                if cmd_input == 'quit':
                    break
                
                if len(cmd_input) == 2:
                    cmd_byte = int(cmd_input, 16)
                    response_type, data = self.send_command(0x01, [cmd_byte])
                    
                    print(f"Response Type: 0x{response_type:02x}" if response_type else "No response")
                    if data:
                        print(f"Data: {' '.join(f'0x{b:02x}' for b in data)}")
                        print(f"Raw: {bytes(data).hex()}")
                    
                else:
                    print("❌ Enter exactly 2 hex digits")
                    
            except ValueError:
                print("❌ Invalid hex format")
            except KeyboardInterrupt:
                break

def main():
    """Main function"""
    print("🔐 ZA620_M5 Fingerprint Scanner Interface")
    print("=" * 50)
    
    scanner = ZA620FingerprintScanner()
    
    if not scanner.connected:
        print("❌ Scanner initialization failed. Exiting.")
        return
    
    while True:
        print("\n" + "=" * 50)
        print("Options:")
        print("1. Test finger detection")
        print("2. Capture fingerprint")
        print("3. Get sensor information") 
        print("4. Save test image pattern")
        print("5. Manual command test")
        print("6. Exit")
        
        try:
            choice = input("\nSelect option (1-6): ").strip()
            
            if choice == '1':
                if scanner.wait_for_finger():
                    print("✅ Finger detection successful!")
                else:
                    print("❌ No finger detected")
            
            elif choice == '2':
                if scanner.wait_for_finger():
                    success, message = scanner.capture_fingerprint()
                    print(f"{'✅' if success else '❌'} {message}")
            
            elif choice == '3':
                scanner.get_sensor_info()
            
            elif choice == '4':
                scanner.save_test_image()
            
            elif choice == '5':
                scanner.manual_command_test()
            
            elif choice == '6':
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice")
                
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    if scanner.serial:
        scanner.serial.close()

if __name__ == "__main__":
    main()