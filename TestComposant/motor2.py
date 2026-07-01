#!/usr/bin/env python3
from pyclbr import Class
import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import motor
import numpy as np
import curses

# motor_EN_A: Pin7 | motor_EN_B: Pin11
# motor_A: Pin8,Pin10 | motor_B: Pin13,Pin12
MOTOR_M1_IN1 = 15 #Define the positive pole of M1
MOTOR_M1_IN2 = 14 #Define the negative pole of M1

Dir_forward = 1
Dir_backward = -1

left_forward = 1
left_backward = 0

right_forward = 0
right_backward= 1

pwn_A = 0
pwm_B = 0

def map(x,in_min,in_max,out_min,out_max):
	return (x - in_min)/(in_max - in_min) *(out_max - out_min) + out_min

class Motor:
	def __init__(self) -> None:
			# Initialisation matérielle
			self.i2c = busio.I2C(SCL, SDA)
			self.pwm_motor = PCA9685(self.i2c, address=0x5f)
			self.pwm_motor.frequency = 50
			
			self.motor1 = motor.DCMotor(self.pwm_motor.channels[MOTOR_M1_IN1], self.pwm_motor.channels[MOTOR_M1_IN2])
			self.motor1.decay_mode = motor.SLOW_DECAY 
			self.motors = [self.motor1]
			self.current_speed = [0]
			self.current_direction = [1]
			self.target_speed = [0]
			self.target_direction = [1] 
			self.pentes = [1]
			self.nb_motors = len(self.motors)
			self.time = time.time()


	def setSpeed(self, new_direction, new_speed, pente=1, channel=1) -> None:
		"""
		Définit la vitesse et la direction d'un moteur
		:param new_direction (int): 1 pour avancer, -1 pour reculer
		:param new_speed (int): Vitesse cible entre 0 et 100
		:param pente (float): (default=1) Plus la pente est faible, plus la transition est lente EX: 0.5 pour une transition en 2 secondes, 1 pour une transition en 1 seconde
		:param channel (int): Numéro du moteur (default=1) entre 1 et le nombre de moteurs disponibles
		"""

		# Sécurisation des limites de vitesse entre 0 et 100
		new_speed = max(0, min(new_speed, 100))
		self.target_speed[channel-1] = new_speed
		self.target_direction[channel-1] = new_direction
		self.pentes[channel-1] = pente
		
		


	def transition(self, channel) -> None:
		"""
		Effectue une transition progressive de la vitesse actuelle à la vitesse cible en fonction de la pente spécifiée.
		:param channel (int): Numéro du moteur entre 1 et le nombre de moteurs disponibles
		"""

		# Vérification de la validité du canal
		if self.checkMotor(channel-1):
			return
		
		v_current = self.current_speed[channel-1] * self.current_direction[channel-1]
		v_target = self.target_speed[channel-1] * self.target_direction[channel-1]
		
		# Calcul de la durée:
		diff_vitesse = abs(v_target - v_current)
		duree_pas = (1.0 / (self.pentes[channel-1] *100)) # la duree est en secondes 
		delta_time = time.time() - self.time
		
		if (diff_vitesse == 0) or (delta_time < duree_pas):
			return
		else:
			v_actuelle = v_current + min((delta_time / duree_pas), diff_vitesse) * (1 if v_target > v_current else -1)
			throttle = map(v_actuelle, -100, 100, -1.0, 1.0)
			self.motors[channel-1].throttle = max(-1.0, min(throttle, 1.0))		
			
			# Mise à jour de la vitesse et de la direction actuelles
			self.current_speed[channel-1] = abs(v_actuelle)
			self.current_direction[channel-1] = self.target_direction[channel-1]
			self.time = time.time()

	def update(self) -> None:
		"""
		Mets à jour la vitesse de tous les moteurs en fonction de leurs vitesses cibles et des pentes spécifiées.
		Doit être appelé régulièrement dans la boucle principale pour assurer des transitions fluides.
		"""
		for i in range(self.nb_motors):
			self.transition(i+1)

	# Arrêt progressif du moteur
	def motorStop(self, channel=None, pente=1) -> None:
		"""
		Arrête progressivement le moteur en réduisant la vitesse à zéro selon la pente spécifiée.
		:param channel (int): Numéro du moteur à arrêter (default=None pour tous les moteurs)
		:param pente (float): Plus la pente est faible, plus l'arrêt est lent (default=1) EX: 0.5 pour un arrêt en 2 secondes, 1 pour un arrêt en 1 seconde
		"""

		if channel is None:
			for i in range(len(self.motors)):
				self.setSpeed(1, 0, pente, channel=i+1)
				while any(speed > 0 for speed in self.current_speed):
					self.update()
					time.sleep(0.001) # Petite pause pour soulager le processeur

		else:
			self.setSpeed(1, 0, pente, channel=channel)
			while self.current_speed[channel-1] > 0:
				self.update()
				time.sleep(0.001) # Petite pause pour soulager le processeur

	# Récupération de la vitesse actuelle
	def getSpeed(self, channel = None) -> int:
		"""
		Récupère la vitesse actuelle du moteur spécifié ou de tous les moteurs si aucun canal n'est précisé.
		:param channel (int): Numéro du moteur à interroger (default=None pour tous les moteurs)
		:return (int or list of int): Vitesse actuelle du moteur ou liste de vitesses pour tous les moteurs
		"""

		if channel is None:
			return self.current_speed
		else:
			# Vérification de la validité du canal
			if self.checkMotor(channel-1):
				return
			return self.current_speed[channel-1]
	

	# Récupération de la direction actuelle
	def getDirection(self, channel = None) -> int:
		"""
		Récupère la direction actuelle du moteur spécifié ou de tous les moteurs si aucun canal n'est précisé.
		:param channel (int): Numéro du moteur à interroger (default=None pour tous les moteurs)
		:return (int or list of int): Direction actuelle du moteur ou liste de directions pour tous les moteurs
		"""

		if channel is None:
			return self.current_direction
		else:
			# Vérification de la validité du canal
			if self.checkMotor(channel-1):
				return
			return self.current_direction[channel-1]
	

	# Mise à jour de la vitesse et de la direction pour tous les moteurs
	def setAllSpeeds(self, new_direction, new_speed, pente=1) -> None:
		"""
		Mets à jour la vitesse et la direction de tous les moteurs simultanément.
		:param new_direction (int): 1 pour avancer, -1 pour reculer
		:param new_speed (int): Vitesse cible entre 0 et 100
		:param pente (float): (default=1) Plus la pente est faible, plus la transition est lente EX: 0.5 pour une transition en 2 secondes, 1 pour une transition en 1 seconde
		"""
		for i in range(len(self.motors)):
			self.setSpeed(new_direction, new_speed, pente, channel=i+1)
	

	# Arrêt brutal de tous les moteurs
	def destroy(self) -> None:
		"""
		Arrête immédiatement tous les moteurs et libère les ressources matérielles.
		"""
		self.motorStop(pente=10)
		self.pwm_motor.deinit()
		self.i2c.deinit()
	
	def checkMotor(self, channel) -> bool:
		"""
		Vérifie si le numéro de moteur spécifié est valide.
		:param channel (int): Numéro du moteur à vérifier
		:return (bool): True si le numéro de moteur est invalide, False sinon
		"""
		return not (0 <= channel < self.nb_motors)
	
	def __del__(self) -> None:
		"""
		Nettoie les ressources lors de la destruction de l'objet Motor.
		"""
		self.destroy()
	
	


