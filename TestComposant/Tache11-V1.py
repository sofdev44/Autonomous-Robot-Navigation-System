import time
import busio
from board import SCL, SDA
from adafruit_pca9685 import PCA9685
from adafruit_motor import motor, servo
from gpiozero import InputDevice, DistanceSensor
import led_control as led

# =====================================================
# ROBOT & NAVIGATION
# =====================================================
class Robot:
    def __init__(self):
        self.i2c = busio.I2C(SCL, SDA)
        self.pca_motor = PCA9685(self.i2c, address=0x5f); self.pca_motor.frequency = 1000
        self.motor = motor.DCMotor(self.pca_motor.channels[15], self.pca_motor.channels[14])
        self.pca_servo = PCA9685(self.i2c, address=0x5f); self.pca_servo.frequency = 50
        self.steer_servo = servo.Servo(self.pca_servo.channels[0])
        self.L, self.M, self.R = InputDevice(22), InputDevice(27), InputDevice(17)
        self.dist = DistanceSensor(echo=24, trigger=23, max_distance=1)
        self.last_dir = 90
        led.switchSetup()

    def set_leds(self, status):
        for code in range(14, 20): led.switch_rgb_led(code, 0)
        if status == "GREEN": 
            led.switch_rgb_led(15, 1); led.switch_rgb_led(18, 1)
        elif status == "RED": 
            led.switch_rgb_led(14, 1); led.switch_rgb_led(17, 1)

    def drive(self, speed): self.motor.throttle = speed
    def steer(self, angle): self.steer_servo.angle = max(40, min(140, angle)); self.last_dir = angle
    def stop(self): self.motor.throttle = 0

class LineFollower:
    def __init__(self):
        self.r = Robot()

    def recover(self):
        # 1. ARReT TOTAL IMMeDIAT
        self.r.stop() 
        print(" -> [OBSTACLE] Arret d'urgence detecte !")
        
        self.r.set_leds("RED")
        
        # 2. Sequence de recul et realignement
        escape_angle = 40 if self.r.last_dir > 90 else 140
        self.r.steer(escape_angle)
        
        self.r.drive(-0.15)
        time.sleep(0.5) # Recul
        
        self.r.stop()
        self.r.steer(90) # Recentrage
        time.sleep(0.3)
        self.r.set_leds("GREEN") # On repasse en mode normal

    def run(self):
        SPEED = 0.20
        print("Suivi de ligne actif. Priorite Obstacle activee.")
        while True:
            # LECTURE PRIORITAIRE
            dist = self.r.dist.distance
            L, M, R = self.r.L.value, self.r.M.value, self.r.R.value
            
            # SeCURITe ABSOLUE (Obstacle)
            if dist < 0.20 and dist > 0.0: # dist > 0 evite les erreurs de lecture capteur a 0
                self.recover()
                continue # Force le redemarrage de la boucle apres le recul
            
            # Logique de suivi
            print(f"Capteurs: ({L}, {M}, {R}) | Dist: {dist:.2f}m")
            
            if (L, M, R) == (0, 1, 0):
                self.r.set_leds("GREEN")
                self.r.steer(90); self.r.drive(SPEED + 0.1)
            elif (L, M, R) in [(1, 0, 0), (1, 1, 0)]:
                self.r.set_leds("GREEN")
                self.r.steer(140); self.r.drive(SPEED)
            elif (L, M, R) in [(0, 0, 1), (0, 1, 1)]:
                self.r.set_leds("GREEN")
                self.r.steer(40); self.r.drive(SPEED)
            elif (L, M, R) == (0, 0, 0):
                print(" -> [PERTE] Recherche ligne...")
                self.recover()
            else:
                self.r.steer(90); self.r.drive(SPEED)

            time.sleep(0.02)

    def run(self):
        SPEED = 0.20
        print("Suivi de ligne actif. Affichage des capteurs (L, M, R) :")
        while True:
            # Lecture et affichage des capteurs
            L, M, R = self.r.L.value, self.r.M.value, self.r.R.value
            print(f"Capteurs: ({L}, {M}, {R}) | Dir: {self.r.last_dir}")

            # Securite Obstacle
            if self.r.dist.distance < 0.20:
                print(" -> [OBSTACLE] Recul d'urgence")
                self.recover()
                continue
            
            # Logique de suivi
            if (L, M, R) == (0, 1, 0): # Centre
                self.r.set_leds("GREEN")
                self.r.steer(90); self.r.drive(SPEED + 0.1)
            elif (L, M, R) == (1, 0, 0) or (L, M, R) == (1, 1, 0): # Gauche
                self.r.set_leds("GREEN")
                self.r.steer(140); self.r.drive(SPEED)
            elif (L, M, R) == (0, 0, 1) or (L, M, R) == (0, 1, 1): # Droite
                self.r.set_leds("GREEN")
                self.r.steer(40); self.r.drive(SPEED)
            else: # Perte de ligne (0,0,0) ou croisements (1,1,1)
                if (L, M, R) == (0, 0, 0):
                    print(" -> [PERTE] Recherche ligne...")
                    self.recover()
                else:
                    self.r.steer(90); self.r.drive(SPEED)

            time.sleep(0.04)

if __name__ == "__main__":
    follower = LineFollower()
    try: follower.run()
    finally: follower.r.stop()
