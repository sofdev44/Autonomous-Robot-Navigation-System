#!/usr/bin/env python3
"""
tache9_robot.py

Version orientée objet de la tâche 9 avec une classe Robot.

Fonctionnement :
- M : démarre le robot en marche avant
- A/a : arrêt immédiat
- Si le capteur ultrason détecte un obstacle trop proche :
    - le robot s'arrête progressivement
    - les feux de détresse clignotent
- CTRL+C : quitte le programme proprement

Important :
Cette version utilise motor_controller.update() à chaque tour de boucle.
Cela permet au moteur de gérer ses transitions progressivement sans bloquer
la lecture du clavier ni celle du capteur ultrason.
"""

import select
import sys
import time

import RPi.GPIO as GPIO

import led_control
from distance_ultrasons import UltrasonicSensor
from motor2 import Dir_forward, Motor
from WS2812_LED1 import LED


class Robot:
    """
    Classe principale de la tâche 9.

    Elle regroupe :
    - le moteur
    - le capteur ultrason
    - les LED HAT
    - les LED RGB avant
    - les LED WS2812
    - les commandes clavier
    - la sécurité obstacle
    - les feux de détresse
    """

    def __init__(
        self,
        obstacle_limit_mm=200,
        motor_speed=30,
        acceleration_pente=50,
        deceleration_pente=50,
        motor_channel=1,
        main_loop_delay=0.05,
        hazard_blink_delay=0.4,
        ultrasonic_trigger_pin=23,
        ultrasonic_echo_pin=24,
        ultrasonic_max_distance_m=2
    ):
        """
        Initialise les paramètres du robot.

        Les objets matériels sont créés dans setup().
        """

        # Paramètres obstacle
        self.obstacle_limit_mm = obstacle_limit_mm

        # Paramètres moteur
        self.motor_speed = motor_speed
        self.acceleration_pente = acceleration_pente
        self.deceleration_pente = deceleration_pente
        self.motor_channel = motor_channel

        # Paramètres boucle principale
        self.main_loop_delay = main_loop_delay

        # Paramètres feux de détresse
        self.hazard_blink_delay = hazard_blink_delay

        # Paramètres ultrason
        self.ultrasonic_trigger_pin = ultrasonic_trigger_pin
        self.ultrasonic_echo_pin = ultrasonic_echo_pin
        self.ultrasonic_max_distance_m = ultrasonic_max_distance_m

        # LED HAT
        self.hat_led_channels = (11, 12, 13)

        # Codes LED RGB selon led_control.py :
        # 14 = left_R
        # 15 = left_G
        # 16 = left_B
        # 17 = right_R
        # 18 = right_G
        # 19 = right_B
        self.left_rgb = {
            "R": 14,
            "G": 15,
            "B": 16
        }

        self.right_rgb = {
            "R": 17,
            "G": 18,
            "B": 19
        }

        # États internes
        self.robot_running = False
        self.hazard_active = False
        self.hazard_state = False
        self.last_hazard_blink = 0

        # Objets matériels
        self.motor_controller = None
        self.ultrasonic_sensor = None
        self.ws_led = None

    # =========================================================================
    # INITIALISATION
    # =========================================================================

    def setup(self):
        """
        Initialise le moteur, le capteur ultrason et les LED.
        """

        print("Initialisation du robot...")

        self.motor_controller = Motor()

        self.ultrasonic_sensor = UltrasonicSensor(
            trigger_pin=self.ultrasonic_trigger_pin,
            echo_pin=self.ultrasonic_echo_pin,
            max_distance=self.ultrasonic_max_distance_m
        )

        led_control.switchSetup()

        self.ws_led = LED()

        self.stop_hazard_lights()

        print("Initialisation terminée.\n")
        self.print_menu()

    def print_menu(self):
        """
        Affiche les commandes disponibles.
        """

        print("Commandes disponibles :")
        print("M      : marche avant")
        print("A / a  : arrêt immédiat")
        print("CTRL+C : quitter le programme\n")

    # =========================================================================
    # COMMANDES CLAVIER
    # =========================================================================

    def read_keyboard_command(self):
        """
        Lit une commande clavier sans bloquer la boucle principale.

        L'utilisateur doit appuyer sur Entrée après la commande.
        """

        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.readline().strip()

        return None

    def handle_keyboard_command(self, command):
        """
        Exécute l'action associée à une commande clavier.
        """

        if command == "M":
            print("Commande reçue : M")
            self.stop_hazard_lights()
            self.start_robot()

        elif command in ("A", "a"):
            print("Commande reçue : arrêt manuel")
            self.stop_robot_immediate()
            self.stop_hazard_lights()

        elif command != "":
            print(f"Commande inconnue : {command}")
            print("Commandes valides : M, A, a")

    # =========================================================================
    # MOTEUR
    # =========================================================================

    def update_motor(self):
        """
        Met à jour la transition progressive du moteur.

        Cette méthode doit être appelée à chaque tour de boucle.
        Elle permet au moteur d'accélérer ou de freiner progressivement
        pendant que le programme continue de lire les capteurs.
        """

        if self.motor_controller is None:
            return

        try:
            self.motor_controller.update()
        except AttributeError:
            print("[ERREUR] La classe Motor ne contient pas de méthode update().")
        except TypeError as error:
            print("[ERREUR] Appel incorrect de Motor.update().")
            print("Vérifie que update() ne prend aucun paramètre.")
            print("Détail :", error)
        except Exception as error:
            print("[ERREUR] Erreur pendant Motor.update() :", error)

    def start_robot(self):
        """
        Démarre le robot en marche avant.
        """

        if self.motor_controller is None:
            print("Erreur : moteur non initialisé.")
            return

        print("Démarrage du robot en marche avant.")

        self.motor_controller.setSpeed(
            Dir_forward,
            self.motor_speed,
            pente=self.acceleration_pente,
            channel=self.motor_channel
        )

        self.robot_running = True

    def stop_robot_smooth(self):
        """
        Demande un arrêt progressif du robot.
        """

        if self.motor_controller is None:
            return

        print("Arrêt progressif du robot.")

        try:
            self.motor_controller.setSpeed(
                Dir_forward,
                0,
                pente=self.deceleration_pente,
                channel=self.motor_channel
            )

        except Exception as error:
            print("Erreur pendant l'arrêt progressif :", error)
            print("Arrêt immédiat par sécurité.")
            self.stop_robot_immediate()
            return

        # On indique que le robot ne doit plus être considéré comme en mouvement.
        # La méthode update_motor() continue quand même d'être appelée dans la boucle.
        self.robot_running = False

    def stop_robot_immediate(self):
        """
        Arrête immédiatement le robot.
        """

        if self.motor_controller is None:
            return

        print("Arrêt immédiat du robot.")

        try:
            self.motor_controller.motorStop(
                channel=self.motor_channel,
                pente=self.deceleration_pente
            )
        except TypeError:
            self.motor_controller.motorStop(self.motor_channel)

        self.robot_running = False

    # =========================================================================
    # CAPTEUR ULTRASON
    # =========================================================================

    def get_distance_mm(self):
        """
        Retourne la distance mesurée par le capteur ultrason en millimètres.
        """

        if self.ultrasonic_sensor is None:
            return None

        try:
            return self.ultrasonic_sensor.get_distance_mm()

        except Exception as error:
            print("Erreur lecture capteur ultrason :", error)
            return None

    def obstacle_detected(self):
        """
        Retourne True si un obstacle est plus proche que la limite configurée.
        """

        distance = self.get_distance_mm()

        if distance is None:
            return False

        print(f"Distance : {distance:.2f} mm")

        return distance < self.obstacle_limit_mm

    def check_obstacle_while_running(self):
        """
        Vérifie les obstacles uniquement lorsque le robot avance.
        """

        if self.robot_running and self.obstacle_detected():
            self.stop_robot_smooth()
            self.start_hazard_lights()

    # =========================================================================
    # LED WS2812
    # =========================================================================

    def set_ws2812_color(self, red, green, blue):
        """
        Change la couleur des LED WS2812.
        """

        if self.ws_led is not None:
            self.ws_led.colorWipe(red, green, blue)

    # =========================================================================
    # LED HAT + RGB AVANT
    # =========================================================================

    def set_front_rgb(self, left_red, left_green, left_blue, right_red, right_green, right_blue):
        """
        Contrôle les deux LED RGB avant.

        Chaque paramètre vaut :
        - 1 pour allumer la couleur
        - 0 pour éteindre la couleur

        led_control.switch_rgb_led() gère déjà le fonctionnement inversé
        des LED RGB.
        """

        led_control.switch_rgb_led(self.left_rgb["R"], left_red)
        led_control.switch_rgb_led(self.left_rgb["G"], left_green)
        led_control.switch_rgb_led(self.left_rgb["B"], left_blue)

        led_control.switch_rgb_led(self.right_rgb["R"], right_red)
        led_control.switch_rgb_led(self.right_rgb["G"], right_green)
        led_control.switch_rgb_led(self.right_rgb["B"], right_blue)

    def set_hazard_leds_on(self):
        """
        Allume les feux de détresse.
        """

        for channel in self.hat_led_channels:
            led_control.switch_hat_led(channel, 1)

        self.set_front_rgb(
            1, 0, 0,
            1, 0, 0
        )

        self.set_ws2812_color(255, 0, 0)

    def set_hazard_leds_off(self):
        """
        Éteint les feux de détresse.
        """

        led_control.set_all_switch_off()
        self.set_ws2812_color(0, 0, 0)

    def hazard_lights_on_step(self):
        """
        Fait clignoter les feux de détresse sans bloquer le programme.
        """

        current_time = time.time()

        if current_time - self.last_hazard_blink < self.hazard_blink_delay:
            return

        self.last_hazard_blink = current_time
        self.hazard_state = not self.hazard_state

        if self.hazard_state:
            self.set_hazard_leds_on()
        else:
            self.set_hazard_leds_off()

    def start_hazard_lights(self):
        """
        Active le mode feux de détresse.
        """

        print("Obstacle détecté : activation des feux de détresse.")

        self.hazard_active = True
        self.hazard_state = False
        self.last_hazard_blink = 0

        self.set_hazard_leds_off()

    def stop_hazard_lights(self):
        """
        Désactive les feux de détresse.
        """

        self.hazard_active = False
        self.hazard_state = False
        self.set_hazard_leds_off()

    def update_hazard_lights(self):
        """
        Met à jour les feux de détresse si le mode est actif.
        """

        if self.hazard_active:
            self.hazard_lights_on_step()

    # =========================================================================
    # BOUCLE PRINCIPALE
    # =========================================================================

    def update(self):
        """
        Une itération de la boucle principale.

        Ordre important :
        1. update_motor()
        2. lecture clavier
        3. vérification obstacle
        4. mise à jour des feux de détresse
        """

        self.update_motor()

        command = self.read_keyboard_command()

        if command is not None:
            self.handle_keyboard_command(command)

        self.check_obstacle_while_running()
        self.update_hazard_lights()

    def run(self):
        """
        Lance le programme principal.
        """

        self.setup()

        try:
            while True:
                self.update()
                time.sleep(self.main_loop_delay)

        except KeyboardInterrupt:
            print("\nFin de programme par Ctrl+C.")

        finally:
            self.cleanup()

    # =========================================================================
    # NETTOYAGE
    # =========================================================================

    def cleanup(self):
        """
        Arrête le robot et libère proprement les ressources matérielles.
        """

        print("Nettoyage final en cours...")

        try:
            if self.motor_controller is not None:
                try:
                    self.motor_controller.motorStop(
                        channel=self.motor_channel,
                        pente=self.deceleration_pente
                    )
                except TypeError:
                    self.motor_controller.motorStop(self.motor_channel)

                self.motor_controller.destroy()

        except Exception as error:
            print("Erreur nettoyage moteur :", error)

        try:
            if self.ultrasonic_sensor is not None:
                self.ultrasonic_sensor.close()
        except Exception as error:
            print("Erreur nettoyage capteur ultrason :", error)

        try:
            self.set_hazard_leds_off()
        except Exception as error:
            print("Erreur extinction LEDs :", error)

        try:
            GPIO.cleanup()
        except Exception as error:
            print("Erreur GPIO cleanup :", error)

        print("Nettoyage final réalisé.")


def main():
    robot = Robot()
    robot.run()


if __name__ == "__main__":
    main()