if __name__ == '__main__':
	mot = None
	try:
		print("Initialisation du moteur...")
		mot = Motor()
		
		# Initialisation de la fenêtre de capture clavier
		stdscr = curses.initscr()
		curses.noecho()
		curses.cbreak()
		stdscr.keypad(True)
		stdscr.nodelay(True) # Empêche getch() de bloquer le code

		print("\n=== Contrôle du Moteur ===")
		print("Flèche Haut   : Configurer Marche Avant (direction = 1)")
		print("Flèche Bas    : Configurer Marche Arrière (direction = -1)")
		print("Espace        : Accélérer (+10% de vitesse cible)")
		print("Touche 's'    : Arrêt progressif (Stop)")
		print("Touche 'q'    : Quitter")
		print("==========================\n")

		vitesse_cible = 0
		direction_cible = 1

		while True:
			# Appel impératif et constant de la mise à jour des moteurs
			mot.update()
			
			# Capture de la touche pressée
			key = stdscr.getch()

			if key == ord('q'):
				break
				
			elif key == curses.KEY_UP:
				direction_cible = 1
				mot.setSpeed(direction_cible, vitesse_cible, pente=1.0, channel=1)
				print(f"Direction configurée : AVANT | Vitesse actuelle cible : {vitesse_cible}%")
				
			elif key == curses.KEY_DOWN:
				direction_cible = -1
				mot.setSpeed(direction_cible, vitesse_cible, pente=1.0, channel=1)
				print(f"Direction configurée : ARRIÈRE | Vitesse actuelle cible : {vitesse_cible}%")
				
			elif key == ord(' '):
				vitesse_cible = min(vitesse_cible + 10, 100)
				mot.setSpeed(direction_cible, vitesse_cible, pente=1.0, channel=1)
				print(f"Accélération -> Vitesse cible : {vitesse_cible}% (Direction: {direction_cible})")
				
			elif key == ord('s'):
				vitesse_cible = 0
				mot.motorStop(channel=1, pente=1.0)
				print("Arrêt progressif demandé.")

			# Petite pause pour soulager le processeur (10ms)
			time.sleep(0.01)

	except KeyboardInterrupt:
		print("\nInterruption clavier détectée.")
	finally:
		# Restauration obligatoire du terminal standard
		curses.nocbreak()
		stdscr.keypad(False)
		curses.echo()
		curses.endwin()
		
		if mot:
			print("Extinction du système et libération du bus I2C.")
			mot.destroy()

