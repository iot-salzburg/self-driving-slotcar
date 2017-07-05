import slotcar_control as scc
#import esp_connection as espconn

class simpleAI():
	
	def __init__(self, carID=2):
		self.max_acceleration = 9.8 * 0.15 #m/s^2 Calculates by estimating force of friction with a slope and raeding off accelerometer data
		self.slotcar_client = scc.slotcarClient()
		#self.esp_client = espconn.espClient()
		#self.esp_client_loop
		self.error_margin = 1 #m/s^2
		self.carID = carID
		self.game_started = False
		self.last_power = 5
		self.min_power = 5
		self.max_power = 30 #as shown in protocol
		
		
	#expecting last_cross_acceleration in m/s^2
	def main(self, last_cross_acceleration):
		#print(last_cross_acceleration)
		if abs(last_cross_acceleration) > self.max_acceleration:
			#call function which reduces acceleration
			self.change_power(increase = False)
			return
		elif abs(last_cross_acceleration) > self.max_acceleration - self.error_margin:
			#retain current speed
			return
		else:
			#increase current speed
			self.change_power(increase = True)
			return
	
	def change_power(self, increase):
		if increase:
			if self.last_power + 1 <= self.max_power:
				self.last_power += 1
		else:
			if self.last_power -10 >= self.min_power:
				self.last_power -=10
		self.slotcar_client.write_packet(sucIndicator = True, secondCar = self.slotcar_client.car_byte(0,0, int(self.last_power)), ledByte = self.slotcar_client.led_byte(1,0,0,0,0,0,1,0))
		self.slotcar_client.read_packet() # commented out because read is weird
		
#worker = simpleAI()
#worker.
		
