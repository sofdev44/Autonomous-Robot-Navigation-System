import time
from rpi_ws281x import *

class LED:
    def __init__(self):
        
        self.LED_COUNT = 14 # Nombre total de LEDs sur le robot (peut être supérieur au nombre de LEDs connectées directement au Raspberry Pi)
        self.LED_PIN = 10 # Broche GPIO utilisée pour le signal
        self.LED_FREQ_HZ = 800000 # Fréquence du signal des LEDs en Hertz (généralement 800 kHz)
        self.LED_DMA = 10 # Canal DMA à utiliser pour générer le signal en arrière-plan
        self.LED_BRIGHTNESS = 255 # Luminosité globale : 0 pour éteint, 255 pour la luminosité maximale
        self.LED_INVERT = False # True pour inverser le signal (utile avec certains circuits de décalage de niveau)
        self.LED_CHANNEL = 0
        
        # Création de l'objet NeoPixel avec la configuration définie ci-dessus
        self.strip = Adafruit_NeoPixel(self.LED_COUNT, self.LED_PIN, self.LED_FREQ_HZ,
        self.LED_DMA, self.LED_INVERT, self.LED_BRIGHTNESS, self.LED_CHANNEL)
        
        # Initialisation de la bibliothèque (doit être appelée une seule fois avant les autres fonctions)
        self.strip.begin()

    # Choisir une couleur pour toutes les LEDs (effet de balayage/remplissage)
    def colorWipe(self, R, G, B) -> None:
        """
        Cette fonction permet de changer la couleur de l'ensemble du bandeau LED.
        :param R (int): Intensité de la composante rouge (0-255)
        :param G (int): Intensité de la composante verte (0-255)
        :param B (int): Intensité de la composante bleue (0-255)
        :return (None):
        """

        color = Color(R, G, B)
        for i in range(self.strip.numPixels()):
            # On ne peut configurer qu'une seule LED à la fois, une boucle est donc nécessaire
            self.strip.setPixelColor(i, color)
            self.strip.show() # Le changement de couleur ne devient réel qu'après l'appel de la méthode show()
            # Ce code va contrôler toutes les lumières WS2812. Appuyez sur CTRL+C pour quitter le programme.


    # Choisir l'intensité globale des LEDs
    def setBrightness(self, brightness) -> None:
        """
        Cette fonction permet de changer l'intensité globale des LEDs.
        :param brightness (int): Intensité de la luminosité (0-255)
        :return (None):
        """

        # La luminosité doit obligatoirement être comprise entre 0 et 255
        if brightness < 0:
            brightness = 0
        if brightness > 255:
            brightness = 255
        
        self.strip.setBrightness(brightness)
        self.strip.show()


    # Choisir la couleur d'une seule LED
    def setLedColor(self, led_number, R, G, B) -> None:
        """
        Cette fonction permet de changer la couleur d'une seule LED du bandeau.
        :param led_number (int): Numéro de la LED à configurer (0 pour
        la première LED, 1 pour la deuxième, etc.)
        :param R (int): Intensité de la composante rouge (0-255)
        :param G (int): Intensité de la composante verte (0-255)
        :param B (int): Intensité de la composante bleue (0-255
        :return (None):
        """
        
        # Vérifie que le numéro de la LED demandé est valide
        if led_number < 0 or led_number >= self.strip.numPixels():
            print("Erreur : numéro de LED invalide")
            return
        
        # Crée l'objet couleur RGB
        color = Color(R, G, B)

        # Modifie la couleur de la LED sélectionnée en mémoire
        self.strip.setPixelColor(led_number, color)

        # Envoie et applique le changement physiquement aux LEDs
        self.strip.show()


    # Choisir la couleur et l'intensité d'une seule LED
    def setPixelColorRGB(self, led_number, R, G, B, brightness) -> None:
        """
        Cette fonction permet de changer la couleur et l'intensité d'une seule LED du bandeau.
        :param led_number (int): Numéro de la LED à configurer (0 pour la première LED, 1 pour la deuxième, etc.)
        :param R (int): Intensité de la composante rouge (0-255)
        :param G (int): Intensité de la composante verte (0-255)
        :param B (int): Intensité de la composante bleue (0-255)
        :param brightness (int): Intensité de la luminosité (0-255)
        :return (None):
        """

        # Vérifie que le numéro de la LED demandé est valide
        if led_number < 0 or led_number >= self.strip.numPixels():
            print("Erreur : numéro de LED invalide")
            return
        
        # Vérifie que la luminosité est bien comprise entre 0 et 255
        if brightness < 0:
            brightness = 0
        if brightness > 255:
            brightness = 255
        
        # Applique le ratio de luminosité à chaque composante de couleur
        red = int(R * brightness / 255)
        green = int(G * brightness / 255)
        blue = int(B * brightness / 255)

        color = Color(red, green, blue)        

        # Applique la couleur calculée à la LED ciblée
        self.strip.setPixelColor(led_number, color)

        # Envoie et applique le changement physiquement aux LEDs
        self.strip.show()

if __name__ == '__main__':
    led = LED()

    try:
        # Exemple : Allume la LED numéro 5 en bleu avec une intensité réduite (60)
        led.setPixelColorRGB(5, 0, 0, 255, 60)

        # Boucle infinie pour maintenir le script actif et les LEDs allumées
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        # Permet de quitter proprement le script avec un CTRL+C en éteignant toutes les LEDs
        led.colorWipe(0, 0, 0) # Éteint toutes les lumières
