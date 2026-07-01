import cv2
import numpy as np
from picamera2 import Picamera2
from flask import Flask, Response
import signal
import sys
import config
from motor2 import Motor

from pilotage_servo import ServoController

app = Flask(__name__)
mot = Motor()

# --- CONFIGURATION ---
WIDTH, HEIGHT = 640, 480
STEERING_CHANNEL = 0
MOTOR_CHANNEL = 1
CAMERA_TILT_CHANNEL = 2
CAMERA_TILT_ANGLE = 60

# Initialisation Materiel
controller = ServoController(startup_center_channels=(0, CAMERA_TILT_CHANNEL))
controller.center_servos_on_startup()
print(f"Inclinaison de la camera (canal {CAMERA_TILT_CHANNEL}) a {CAMERA_TILT_ANGLE}...")
controller.set_angle(CAMERA_TILT_CHANNEL, CAMERA_TILT_ANGLE)

picam2 = Picamera2()
camera_config = picam2.create_video_configuration(main={"size": (WIDTH, HEIGHT), "format": "BGR888"})
picam2.configure(camera_config)
picam2.start()

# Gestion de l'arret
def signal_handler(sig, frame):
    print("\nArret en cours...")
    
    picam2.stop()
    
    if 'mot' in globals():
      mot.destroy() # pour liberer propremebt depuis motor2
      print("moteurs stoppe")
    
    controller.set_angle(CAMERA_TILT_CHANNEL, 90) # On remonte la camera
    controller.close()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def get_line_centers(mask):
    print("dans get line ")
    h, w = mask.shape
    mid = h // 2
    def find_centroid(img_segment):
        print("dans find centroid")
        M = cv2.moments(img_segment)
        if M["m00"] > 500: # Seuil minimal pour eviter le bruit
            return int(M["m10"] / M["m00"])
        return None
    return find_centroid(mask[0:mid, :]), find_centroid(mask[mid:h, :])

def generate_frames():
    print("dans generate frame")
    center_screen = WIDTH // 2
    
    lower_red1, upper_red1 = np.array([0, 160, 140]), np.array([10, 255, 255])
    lower_red2, upper_red2 = np.array([170, 160, 140]), np.array([180, 255, 255])
    
    while True:
        print("dans le while")
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Masque Rouge
        mask = cv2.inRange(hsv, np.array([0, 160, 140]), np.array([10, 255, 255])) + \
               cv2.inRange(hsv, np.array([170, 160, 140]), np.array([180, 255, 255]))
        
        x_haut, x_bas = get_line_centers(mask)
        
        mot.update()
        
        if x_bas is not None:
            print("dans le if x_bas")
            erreur = x_bas - center_screen
            angle = config.STRAIGHT_ANGLE - (erreur // 5)
            angle = max(config.RIGHT_HARD, min(config.LEFT_HARD, angle))    
            controller.set_angle(STEERING_CHANNEL, angle)
            
            vitesse_moteur = int(config.CENTER_SPEED * 300)
            mot.setSpeed(1, vitesse_moteur, pente=0.2, channel=1) 
                       
            cv2.line(frame, (center_screen, HEIGHT), (x_bas, HEIGHT // 2), (255, 255, 0), 3)
        else:
            print("dans le else")
            #vitesse_ralentie = int(config.RECENTER_SPEED * 100) a laisser si volonte de ne pas s'arrete a la fin de la ligne
            mot.setSpeed(1, 0, pente=1.0, channel=1) 
            cv2.putText(frame, "LIGNE PERDUE - ARRET", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")

@app.route("/")
def index():
    return "<html><body><h1>Suivi de ligne actif</h1><img src='/video'></body></html>"

@app.route("/video")
def video():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
