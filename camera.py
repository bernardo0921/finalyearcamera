import time
from picamera2 import Picamera2

# A simple Python script to capture and save an image from the Raspberry Pi Camera.

def capture_image():
    """
    Initializes the Picamera2, shows a preview, and captures a still image.
    """
    print("Initializing camera...")
    
    # Create an instance of the Picamera2 class.
    # This class provides the main interface to the camera.
    picam2 = Picamera2()
    
    try:
        # Create a preview window. This will open a window on your desktop
        # showing what the camera sees.
        picam2.start_preview()
        
        # Start the camera.
        picam2.start()
        
        # Give the camera sensor some time to adjust to the light conditions.
        # This prevents the first few frames from being underexposed.
        print("Camera preview started. Waiting 2 seconds for sensor to adjust...")
        time.sleep(2)
        
        # Create a unique filename for the image using a timestamp.
        # This prevents overwriting previous photos.
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"capture-{timestamp}.jpg"
        
        # Capture a still image and save it to the specified filename.
        print(f"Capturing image and saving to {filename}...")
        picam2.capture_file(filename)
        
        print("Image captured successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Stop the camera and the preview to release the hardware resources.
        # This is a crucial step to prevent errors on subsequent runs.
        picam2.stop_preview()
        picam2.stop()
        print("Camera stopped and resources released.")

if __name__ == "__main__":
    capture_image()
