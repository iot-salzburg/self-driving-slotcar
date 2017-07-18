import slotcar_control as scc
import esp_connection as esp
import multiprocessing as mp
import time
import numpy as np
import Data_Manipulation as dm


class SimpleAI():
    def __init__(self, carID=2):
        self.max_acceleration = 9.8 * 0.15  # m/s^2 Calculates by estimating force of friction with a slope and raeding off accelerometer data
        self.slotcar_client = scc.slotcarClient()
        self.error_margin = 1  # m/s^2
        self.carID = carID
        self.game_started = False
        self.last_power = 5
        self.min_power = 5
        self.max_power = 30  # max potential as shown in protocol. we can adjust the max we want here

        # set in init_from_queue
        self.gravity = -1
        self.gyro = -1

        self.index_data = None

        self.data = None
        self.esp_data = None

        self.init_queue = None
        self.init_done = False

        self.moving_averages = np.empty([0, 7])

        self.data_manip = dm.DataManipulation()

    # expecting last_cross_acceleration in m/s^2
    def main(self):

        self.init_from_queue()
        while True:
            self.get_new_data()
            last_cross_acceleration = self.data[-20:, self.index_data["AcY"]].cumsum()[-1:]/20
            if abs(last_cross_acceleration) > self.max_acceleration:
                # call function which reduces acceleration
                self.change_power(increase=False)
                return
            elif abs(last_cross_acceleration) > self.max_acceleration - self.error_margin:
                # retain current speed
                return
            else:
                # increase current speed
                self.change_power(increase=True)

    def change_power(self, increase):
        if increase:
            if self.last_power + 1 <= self.max_power:
                self.last_power += 1
        else:
            if self.last_power - 10 >= self.min_power:
                self.last_power -= 10
        self.slotcar_client.write_packet(sucIndicator=True,
                                         secondCar=self.slotcar_client.car_byte(0, 0, int(self.last_power)),
                                         ledByte=self.slotcar_client.led_byte(1, 0, 0, 0, 0, 0, 1, 0))
        self.slotcar_client.read_packet()  # commented out because read is weird

    # n is the number of data points I will pull
    def get_new_data(self):
        size = self.esp_data.qsize()
        # because we have 7 datapoints
        temp = np.empty([size, 7])
        for i in range(size):
            data = self.esp_data.get()
            temp[i] = data
        if self.data == None:
            self.data = temp
        else:
            self.data = np.append(self.data, temp, axis=0)

    # currently the data is put in and got in this order
    def init_from_queue(self):
        while self.init_queue.qsize != 5:
            continue
        self.index_data = self.init_queue.get()
        self.gravity = self.init_queue.get()
        self.gyro = self.init_queue.get()
        self.init_done = True

    def start_me(self):
        # not setting it as instance variable since we can not
        # properly communicate with it anyway.
        espClient = esp.EspClient()
        self.init_queue = mp.Queue()
        self.esp_data = mp.Queue()
        p = mp.Process(target=espClient.start_esp, args=(self.esp_data, self.init_queue,))
        p.start()


if __name__ == "__main__":
    ai = SimpleAI()
    ai.start_me()
