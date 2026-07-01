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

        self.lost_counter = 0
        self.MAX_LOST = 2

    def recover(self):

        print(" -> [RECOVERY]")

        self.r.set_leds("RED")

        self.r.stop()
        time.sleep(0.1)

        # contre-braquage
        if self.r.last_dir > 90:
            escape_angle = 40

        elif self.r.last_dir < 90:
            escape_angle = 140

        else:
            escape_angle = 90

        self.r.steer(escape_angle)

        # recul
        self.r.drive(-0.20)
        time.sleep(0.5)

        self.r.stop()
        time.sleep(0.1)

        # balayage intelligent
        for angle in [escape_angle, 90, 180 - escape_angle]:

            self.r.steer(angle)
            self.r.drive(0.20)

            for _ in range(10):

                L = self.r.L.value
                M = self.r.M.value
                R = self.r.R.value

                if (L, M, R) != (0, 0, 0):

                    print(" -> Ligne retrouvee")

                    self.r.set_leds("GREEN")
                    self.lost_counter = 0
                    return

                time.sleep(0.03)

        self.r.stop()

    def run(self):

        SPEED = 0.15

        print("Suivi de ligne actif")

        while True:

            dist = self.r.dist.distance

            L = self.r.L.value
            M = self.r.M.value
            R = self.r.R.value

            print(
                f"Capteurs=({L},{M},{R}) "
                f"Dist={dist:.2f} "
                f"Dir={self.r.last_dir}"
            )

            # =================================================
            # EVITEMENT OBSTACLE
            # =================================================

            if (0 < dist < 0.25):

                print(" -> OBSTACLE")

                self.r.stop()
                continue

            # =================================================
            # CENTRE
            # =================================================

            if (L, M, R) == (0, 1, 0):

                self.lost_counter = 0

                self.r.set_leds("GREEN")

                self.r.steer(90)
                self.r.drive(0.30)

                self.r.last_dir = 90

            # =================================================
            # VIRAGE GAUCHE
            # =================================================

            elif (L, M, R) == (1, 1, 0):

                self.lost_counter = 0

                self.r.set_leds("GREEN")

                self.r.steer(120)
                self.r.drive(SPEED*1.2)

                self.r.last_dir = 120

            elif (L, M, R) == (1, 0, 0):

                self.lost_counter = 0

                self.r.set_leds("GREEN")

                self.r.steer(140)
                self.r.drive(SPEED*1.2)

                self.r.last_dir = 140

            # =================================================
            # VIRAGE DROITE
            # =================================================

            elif (L, M, R) == (0, 1, 1):

                self.lost_counter = 0

                self.r.set_leds("GREEN")

                self.r.steer(60)
                self.r.drive(SPEED*1.2)

                self.r.last_dir = 60

            elif (L, M, R) == (0, 0, 1):

                self.lost_counter = 0

                self.r.set_leds("GREEN")

                self.r.steer(40)
                self.r.drive(SPEED*1.2)

                self.r.last_dir = 40

            # =================================================
            # TROU DANS LA LIGNE
            # =================================================

            elif (L, M, R) == (0, 0, 0):
              
                #self.lost_counter += 1

                if ((75 < self.r.last_dir < 115)):
                 #self.lost_counter < self.MAX_LOST:

                    print(" -> Survol trou")

                    self.r.steer(self.r.last_dir)
                    self.r.drive(SPEED*1.2)

                else:

                    print(" -> Perte reelle")

                    self.recover()

            # =================================================
            # INTERSECTION
            # =================================================

            elif (L, M, R) == (1, 1, 1):

                self.lost_counter = 0

                self.r.steer(90)
                self.r.drive(SPEED)

            # =================================================
            # CAS PARASITE
            # =================================================

            else:

                self.r.steer(self.r.last_dir)
                self.r.drive(SPEED * 0.8)

            time.sleep(0.02)

if __name__ == "__main__":
    follower = LineFollower()
    try: follower.run()
    finally: follower.r.stop()
