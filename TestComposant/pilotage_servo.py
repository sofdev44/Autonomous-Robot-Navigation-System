#!/usr/bin/env python3

import time
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685


class ServoController:
    def __init__(
        self,
        i2c_address=0x5f,
        frequency=50,
        min_pulse=500,
        max_pulse=2400,
        actuation_range=180,
        offsets=None,
        rotation_delay=0.001,
        startup_center_channels=(0,)
    ):
        """
        Initialise le contrôleur PCA9685 et prépare la gestion des servos.

        i2c_address : adresse I2C du module PCA9685
        frequency : fréquence PWM utilisée par les servos
        min_pulse / max_pulse : limites du signal PWM du servo
        actuation_range : plage d'angle du servo, généralement 180°
        offsets : dictionnaire contenant les offsets par canal
        rotation_delay : temps d'attente entre chaque degré du mouvement
                         Plus la valeur est grande, plus le servo tourne lentement.
        startup_center_channels : canaux à mettre automatiquement à 90°
                                  au démarrage du programme.
        """

        # Création du bus I2C avec les broches SCL et SDA du Raspberry Pi
        self.i2c = busio.I2C(SCL, SDA)

        # Initialisation du module PCA9685
        self.pca = PCA9685(self.i2c, address=i2c_address)
        self.pca.frequency = frequency

        # Dictionnaire pour stocker les servos déjà créés
        self.servos = {}

        # Dictionnaire pour mémoriser le dernier angle envoyé à chaque servo
        # Cela permet de ralentir le mouvement entre deux angles connus.
        self.current_angles = [90,90,90]
        self.target_angles = [None,None,None]

        # Paramètres des servos
        self.min_pulse = min_pulse
        self.max_pulse = max_pulse
        self.actuation_range = actuation_range

        # Vitesse de rotation
        # Le pas reste normal : 1 degré à la fois.
        # Seul le délai entre chaque degré change.
        self.rotation_delay = rotation_delay

        # Canaux à centrer automatiquement au démarrage.
        # Par défaut, on centre seulement le canal 0, qui gère la direction.
        # Si tu veux centrer les canaux 0, 1 et 2, remplace par (0, 1, 2).
        self.startup_center_channels = startup_center_channels

        # Offsets des servos
        # Par défaut, le canal 0 a un offset de 8°
        self.offsets = offsets if offsets is not None else {
            0: 8,  # Offset pour le servo canal 0 qui gère la direction
        }

        self.last_servo_time = [time.time(), time.time(),time.time()]
        

    def get_servo(self, channel):
        """
        Retourne le servo correspondant au canal demandé.

        Si le servo n'existe pas encore dans le dictionnaire,
        il est créé puis sauvegardé.
        """

        if channel not in self.servos:
            self.servos[channel] = servo.Servo(
                self.pca.channels[channel],
                min_pulse=self.min_pulse,
                max_pulse=self.max_pulse,
                actuation_range=self.actuation_range
            )

        return self.servos[channel]

    def apply_offset(self, channel, angle):
        """
        Applique l'offset du canal et limite l'angle entre 0° et 180°.
        """

        # Récupération de l'offset du canal
        # Si aucun offset n'est défini, on utilise 0
        offset = self.offsets.get(channel, 0)

        # Application de l'offset
        corrected_angle = angle + offset

        # Sécurité : on bloque l'angle entre 0° et 180°
        corrected_angle = max(0, min(180, corrected_angle))

        return corrected_angle

    
    def move_servo_with_speed(self, channel, corrected_angle):
        """Déplace le servo de façon asynchrone basé sur le temps écoulé."""
        selected_servo = self.get_servo(channel)

        # Premier mouvement : initialisation immédiate
        if channel not in self.current_angles:
            selected_servo.angle = corrected_angle
            self.current_angles[channel] = corrected_angle
            self.last_servo_time[channel] = time.time()
            print("init angle")
            return

        start_angle = self.current_angles[channel]
        target_angle = corrected_angle
        self.target_angles[channel] = corrected_angle
        if start_angle == target_angle:
            return

        # Mouvement instantané si aucun délai n'est configuré
        if self.rotation_delay <= 0:
            selected_servo.angle = target_angle
            self.current_angles[channel] = target_angle
            return

        now = time.time()
        last_time = self.last_servo_time[channel]
        delta_time = now - last_time
        
        if delta_time >= self.rotation_delay:
            # Calcul du déplacement proportionnel (ex: si rotation_delay = 0.1s pour 1°, alors 1s = 10°)
            pas_par_seconde = 1.0 / self.rotation_delay
            deplacement = delta_time * pas_par_seconde
            
            direction = 1 if target_angle > start_angle else -1
            next_angle = start_angle + (direction * deplacement)
            
            # Sécurité : Évite de dépasser la cible (overshoot)
            if (direction == 1 and next_angle >= target_angle) or (direction == -1 and next_angle <= target_angle):
                next_angle = target_angle

            selected_servo.angle = next_angle
            self.current_angles[channel] = next_angle
            self.last_servo_time[channel] = now
    
    def update(self):
        for i in range(0,3):
            if self.target_angles[i] != None:
                self.move_servo_with_speed(self, i,self.target_angles[i])

    def set_angle(self, channel, angle):
        """
        Définit l'angle d'un servo en appliquant l'offset du canal,
        puis en contrôlant la vitesse de rotation.

        channel : canal du PCA9685
        angle : angle demandé par l'utilisateur
        """

        # Calcul de l'angle corrigé avec l'offset
        corrected_angle = self.apply_offset(channel, angle)

        # Déplacement vers l'angle corrigé avec vitesse contrôlée
        self.move_servo_with_speed(channel, corrected_angle)
        """
        print(
            f"Servo sur le canal {channel} demandé à {angle}° "
            f"-> envoyé à {corrected_angle}°"
        )
        """
    def print_angle(self, channel):
        print(f"Servo sur le canal {channel} à pour angle {self.current_angles[channel]}")
        return

    def center_servos_on_startup(self):
        """
        Place automatiquement les servos choisis à 90° au démarrage
        """

        if not self.startup_center_channels:
            return

        print("Mise au centre des servos au démarrage...")

        for channel in self.startup_center_channels:
            corrected_angle = self.apply_offset(channel, 90)
            selected_servo = self.get_servo(channel)
            selected_servo.angle = corrected_angle

            # On mémorise l'angle corrigé pour que les prochains mouvements
            # puissent être ralentis dès la première commande utilisateur.
            self.current_angles[channel] = corrected_angle

            print(
                f"Servo sur le canal {channel} placé à 90° "
                f"-> envoyé à {corrected_angle}°"
            )

        time.sleep(0.5)
        print()

    def ask_int(self, message, minimum, maximum):
        """
        Demande une valeur entière à l'utilisateur.

        Retourne None si l'utilisateur tape q, quit ou exit.
        """

        while True:
            value = input(message).strip()

            # Permet de quitter le programme
            if value.lower() in ["q", "quit", "exit"]:
                return None

            try:
                value = int(value)
            except ValueError:
                print("Entrer une valeur valide.")
                continue

            # Vérifie que la valeur est dans la plage autorisée
            if value < minimum or value > maximum:
                print(f"Entrer une valeur entre {minimum} et {maximum}.")
                continue

            return value

    def ask_float(self, message, minimum, maximum, default=None):
        """
        Demande une valeur décimale à l'utilisateur.

        Si l'utilisateur appuie juste sur Entrée, la valeur par défaut est utilisée.
        Retourne None si l'utilisateur tape q, quit ou exit.
        """

        while True:
            value = input(message).strip()

            # Permet de quitter le programme
            if value.lower() in ["q", "quit", "exit"]:
                return None

            # Permet d'utiliser la valeur par défaut
            if value == "" and default is not None:
                return default

            try:
                value = float(value)
            except ValueError:
                print("Entrer une valeur valide.")
                continue

            # Vérifie que la valeur est dans la plage autorisée
            if value < minimum or value > maximum:
                print(f"Entrer une valeur entre {minimum} et {maximum}.")
                continue

            return value

    def configure_speed(self, delay=None):
        """
        Permet à l'utilisateur de choisir uniquement la vitesse du mouvement.

        Le pas reste toujours de 1°.

        Exemples :
        - 0.01 : assez rapide
        - 0.03 : plus lent
        - 0.05 : très lent
        - 0 : instantané
        """
        if delay is not None:
            if delay >= 0 and delay <= 1:
                self.rotation_delay = delay
                return
        print("Réglage de la vitesse du mouvement")
        print("Le pas reste normal : 1° à la fois.")
        print("Appuie sur Entrée pour garder la valeur par défaut.")
        print()

        delay = self.ask_float(
            f"Délai entre chaque degré en secondes "
            f"(défaut {self.rotation_delay}, 0 = instantané): ",
            0,
            1,
            self.rotation_delay
        )

        if delay is None:
            return False

        self.rotation_delay = delay

        print(f"Vitesse réglée : 1° toutes les {self.rotation_delay} secondes.")
        print()

        return True

    def run(self):
        """
        Lance le mode interactif pour piloter les servos.
        """

        print("Pilotage de Servo")
        print("Taper q pour quitter.")
        print()

        # Au démarrage, on place le ou les servos choisis à 90°.
        # Cela donne une position connue au programme avant les commandes utilisateur.
        self.center_servos_on_startup()

        # Demande la vitesse une seule fois au lancement du programme
        if not self.configure_speed():
            return

        while True:
            # Demande du canal servo
            channel = self.ask_int("Canal du Servo 0-2: ", 0, 2)

            if channel is None:
                break

            # Le servo de direction sur le canal 0 est limité entre 45° et 135°
            if channel == 0:
                angle = self.ask_int("Angle 45-135: ", 45, 135)
            else:
                angle = self.ask_int("Angle 0-180: ", 0, 180)

            if angle is None:
                break

            # Envoi de l'angle au servo
            self.set_angle(channel, angle)

            time.sleep(0.2)
            print()

    def close(self):
        """
        Libère proprement le module PCA9685.
        """

        self.pca.deinit()
        print("PCA9685 libéré.")


if __name__ == "__main__":
    # Tu peux aussi régler la vitesse ici directement.
    # Exemple plus lent :
    # controller = ServoController(rotation_delay=0.05)
    #
    # Par défaut, le canal 0 est placé à 90° au démarrage.
    # Pour centrer les canaux 0, 1 et 2 au démarrage :
    # controller = ServoController(startup_center_channels=(0, 1, 2))
    controller = ServoController()

    try:
        controller.run()

    except KeyboardInterrupt:
        print("\nArrêté par l'utilisateur.")

    finally:
        controller.close()
