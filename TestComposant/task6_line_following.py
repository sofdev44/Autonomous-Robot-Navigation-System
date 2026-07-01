#!/usr/bin/env python3
"""
task6_line_following.py

Tâche 6 : Capteurs de suivi de ligne

Version avec classe LineFollower.

Correction importante :
- pull_up n'est plus à None par défaut.
- On utilise pull_up=False pour éviter l'erreur :
  PinInvalidState: Pin GPIO22 is defined as floating, but active_state is not defined
"""

import time
from gpiozero import InputDevice


class LineFollower:
    def __init__(
        self,
        left_pin=22,
        middle_pin=27,
        right_pin=17,
        pull_up=False
    ):
        """
        Initialise les trois capteurs de suivi de ligne.

        left_pin   : GPIO du capteur gauche
        middle_pin : GPIO du capteur milieu
        right_pin  : GPIO du capteur droit
        pull_up    : résistance pull-up interne.
                     False évite que la broche soit considérée comme flottante.
        """

        self.left_pin = left_pin
        self.middle_pin = middle_pin
        self.right_pin = right_pin
        self.pull_up = pull_up

        self.left_sensor = InputDevice(pin=self.left_pin, pull_up=self.pull_up)
        self.middle_sensor = InputDevice(pin=self.middle_pin, pull_up=self.pull_up)
        self.right_sensor = InputDevice(pin=self.right_pin, pull_up=self.pull_up)

    def read(self):
        """
        Lit les trois capteurs.

        Retourne :
        (gauche, milieu, droite)

        Selon le module :
        - 0 peut signifier ligne noire détectée
        - 1 peut signifier pas de ligne
        """

        return (
            self.left_sensor.value,
            self.middle_sensor.value,
            self.right_sensor.value
        )

    def read_left(self):
        """
        Lit uniquement le capteur gauche.
        """

        return self.left_sensor.value

    def read_middle(self):
        """
        Lit uniquement le capteur du milieu.
        """

        return self.middle_sensor.value

    def read_right(self):
        """
        Lit uniquement le capteur droit.
        """

        return self.right_sensor.value

    def print_values(self):
        """
        Affiche une seule lecture des trois capteurs.
        """

        left_value, middle_value, right_value = self.read()

        print(
            "left: %d    middle: %d    right: %d"
            % (left_value, middle_value, right_value)
        )

    def run(self, delay=0.3):
        """
        Lance un test manuel en boucle.
        """

        print("Test des capteurs de suivi de ligne")
        print("Appuie sur Ctrl+C pour arrêter.")
        print()

        try:
            while True:
                self.print_values()
                time.sleep(delay)

        except KeyboardInterrupt:
            print("\nArrêt du suivi de ligne.")

    def close(self):
        """
        Libère proprement les ressources gpiozero.
        """

        self.left_sensor.close()
        self.middle_sensor.close()
        self.right_sensor.close()


def setup_sensors():
    """
    Fonction de compatibilité.

    Si un ancien programme appelle encore setup_sensors(),
    cette fonction retourne directement un objet LineFollower.
    """

    return LineFollower()


def read_sensors(line_follower):
    """
    Fonction de compatibilité.

    Lit les capteurs depuis un objet LineFollower.
    """

    return line_follower.read()


def main():
    """
    Test manuel du module.
    """

    line_follower = LineFollower()

    try:
        line_follower.run(delay=0.3)

    finally:
        line_follower.close()


if __name__ == "__main__":
    main()
