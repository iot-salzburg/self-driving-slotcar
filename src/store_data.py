import time
import numpy as np
import Data_Manipulation as dm
import AI_Base
import json

class StoreData(AI_Base.BaseAI):
    """Stores 5 laps worth of data."""
    def __init__(self, carID=2, print_power=False, print_lap_times=True):
        super().__init__(carID=carID)
        self.power = 12

        self.moving_averages = np.empty([0, 7])
        self.data_manip = dm.DataManipulation()

        self.print_power = print_power
        self.print_lap_times = print_lap_times

        self.seconds = 20

        self.num_laps=10
        self.count_num_laps = 0
        self.global_time = -1

    # expecting last_cross_acceleration in m/s^2
    def main(self):
        """The main loop which handles the algorithm."""
        print("The data storing has started.")
        start_time = time.time()
        #while self.count_num_laps < self.num_laps:
        while time.time() - start_time < self.seconds:
            print(int(time.time() - start_time))
        #     self.slotcar_client.write_packet(sucIndicator=True,
        #                                      secondCar=self.slotcar_client.car_byte(0, 0, int(self.power)),
        #                                      ledByte=self.slotcar_client.led_byte(1, 0, 0, 0, 0, 0, 1, 0))
        #     self.slotcar_client.read_packet()
        #     if self.slotcar_client.car_times[self.car_time_index][1] != self.global_time:
        #         self.global_time = self.slotcar_client.car_times[self.car_time_index][1]
        #         self.count_num_laps += 1
        #         print("Number of laps: " + str(self.count_num_laps))
        #
        #
        # self.slotcar_client.write_packet(sucIndicator=True,
        #             secondCar=self.slotcar_client.car_byte(0, 0, int(0)),
        #             ledByte=self.slotcar_client.led_byte(1, 0, 0, 0, 0, 0, 1, 0))
        with open("data_10_laps", 'w') as f:
            f.write(json.dumps([self.index_data, self.data.tolist()]))
        print("Done storing data.")



if __name__ == "__main__":
    worker = StoreData()
    worker.start()
    worker.main()
