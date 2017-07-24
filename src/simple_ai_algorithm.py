import time
import numpy as np
import Data_Manipulation as dm
import AI_Base


class SimpleAI(AI_Base.BaseAI):
    def __init__(self, carID=2):
        super.__init__(carID = carID)
        self.max_acceleration = 1 * 0.23  # m/9.8*s^2 Calculates by estimating force of friction with a slope and raeding off accelerometer data
        self.error_margin = 0.09  # m/s^2
        self.game_started = False
        self.last_power = 5
        self.min_power = 5
        self.max_power = 25  # max potential as shown in protocol. we can adjust the max we want here

        self.moving_averages = np.empty([0, 7])
        self.data_manip = dm.DataManipulation()

    # expecting last_cross_acceleration in m/s^2
    def main(self):
        """The main loop which handles the algorithm."""
        while True:
            last = self.data[-5:, self.index_data["AcX"]].cumsum()[-1:]/5
            # last = self.data[-1: , self.index_data["AcX"]]
            print(last)
            if abs(last) > self.max_acceleration:
                # call function which reduces acceleration
                self.change_power(increase=False)
            elif abs(last) > self.max_acceleration - self.error_margin:
                # retain current speed
                continue
            else:
                # increase current speed
                self.change_power(increase=True)

    def change_power(self, increase):
        """Changes the power which is delivered to the slotcar on the track."""
        if increase:
            if self.last_power + 1 <= self.max_power:
                self.last_power += 1
            else:
                self.last_power = self.max_power
        else:
            if self.last_power - 6 >= self.min_power:
                self.last_power -= 6
            else:
                self.last_power = self.min_power
        print(self.last_power)
        self.slotcar_client.write_packet(sucIndicator=True,
                                         secondCar=self.slotcar_client.car_byte(0, 0, int(self.last_power)),
                                         ledByte=self.slotcar_client.led_byte(1, 0, 0, 0, 0, 0, 1, 0))
        self.slotcar_client.read_packet()  # commented out because read is weird



if __name__ == "__main__":
    ai = SimpleAI()
    ai.start_me()
