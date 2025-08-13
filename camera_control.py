from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
import time
import io
import threading
from threading import Lock

class CameraControl:
    def __init__(self):
        self.camera = Picamera2()
        self.lock = Lock()
        self.recording = False
        self.configure_camera()
        
    def configure_camera(self):
        # Configure camera for both preview and recording
        video_config = self.camera.create_video_configuration()
        self.camera.configure(video_config)
        self.camera.start()
        time.sleep(2)  # Allow camera to warm up
        
    def get_frame(self):
        while True:
            with self.lock:
                frame = self.camera.capture_array("main")
                ret, jpeg = cv2.imencode('.jpg', frame)
                if not ret:
                    continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
            time.sleep(0.1)
            
    def start_recording(self):
        if not self.recording:
            self.recording = True
            self.encoder = H264Encoder()
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            self.output = FfmpegOutput(f'recording_{timestamp}.mp4')
            self.camera.start_encoder(self.encoder, self.output)
            
    def stop_recording(self):
        if self.recording:
            self.recording = False
            self.camera.stop_encoder()
            
    def capture_image(self):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.camera.capture_file(f'capture_{timestamp}.jpg')