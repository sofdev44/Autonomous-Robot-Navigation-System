#!/usr/bin/env python3
"""
task7.py

Tâche 7 : Intégration des modules du robot Adeept PiCar-B.

Cette version utilise :
- motor2.py
- pilotage_servo.py
- led_control.py
- WS2812_LED1.py
- distance_ultrasons.py
- task6_line_following.py
- task8_suivi_lumiere.py

Correction importante :
- task6_line_following est maintenant utilisé avec la classe LineFollower.
"""

import time
import sys
import select

import motor2
import pilotage_servo
import led_control
import WS2812_LED1
import distance_ultrasons
import task6_line_following
import task8_light_tracking


# ============================================================
# PARAMÈTRES GÉNÉRAUX
# ============================================================

OBSTACLE_STOP_DISTANCE_MM = 200
DEFAULT_SPEED = 25
MOTOR_RAMP = 100

SERVO_CHANNEL_DIRECTION = 0
SERVO_CENTER_ANGLE = 90
SERVO_LEFT_ANGLE = 60
SERVO_RIGHT_ANGLE = 120

LOOP_DELAY = 0.05
DISPLAY_DELAY = 0.50
HAZARD_BLINK_DELAY = 0.30


# ============================================================
# CLAVIER NON BLOQUANT
# ============================================================

def read_key_non_blocking():
    """
    Lit une commande clavier sans bloquer le programme.
    """

    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.readline().strip().lower()

    return None


# ============================================================
# LED CLASSIQUES : HAT + RGB AVANT
# ============================================================

def set_front_rgb(left_rgb, right_rgb):
    """
    Contrôle les deux LED RGB avant.

    left_rgb et right_rgb sont des tuples :
    (R, G, B)
    """

    left_r, left_g, left_b = left_rgb
    right_r, right_g, right_b = right_rgb

    led_control.switch_rgb_led(14, left_r)
    led_control.switch_rgb_led(15, left_g)
    led_control.switch_rgb_led(16, left_b)

    led_control.switch_rgb_led(17, right_r)
    led_control.switch_rgb_led(18, right_g)
    led_control.switch_rgb_led(19, right_b)


def hazard_lights_step(state):
    """
    Fait une étape de clignotement des feux de détresse.
    """

    new_state = not state

    if new_state:
        led_control.switch_hat_led(11, 1)
        led_control.switch_hat_led(12, 1)
        led_control.switch_hat_led(13, 1)
        set_front_rgb((1, 0, 0), (1, 0, 0))
    else:
        led_control.switch_hat_led(11, 0)
        led_control.switch_hat_led(12, 0)
        led_control.switch_hat_led(13, 0)
        set_front_rgb((0, 0, 0), (0, 0, 0))

    return new_state


# ============================================================
# LED WS2812
# ============================================================

def ws2812_status_color(ws_led, status):
    """
    Change toutes les LED WS2812 selon l'état du robot.
    """

    if ws_led is None:
        return

    if status == "ready":
        ws_led.colorWipe(0, 80, 0)
    elif status == "moving":
        ws_led.colorWipe(0, 0, 80)
    elif status == "obstacle":
        ws_led.colorWipe(80, 0, 0)
    else:
        ws_led.colorWipe(0, 0, 0)


# ============================================================
# MOTEUR
# ============================================================

def motor_forward(motor):
    """
    Fait avancer le robot.
    """

    if motor is None:
        return

    motor.setSpeed(1, DEFAULT_SPEED, pente=MOTOR_RAMP, channel=1)
    print(f"[MOTEUR] Avance à {DEFAULT_SPEED}%")


def motor_backward(motor):
    """
    Fait reculer le robot.
    """

    if motor is None:
        return

    motor.setSpeed(-1, DEFAULT_SPEED, pente=MOTOR_RAMP, channel=1)
    print(f"[MOTEUR] Recule à {DEFAULT_SPEED}%")


def motor_stop(motor):
    """
    Arrête le moteur.
    """

    if motor is None:
        return

    try:
        motor.motorStop(channel=1, pente=MOTOR_RAMP)
        print("[MOTEUR] Stop")
    except Exception as error:
        print(f"[ERREUR] Arrêt moteur impossible : {error}")

        try:
            motor.motor1.throttle = 0
        except Exception:
            pass


