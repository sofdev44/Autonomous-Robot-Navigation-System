import time
import smbus
from pilotage_servo import ServoController
from motor2 import Motor, Dir_forward
from distance_ultrasons import UltrasonicSensor
import led_control

class ADS7830(object):
	def __init__(self):
		self.cmd = 0x84
		self.bus = smbus.SMBus(1)
		self.address = 0x48
		
	def analogRead(self, chn): 
		value = self.bus.read_byte_data(self.address, self.cmd | (((chn<<2 | chn>>1)&0x07)<<4))
		return value
	
	def analogtoangle(self, chn=1, value=None):
		if value is None:
			value = self.analogRead(chn)
			
		angle = ((255.0 - float(value)) / 255.0) * 180.0
		angle2 = int(max(40.0, min(140.0, angle)))
		return angle2 

def obstacle_detected():
	try:
		distance = ultrasonic_sensor.get_distance_mm()
		print(f"Distance : {distance:.1f} mm")
		return distance < OBSTACLE_LIMIT_MM
	except Exception as e:
		print("Erreur capteur ultrason :", e)
		return False
	
if __name__ == "__main__":
	OBSTACLE_LIMIT_MM  = 200
	MOTOR_SPEED        = 20
	ACCEL_PENTE        = 1.0
	DECEL_PENTE        = 2.0
	MOTOR_CHANNEL      = 1
	HAZARD_BLINK_DELAY = 0.4

	# --- Initialisation ---
	adc              = ADS7830()
	controller       = ServoController()
	motor_controller = Motor()

	ultrasonic_sensor = UltrasonicSensor(
		trigger_pin=23,
		echo_pin=24,
		max_distance=2
	)

	led_control.switchSetup()

	robot_running     = False
	hazard_active     = False
	hazard_state      = False
	last_hazard_blink = 0

	motor_controller.setSpeed(Dir_forward, MOTOR_SPEED,
							   pente=ACCEL_PENTE, channel=MOTOR_CHANNEL)
	robot_running = True

	try:
		while True:

			# --- 1. Light tracking ---
			adc_angle = adc.analogtoangle(chn=1)
			controller.set_angle(0, adc_angle)

			# --- 2. Gestion obstacle ---
			if obstacle_detected():
				if robot_running:
					print("Obstacle détecté ! Arrêt.")
					motor_controller.setSpeed(Dir_forward, 0,
											   pente=DECEL_PENTE,
											   channel=MOTOR_CHANNEL)
					robot_running     = False
					hazard_active     = True
					hazard_state      = False
					last_hazard_blink = 0
			else:
				if not robot_running:
					print("Voie libre — reprise.")
					motor_controller.setSpeed(Dir_forward, MOTOR_SPEED,
											   pente=ACCEL_PENTE,
											   channel=MOTOR_CHANNEL)
					robot_running = True
					hazard_active = False
					led_control.set_all_switch_off()

			# --- 3. Clignotement feux (non-bloquant) ---
			if hazard_active:
				now = time.time()
				if now - last_hazard_blink >= HAZARD_BLINK_DELAY:
					last_hazard_blink = now
					hazard_state = not hazard_state
					if hazard_state:
						led_control.switch_hat_led(11, 1)
						led_control.switch_hat_led(12, 1)
						led_control.switch_hat_led(13, 1)
					else:
						led_control.set_all_switch_off()

			# --- 4. Mise à jour moteur ---
			motor_controller.update()
			time.sleep(0.02)

	except KeyboardInterrupt:
		print("\nInterruption clavier détectée.")

	finally:
		motor_controller.motorStop(MOTOR_CHANNEL)
		led_control.set_all_switch_off()
		ultrasonic_sensor.close()
		print("Nettoyage terminé.")
