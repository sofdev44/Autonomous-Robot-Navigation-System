from gpiozero import DistanceSensor
from time import sleep


class UltrasonicSensor:
    def __init__(self, trigger_pin=23, echo_pin=24, max_distance=2) -> None:
        """
        Initialise le capteur ultrason.
        :param trigger_pin (int) : broche GPIO connectée à Trig
        :param echo_pin (int) : broche GPIO connectée à Echo
        :param max_distance (float) : distance maximale de détection en mètres
        """

        self.sensor = DistanceSensor(
            echo=echo_pin,
            trigger=trigger_pin,
            max_distance=max_distance
        )


    def get_distance_mm(self) -> float:
        """
        Retourne la distance mesurée en millimètres.
        :return (float): distance en millimètres
        """

        return self.sensor.distance * 1000


    def print_distance_loop(self, delay=0.05) -> None:
        """
        Affiche en continu la distance mesurée en millimètres.
        :param delay (float) : temps d'attente entre chaque mesure, en secondes
        """

        while True:
            distance = self.get_distance_mm()
            print(f"{distance:.2f} mm")
            sleep(delay)


    def close(self) -> None:
        """
        Libère proprement les ressources GPIO utilisées par le capteur.
        """

        self.sensor.close()


if __name__ == "__main__":
    # Création d'un objet capteur ultrason
    ultrasonic = UltrasonicSensor(trigger_pin=23, echo_pin=24, max_distance=2)

    try:
        # Lance l'affichage continu de la distance
        ultrasonic.print_distance_loop()

    except KeyboardInterrupt:
        # Permet d'arrêter le programme proprement avec Ctrl + C
        print("\nArrêt du programme par l'utilisateur.")

    finally:
        # Libère les ressources GPIO avant de quitter
        ultrasonic.close()