# ============================================================
# SERVO
# ============================================================

def servo_center(servo_controller):
    """
    Centre le servomoteur de direction.
    """

    if servo_controller is None:
        return

    servo_controller.set_angle(SERVO_CHANNEL_DIRECTION, SERVO_CENTER_ANGLE)


def servo_left(servo_controller):
    """
    Tourne la direction à gauche.
    """

    if servo_controller is None:
        return

    servo_controller.set_angle(SERVO_CHANNEL_DIRECTION, SERVO_LEFT_ANGLE)


def servo_right(servo_controller):
    """
    Tourne la direction à droite.
    """

    if servo_controller is None:
        return

    servo_controller.set_angle(SERVO_CHANNEL_DIRECTION, SERVO_RIGHT_ANGLE)


# ============================================================
# CAPTEURS
# ============================================================

def read_ultrasonic_mm(ultrasonic):
    """
    Lit la distance ultrason en millimètres.
    """

    if ultrasonic is None:
        return None

    return ultrasonic.get_distance_mm()


def read_line_sensors(line_follower):
    """
    Lit les 3 capteurs de suivi de ligne avec la classe LineFollower.
    """

    if line_follower is None:
        return None

    return line_follower.read()


def read_light_sensors(adc):
    """
    Lit les deux capteurs de lumière.
    """

    if adc is None:
        return None

    left = adc.analogRead(0)
    right = adc.analogRead(1)

    return left, right


# ============================================================
# MENU
# ============================================================

