#!/usr/bin/env python3
"""
tache10.py

Tâche 10 : Suivi de source lumineuse et obstacle.

Fonctionnement :
- M : démarre le robot en marche avant et active le suivi de lumière.
- A/a : arrêt immédiat manuel.
- Le robot oriente sa direction vers une source lumineuse.
- Si un obstacle est détecté à moins de 20 cm :
    1. arrêt du robot ;
    2. activation des feux de détresse ;
    3. attente de 1 seconde ;
    4. recul du robot d'environ 30 cm à vitesse réduite avec "Bip Bip" ;
    5. arrêt pendant 2 secondes ;
    6. reprise automatique du suivi de lumière.

Le recul de 30 cm est approximatif : il dépend de la vitesse, de la batterie et du sol.
Il faudra ajuster REVERSE_DURATION_S après test réel.
"""

import select
import sys
import time

import RPi.GPIO as GPIO

import led_control
from distance_ultrasons import UltrasonicSensor
from motor2 import Dir_forward, Dir_backward, Motor
from pilotage_servo import ServoController
from task8_light_tracking import ADS7830
from WS2812_LED1 import LED


class RobotTask10:
    def __init__(self):
        # Obstacle
        self.OBSTACLE_LIMIT_MM = 200

        # Moteur
        self.MOTOR_SPEED = 20
        self.REVERSE_SPEED = 15
        self.ACCEL_PENTE = 1.0
        self.DECEL_PENTE = 2.0
        self.MOTOR_CHANNEL = 1

        # Délais
        self.MAIN_LOOP_DELAY = 0.02
        self.HAZARD_BLINK_DELAY = 0.4
        self.WAIT_BEFORE_REVERSE_S = 1.0
        self.REVERSE_DURATION_S = 1.2
        self.PAUSE_AFTER_REVERSE_S = 2.0
        self.BEEP_DELAY_S = 0.35

        # Capteurs
        self.LIGHT_SENSOR_CHANNEL = 1
        self.SERVO_CHANNEL = 0
        self.ULTRASONIC_TRIGGER_PIN = 23
        self.ULTRASONIC_ECHO_PIN = 24
        self.ULTRASONIC_MAX_DISTANCE_M = 2

        # LEDs
        self.HAT_LED_CHANNELS = (11, 12, 13)

        self.LEFT_RGB = {
            "R": 14,
            "G": 15,
            "B": 16
        }

        self.RIGHT_RGB = {
            "R": 17,
            "G": 18,
            "B": 19
        }

        # États possibles :
        # STOPPED, RUNNING, OBSTACLE_WAIT, REVERSING, PAUSE_AFTER_REVERSE
        self.state = "STOPPED"
        self.state_start_time = 0

        self.hazard_active = False
        self.hazard_state = False
        self.last_hazard_blink = 0
        self.last_beep_time = 0

        # Objets matériels
        self.motor_controller = None
        self.servo_controller = None
        self.ultrasonic_sensor = None
        self.adc = None
        self.ws_led = None

    # ============================================================
    # INITIALISATION
    # ============================================================

    def setup(self):
        print("Initialisation du robot pour la tâche 10...")

        self.motor_controller = Motor()

        self.servo_controller = ServoController(
            rotation_delay=0.001,
            startup_center_channels=(0,)
        )
        self.servo_controller.center_servos_on_startup()

        self.ultrasonic_sensor = UltrasonicSensor(
            trigger_pin=self.ULTRASONIC_TRIGGER_PIN,
            echo_pin=self.ULTRASONIC_ECHO_PIN,
            max_distance=self.ULTRASONIC_MAX_DISTANCE_M
        )

        self.adc = ADS7830()

        led_control.switchSetup()

        self.ws_led = LED()

        self.stop_hazard_lights()
        self.set_ws2812_color(0, 0, 0)

        print("Initialisation terminée.\n")
        self.print_menu()

    def print_menu(self):
        print("Commandes disponibles :")
        print("M      : démarrer le suivi de lumière")
        print("A / a  : arrêt immédiat")
        print("CTRL+C : quitter le programme\n")

    # ============================================================
    # CLAVIER
    # ============================================================

    def read_keyboard_command(self):
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.readline().strip()

        return None

    def handle_keyboard_command(self, command):
        if command == "M":
            print("Commande reçue : M")
            self.start_light_following()

        elif command in ("A", "a"):
            print("Commande reçue : arrêt manuel")
            self.manual_stop()

        elif command != "":
            print(f"Commande inconnue : {command}")
            print("Commandes valides : M, A, a")

    # ============================================================
    # MOTEUR
    # ============================================================

    def update_motor(self):
        if self.motor_controller is None:
            return

        try:
            self.motor_controller.update()
        except Exception as error:
            print("Erreur update moteur :", error)

    def motor_forward(self, speed=None):
        if self.motor_controller is None:
            return

        if speed is None:
            speed = self.MOTOR_SPEED

        self.motor_controller.setSpeed(
            Dir_forward,
            speed,
            pente=self.ACCEL_PENTE,
            channel=self.MOTOR_CHANNEL
        )

    def motor_backward(self, speed=None):
        if self.motor_controller is None:
            return

        if speed is None:
            speed = self.REVERSE_SPEED

        self.motor_controller.setSpeed(
            Dir_backward,
            speed,
            pente=self.ACCEL_PENTE,
            channel=self.MOTOR_CHANNEL
        )

    def motor_stop_smooth(self):
        if self.motor_controller is None:
            return

        self.motor_controller.setSpeed(
            Dir_forward,
            0,
            pente=self.DECEL_PENTE,
            channel=self.MOTOR_CHANNEL
        )

    def motor_stop_immediate(self):
        if self.motor_controller is None:
            return

        try:
            self.motor_controller.motorStop(
                channel=self.MOTOR_CHANNEL,
                pente=self.DECEL_PENTE
            )
        except TypeError:
            self.motor_controller.motorStop(self.MOTOR_CHANNEL)

    # ============================================================
    # SUIVI DE LUMIÈRE
    # ============================================================

    def get_light_angle(self):
        if self.adc is None:
            return 90

        try:
            return self.adc.analogtoangle(chn=self.LIGHT_SENSOR_CHANNEL)

        except Exception as error:
            print("Erreur lecture capteur de lumière :", error)
            return 90

    def update_light_tracking(self):
        if self.servo_controller is None:
            return

        angle = self.get_light_angle()

        try:
            self.servo_controller.set_angle(self.SERVO_CHANNEL, angle)

        except Exception as error:
            print("Erreur pilotage servo lumière :", error)

    def start_light_following(self):
        print("Démarrage du suivi de lumière.")

        self.stop_hazard_lights()
        self.set_ws2812_color(0, 80, 0)

        self.motor_forward(self.MOTOR_SPEED)

        self.state = "RUNNING"
        self.state_start_time = time.time()

    # ============================================================
    # ULTRASON
    # ============================================================

    def get_distance_mm(self):
        if self.ultrasonic_sensor is None:
            return None

        try:
            return self.ultrasonic_sensor.get_distance_mm()

        except Exception as error:
            print("Erreur lecture capteur ultrason :", error)
            return None

    def obstacle_detected(self):
        distance = self.get_distance_mm()

        if distance is None:
            return False

        print(f"Distance : {distance:.1f} mm")

        return distance < self.OBSTACLE_LIMIT_MM

    # ============================================================
    # LEDS
    # ============================================================

    def set_ws2812_color(self, red, green, blue):
        if self.ws_led is not None:
            self.ws_led.colorWipe(red, green, blue)

    def set_front_rgb(self, left_red, left_green, left_blue, right_red, right_green, right_blue):
        led_control.switch_rgb_led(self.LEFT_RGB["R"], left_red)
        led_control.switch_rgb_led(self.LEFT_RGB["G"], left_green)
        led_control.switch_rgb_led(self.LEFT_RGB["B"], left_blue)

        led_control.switch_rgb_led(self.RIGHT_RGB["R"], right_red)
        led_control.switch_rgb_led(self.RIGHT_RGB["G"], right_green)
        led_control.switch_rgb_led(self.RIGHT_RGB["B"], right_blue)

    def set_hazard_leds_on(self):
        for channel in self.HAT_LED_CHANNELS:
            led_control.switch_hat_led(channel, 1)

        self.set_front_rgb(
            1, 0, 0,
            1, 0, 0
        )

        self.set_ws2812_color(255, 0, 0)

    def set_hazard_leds_off(self):
        led_control.set_all_switch_off()
        self.set_ws2812_color(0, 0, 0)

    def start_hazard_lights(self):
        self.hazard_active = True
        self.hazard_state = False
        self.last_hazard_blink = 0
        self.set_hazard_leds_off()

    def stop_hazard_lights(self):
        self.hazard_active = False
        self.hazard_state = False
        self.set_hazard_leds_off()

    def update_hazard_lights(self):
        if not self.hazard_active:
            return

        current_time = time.time()

        if current_time - self.last_hazard_blink < self.HAZARD_BLINK_DELAY:
            return

        self.last_hazard_blink = current_time
        self.hazard_state = not self.hazard_state

        if self.hazard_state:
            self.set_hazard_leds_on()
        else:
            self.set_hazard_leds_off()

    # ============================================================
    # BIP BIP
    # ============================================================

    def beep_step(self):
        current_time = time.time()

        if current_time - self.last_beep_time < self.BEEP_DELAY_S:
            return

        self.last_beep_time = current_time

        print("Bip Bip")
        print("\a", end="")

    # ============================================================
    # SCÉNARIO OBSTACLE
    # ============================================================

    def start_obstacle_sequence(self):
        print("Obstacle détecté : arrêt du robot et activation des feux de détresse.")

        self.motor_stop_smooth()
        self.start_hazard_lights()

        self.state = "OBSTACLE_WAIT"
        self.state_start_time = time.time()

    def update_obstacle_wait(self):
        current_time = time.time()

        if current_time - self.state_start_time >= self.WAIT_BEFORE_REVERSE_S:
            print("Début du recul d'environ 30 cm à vitesse réduite.")

            self.motor_backward(self.REVERSE_SPEED)

            self.state = "REVERSING"
            self.state_start_time = current_time
            self.last_beep_time = 0

    def update_reversing(self):
        current_time = time.time()

        self.beep_step()

        if current_time - self.state_start_time >= self.REVERSE_DURATION_S:
            print("Fin du recul. Arrêt pendant 2 secondes.")

            self.motor_stop_smooth()

            self.state = "PAUSE_AFTER_REVERSE"
            self.state_start_time = current_time

    def update_pause_after_reverse(self):
        current_time = time.time()

        if current_time - self.state_start_time >= self.PAUSE_AFTER_REVERSE_S:
            print("Reprise du suivi de lumière.")

            self.stop_hazard_lights()
            self.start_light_following()

    # ============================================================
    # ARRÊT
    # ============================================================

    def manual_stop(self):
        print("Arrêt immédiat du robot.")

        self.motor_stop_immediate()
        self.stop_hazard_lights()
        self.set_ws2812_color(0, 0, 0)

        self.state = "STOPPED"
        self.state_start_time = time.time()

    # ============================================================
    # BOUCLE PRINCIPALE
    # ============================================================

    def update(self):
        self.update_motor()

        command = self.read_keyboard_command()

        if command is not None:
            self.handle_keyboard_command(command)

        if self.state == "RUNNING":
            self.update_light_tracking()

            if self.obstacle_detected():
                self.start_obstacle_sequence()

        elif self.state == "OBSTACLE_WAIT":
            self.update_obstacle_wait()

        elif self.state == "REVERSING":
            self.update_reversing()

        elif self.state == "PAUSE_AFTER_REVERSE":
            self.update_pause_after_reverse()

        elif self.state == "STOPPED":
            pass

        self.update_hazard_lights()

    def run(self):
        self.setup()

        try:
            while True:
                self.update()
                time.sleep(self.MAIN_LOOP_DELAY)

        except KeyboardInterrupt:
            print("\nFin de programme par Ctrl+C.")

        finally:
            self.cleanup()

    # ============================================================
    # NETTOYAGE
    # ============================================================

    def cleanup(self):
        print("Nettoyage final en cours...")

        try:
            if self.motor_controller is not None:
                self.motor_stop_immediate()
                self.motor_controller.destroy()

        except Exception as error:
            print("Erreur nettoyage moteur :", error)

        try:
            if self.servo_controller is not None:
                self.servo_controller.close()

        except Exception as error:
            print("Erreur nettoyage servo :", error)

        try:
            if self.ultrasonic_sensor is not None:
                self.ultrasonic_sensor.close()

        except Exception as error:
            print("Erreur nettoyage ultrason :", error)

        try:
            self.stop_hazard_lights()

        except Exception as error:
            print("Erreur extinction LED :", error)

        try:
            GPIO.cleanup()

        except Exception as error:
            print("Erreur GPIO cleanup :", error)

        print("Nettoyage final réalisé.")


def main():
    robot = RobotTask10()
    robot.run()


if __name__ == "__main__":
    main()
