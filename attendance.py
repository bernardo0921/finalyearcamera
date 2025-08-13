import serial
from PIL import Image
import time
import os

# === CONFIG ===
PORT = "/dev/serial0"  # Change to /dev/ttyAMA0 if needed
BAUD = 57600
IMG_WIDTH, IMG_HEIGHT = 256, 288
OUTPUT_FOLDER = "/home/pi/fingerprint_images"

# Ensure folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# === COMMANDS ===
GET_IMAGE = b'\xEF\x01\xFF\xFF\xFF\xFF\x01\x00\x03\x01\x00\x05'
DOWN_IMAGE = b'\xEF\x01\xFF\xFF\xFF\xFF\x01\x00\x03\x0A\x00\x0E'

# === FUNCTIONS ===
def send_cmd(ser, cmd):
    ser.write(cmd)

def read_packets(ser):
    """Read all image data packets until End Packet is received."""
    image_data = b''
    while True:
        packet = ser.read(139)  # 9-byte header + 128 data + 2-byte checksum
        if len(packet) < 11:
            break
        if packet[6] == 0x02:  # Data packet
            image_data += packet[9:-2]
        elif packet[6] == 0x08:  # End of data packet
            image_data += packet[9:-2]
            break
    return image_data

# === MAIN ===
with serial.Serial(PORT, BAUD, timeout=1) as ser:
    time.sleep(1)  # Give port time

    # Step 1: Capture image
    send_cmd(ser, GET_IMAGE)
    resp = ser.read(12)
    if len(resp) >= 10 and resp[9] == 0x00:
        print("[+] Fingerprint image captured.")
    else:
        print("[-] Failed to capture image. Try placing finger firmly.")
        exit()

    # Step 2: Download image
    send_cmd(ser, DOWN_IMAGE)
    raw_data = read_packets(ser)

    if len(raw_data) != IMG_WIDTH * IMG_HEIGHT:
        print("[-] Unexpected image size:", len(raw_data))
        exit()

    # Step 3: Save PNG
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    png_path = os.path.join(OUTPUT_FOLDER, f"fingerprint_{timestamp}.png")

    img = Image.frombytes('L', (IMG_WIDTH, IMG_HEIGHT), raw_data)
    img.save(png_path)
    print(f"[+] Saved fingerprint image: {png_path}")