def print_menu():
    print()
    print("=================================================")
    print("TÂCHE 7 - INTÉGRATION DES MODULES")
    print("=================================================")
    print("Commandes :")
    print("  m  : avancer")
    print("  b  : reculer")
    print("  a  : arrêt moteur")
    print("  g  : tourner à gauche")
    print("  d  : tourner à droite")
    print("  c  : centrer la direction")
    print("  s  : afficher l'état des capteurs")
    print("  l  : test LED avant")
    print("  w  : test LED WS2812")
    print("  q  : quitter")
    print("=================================================")
    print()


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():
    print_menu()

    motor = None
    ws_led = None
    ultrasonic = None
    line_follower = None
    adc = None
    servo_controller = None

    robot_is_moving = False
    obstacle_detected = False
    hazard_state = False
    last_hazard_time = 0
    last_display_time = 0

    try:
        # Initialisation LED HAT + RGB
        led_control.switchSetup()
        set_front_rgb((0, 1, 0), (0, 1, 0))
        print("[OK] LED HAT/RGB initialisées")

        # Initialisation WS2812
        ws_led = WS2812_LED1.LED()
        ws2812_status_color(ws_led, "ready")
        print("[OK] LED WS2812 initialisées")

        # Initialisation moteur
        motor = motor2.Motor()
        motor_stop(motor)
        print("[OK] Moteur initialisé")

        # Initialisation servo
        servo_controller = pilotage_servo.ServoController(
            rotation_delay=0.001,
            startup_center_channels=(0,)
        )
        servo_controller.center_servos_on_startup()
        print("[OK] Servo de direction initialisé")

        # Initialisation ultrason
        ultrasonic = distance_ultrasons.UltrasonicSensor(
            trigger_pin=23,
            echo_pin=24,
            max_distance=2
        )
        print("[OK] Capteur ultrason initialisé")

        # Initialisation suivi de ligne
        line_follower = task6_line_following.LineFollower(
            left_pin=22,
            middle_pin=27,
            right_pin=17,
            pull_up=False
        )
        print("[OK] Capteurs de suivi de ligne initialisés")

        # Initialisation lumière
        adc = task8_light_tracking.ADS7830()
        print("[OK] Capteurs de lumière initialisés")

        print()
        print("Tâche 7 démarrée.")
        print("Tape une commande puis Entrée.")
        print()

        while True:
            now = time.time()
            motor.update()
            distance_mm = read_ultrasonic_mm(ultrasonic)
            line_values = read_line_sensors(line_follower)
            light_values = read_light_sensors(adc)

            # Sécurité obstacle
            if distance_mm is not None and distance_mm < OBSTACLE_STOP_DISTANCE_MM:
                if robot_is_moving:
                    print()
                    print(f"[SÉCURITÉ] Obstacle à {distance_mm:.1f} mm -> arrêt moteur")
                    motor_stop(motor)
                    robot_is_moving = False

                obstacle_detected = True
                ws2812_status_color(ws_led, "obstacle")

            else:
                obstacle_detected = False

                if robot_is_moving:
                    ws2812_status_color(ws_led, "moving")
                else:
                    ws2812_status_color(ws_led, "ready")

            # LED d'état
            if obstacle_detected:
                if now - last_hazard_time >= HAZARD_BLINK_DELAY:
                    hazard_state = hazard_lights_step(hazard_state)
                    last_hazard_time = now
            else:
                hazard_state = False

                if robot_is_moving:
                    set_front_rgb((0, 0, 1), (0, 0, 1))
                else:
                    set_front_rgb((0, 1, 0), (0, 1, 0))

            # Affichage régulier
            if now - last_display_time >= DISPLAY_DELAY:
                distance_text = f"{distance_mm:.1f} mm" if distance_mm is not None else "N/A"

                if line_values is None:
                    line_text = "N/A"
                else:
                    line_text = f"G={line_values[0]} M={line_values[1]} D={line_values[2]}"

                if light_values is None:
                    light_text = "N/A"
                else:
                    light_text = f"G={light_values[0]} D={light_values[1]}"

                print(
                    f"[ÉTAT] distance={distance_text} | ligne={line_text} | lumière={light_text}",
                    end="\r"
                )

                last_display_time = now

            # Commandes clavier
            cmd = read_key_non_blocking()

            if cmd == "q":
                print("\n[COMMANDE] Quitter")
                break

            elif cmd == "m":
                if obstacle_detected:
                    print("\n[REFUS] Obstacle trop proche, avance interdite.")
                else:
                    motor_forward(motor)
                    robot_is_moving = True

            elif cmd == "b":
                motor_backward(motor)
                robot_is_moving = True

            elif cmd == "a":
                motor_stop(motor)
                robot_is_moving = False

            elif cmd == "g":
                servo_left(servo_controller)

            elif cmd == "d":
                servo_right(servo_controller)

            elif cmd == "c":
                servo_center(servo_controller)

            elif cmd == "s":
                print()
                print("----- ÉTAT CAPTEURS -----")
                print(f"Distance ultrason : {distance_mm}")
                print(f"Suivi de ligne    : {line_values}")
                print(f"Lumière           : {light_values}")
                print("-------------------------")

            elif cmd == "l":
                print("\n[TEST] LED avant rouge")
                set_front_rgb((1, 0, 0), (1, 0, 0))
                time.sleep(0.5)

                print("[TEST] LED avant verte")
                set_front_rgb((0, 1, 0), (0, 1, 0))
                time.sleep(0.5)

                print("[TEST] LED avant bleue")
                set_front_rgb((0, 0, 1), (0, 0, 1))
                time.sleep(0.5)

            elif cmd == "w":
                print("\n[TEST] WS2812 rouge, vert, bleu")
                ws_led.colorWipe(80, 0, 0)
                time.sleep(0.5)

                ws_led.colorWipe(0, 80, 0)
                time.sleep(0.5)

                ws_led.colorWipe(0, 0, 80)
                time.sleep(0.5)

                ws2812_status_color(ws_led, "ready")

            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur.")

    finally:
        print("\nNettoyage du robot...")

        try:
            if motor is not None:
                motor_stop(motor)
        except Exception:
            pass

        try:
            led_control.set_all_switch_off()
        except Exception:
            pass

        try:
            if ws_led is not None:
                ws_led.colorWipe(0, 0, 0)
        except Exception:
            pass

        try:
            if ultrasonic is not None:
                ultrasonic.close()
        except Exception:
            pass

        try:
            if line_follower is not None:
                line_follower.close()
        except Exception:
            pass

        try:
            if servo_controller is not None:
                servo_controller.close()
        except Exception:
            pass

        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
        except Exception:
            pass

        print("Fin de la tâche 7.")


if __name__ == "__main__":
    main()
