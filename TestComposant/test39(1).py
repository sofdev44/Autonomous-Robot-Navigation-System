import time
from motor2 import *
from pilotage_servo import *
from distance_ultrasons import *
from buzzer import *
from task6_line_following import *
from WS2812_LED1 import *
from led_control import *

# =====================================================
# ROBOT & NAVIGATION
# =====================================================
class Robot:
    def __init__(self):
        self.buzzer = MidiBuzzer()
        self.capteurSuiviLigne = LineFollower()
        self.direction = ServoController()
         # self.ledAvant = ()
        self.moteur = Motor()
        self.ultrasonic = UltrasonicSensor()
        self.led = LED()

    def set_leds(self, status):
        for code in range(14, 20): led.switch_rgb_led(code, 0)
        if status == "GREEN": 
            led.switch_rgb_led(15, 1); led.switch_rgb_led(18, 1)
        elif status == "RED": 
            led.switch_rgb_led(14, 1); led.switch_rgb_led(17, 1)

    def bip(self) :
        self.buzzer.play_note(57)

    def drive(self,direction,  speed) :
        self.moteur.setSpeed(direction ,speed)

    def stopEngine(self) :
        self.moteur.motorStop()



    def suiviLigne(self) :
        speed = 45
        reverse_speed = 35
        reverse_spd_slow = 35
        MOST_LEFT = 130
        MID_LEFT = 100
        MID_RIGHT = 80
        MOST_RIGHT = 50
        curtime = time.time()
        robot.drive(1,speed)
        robot.direction.configure_speed(1)
        timeonline = time.time()
        prvangle = 90
        while True:
            robot.moteur.update()
            robot.direction.update()

            
            etat = robot.capteurSuiviLigne.read()
            if ((time.time() - curtime) > 0.01) :
                if(etat == (0,0,0)) :
                    if((time.time() - timeonline) > 1):
                        if (robot.moteur.current_direction[0] == 1):
                            robot.led.colorWipe(255,0,0)
                            if (robot.direction.current_angles == 90):
                                robot.drive(-1,reverse_speed)
                                robot.direction.set_angle(0,(prvangle))
                                print("tout droit:")
                                robot.direction.print_angle(0)
                            else:
                                robot.drive(-1,reverse_spd_slow)
                                robot.direction.set_angle(0, (180 - robot.direction.current_angles[0]))
                                print("inverser l angle")
                                robot.direction.print_angle(0)
                    else:
                        robot.direction.set_angle(0,90)
                    
                else:
                    robot.drive(1, speed)
                    robot.led.colorWipe(0,255,0)
                    if(etat == (1,0,0)) : # Braquer à gauche
                        robot.direction.set_angle(0,MOST_LEFT)
                        curtime = time.time()
                        timeonline = 0
                        prvangle = MID_LEFT
                        

                    elif(etat == (0,0,1)) : # Braquer à droite
                        robot.direction.set_angle(0,MOST_RIGHT)
                        print("tourne a droit :" +str(MOST_RIGHT))
                        curtime = time.time()
                        timeonline = 0
                        prvangle = MID_RIGHT

                    elif(etat == (0,1,1)) :
                        robot.direction.set_angle(0, MID_RIGHT) # Tourner à droite de 20°
                        curtime = time.time()
                        timeonline = time.time() -0.3
                        prvangle = MID_RIGHT

                    elif(etat == (1,1,1)) : # Ligne noire => aller tout droit
                        robot.direction.set_angle(0,90)
                        robot.drive(1, speed)
                        curtime = time.time()
                        timeonline = time.time()
                        prvangle = 90

                    elif(etat == (1,1,0)) :
                        robot.direction.set_angle(0, MID_LEFT) # Tourner à gauche de 20°
                        curtime = time.time()
                        timeonline = time.time() -0.3
                        prvangle = MID_LEFT
                



if __name__ == '__main__':
    robot = Robot()
    
    try:
        robot.suiviLigne()
        #while True :
            #robot.ledAvant.warning()

    except KeyboardInterrupt:
        print("Fin du programme via le clavier.")
        robot.led.colorWipe(0, 0, 0)
        robot.direction.set_angle(0,90)
        robot.moteur.destroy()

