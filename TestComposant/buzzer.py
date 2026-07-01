#!/usr/bin/env python3

from gpiozero import TonalBuzzer
from gpiozero.tones import Tone
import mido


class MidiBuzzer:
    def __init__(self, pin=18, octaves=4, min_frequency=220, max_frequency=880) -> None:
        """
        Classe permettant de jouer des notes MIDI avec un buzzer branché sur un GPIO.
        :param pin (int): Numéro du pin GPIO sur lequel le buzzer est branché.
        :param octaves (int): Nombre d'octaves gérées par TonalBuzzer.
        :param min_frequency (float): Fréquence minimale autorisée, en Hz.
        :param max_frequency (float): Fréquence maximale autorisée, en Hz.
        """

        # On sauvegarde les paramètres dans l'objet pour pouvoir les réutiliser ailleurs.
        self.pin = pin
        self.octaves = octaves
        self.min_frequency = min_frequency
        self.max_frequency = max_frequency

        # Création du buzzer tonal sur le pin GPIO choisi.
        self.buzzer = TonalBuzzer(pin, octaves=octaves)


    def note_to_frequency(self, note) -> float:
        """
        Convertit une note MIDI en fréquence réelle, limitée entre min_frequency et max_frequency.
        :param note (int): Numéro de la note MIDI à convertir.
        :return (float): Fréquence correspondante à la note MIDI, limitée entre min_frequency et max_frequency.
        """

        frequency = 440 * (2 ** (((note - 69) / 12) - 0.5))

        # On limite la fréquence pour éviter de demander au buzzer des sons trop graves ou trop aigus.
        return max(self.min_frequency, min(self.max_frequency, frequency))

    
    def play_note(self, note) -> None:
        """
        Joue une note MIDI avec le buzzer.
        :param note (int): Numéro de la note MIDI à jouer.
        """

        # Conversion de la note MIDI en fréquence réelle.
        frequency = self.note_to_frequency(note)

        # Lecture de la fréquence avec le buzzer.
        self.buzzer.play(Tone(frequency=frequency))


    def stop(self) -> None:
        """
        Arrête le son du buzzer.
        """
        self.buzzer.stop()


    def play_midi(self, midi_file_path) -> None :
        """
        Lit un fichier MIDI et joue ses notes avec le buzzer.
        :param midi_file_path (str): Chemin vers le fichier MIDI à lire.
        """

        # Chargement du fichier MIDI avec la librairie mido.
        mid = mido.MidiFile(midi_file_path)
        print(f"Lecture du fichier bridée entre {self.min_frequency}Hz et {self.max_frequency}Hz...")

        # mid.play() lit les messages MIDI en respectant les temps du fichier.
        for msg in mid.play():
            # Une note_on avec une vélocité supérieure à 0 signifie qu'une note commence.
            if msg.type == "note_on" and msg.velocity > 0:
                self.play_note(msg.note)

            # Une note_off, ou une note_on avec vélocité 0, signifie que la note s'arrête.
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                self.stop()


    def close(self) -> None:
        """
        Libère proprement les ressources GPIO utilisées par le buzzer.
        """

        # On arrête d'abord le buzzer pour éviter qu'un son reste bloqué.
        self.stop()

        # Puis on ferme l'objet gpiozero.
        self.buzzer.close()


    def __enter__(self) -> "MidiBuzzer":
        """
        Permet d'utiliser la classe avec un bloc 'with'.
        Exemple:
            with MidiBuzzer() as buzzer:
                buzzer.play_midi("7.mid")
        :return (MidiBuzzer): L'instance de MidiBuzzer elle-même pour pouvoir l'utiliser dans le bloc 'with'.
        """

        return self


    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Ferme automatiquement le buzzer à la fin d'un bloc 'with'.
        """

        self.close()


if __name__ == "__main__":
    # Création du buzzer sur le GPIO 18.
    buzzer = MidiBuzzer(pin=18, octaves=4)

    try:
        # Lecture du fichier MIDI nommé 7.mid.
        buzzer.play_midi("7.mid")

    except KeyboardInterrupt:
        # Si l'utilisateur fait Ctrl+C, on arrête le buzzer proprement.
        buzzer.stop()

    finally:
        # Dans tous les cas, on libère les ressources GPIO à la fin du programme.
        buzzer.close()
