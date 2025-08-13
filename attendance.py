import serial
import cv2
import numpy as np
import time
import os

# === CONFIG ===
PORT = "/dev/serial0"  # Change to /dev/ttyAMA0 if needed
BAUD = 57600
IMG_WIDTH, IMG_HEIGHT = 256, 288
OUTPUT_FOLDER = "/home/pi/images"

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

def capture_fingerprint(ser):
    # Step 1: Capture image
    send_cmd(ser, GET_IMAGE)
    resp = ser.read(12)
    if len(resp) >= 10 and resp[9] == 0x00:
        print("[+] Fingerprint detected.")
    else:
        return None  # No fingerprint

    # Step 2: Download image
    send_cmd(ser, DOWN_IMAGE)
    raw_data = read_packets(ser)

    if len(raw_data) != IMG_WIDTH * IMG_HEIGHT:
        print("[-] Unexpected image size:", len(raw_data))
        return None

    return raw_data

def save_fingerprint(raw_data, filename):
    img_array = np.frombuffer(raw_data, dtype=np.uint8).reshape((IMG_HEIGHT, IMG_WIDTH))
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    cv2.imwrite(filepath, img_array)
    print(f"[+] Saved fingerprint image: {filepath}")

# === MAIN LOOP ===
with serial.Serial(PORT, BAUD, timeout=1) as ser:
    time.sleep(1)  # Give port time
    print("[*] Waiting for fingerprints... (Press Ctrl+C to stop)")

    try:
        while True:
            raw_data = capture_fingerprint(ser)
            if raw_data:
                # Ask for name after capture
                name = input("Enter a name for this fingerprint: ").strip()
                if not name:
                    name = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{name}.png"
                save_fingerprint(raw_data, filename)
                print("[*] Ready for next fingerprint...\n")
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[!] Stopped.")
