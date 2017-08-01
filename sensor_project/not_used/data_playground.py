import pandas as pd
import numpy as np
import esp_connection as esp
import multiprocessing as mp
import time

import matplotlib

# have to do this to set backend of matplotlib. otherwise no graph is displayed
matplotlib.use("TKAgg")
import matplotlib.pyplot as plt


class DataPlayground:
    def __init__(self):
        self.index_data = None
        self.norm_const = None
        self.calibration_data = None

        self.np_data = None
        self.esp_data = None

        self.init_queue = None
        self.init_done = False

        self.graph = None

        self.moving_averages = np.empty([0, 7])

        # set in init_from_queue
        self.gravity = -1
        self.gyro = -1

    # n is the number of data points I will pull
    def get_new_data(self):
        size = self.esp_data.qsize()
        # because we have 7 datapoints
        temp = np.empty([size, 7])
        # really optimal ?
        for i in range(size):
            data = self.esp_data.get()
            temp[i] = data
        temp = (temp - self.calibration_data) * self.norm_const
        if self.np_data == None:
            self.np_data = temp
        else:
            self.np_data = np.append(self.np_data, temp, axis=0)
        # plotting here

        self.calculate_moving_average(self.index_data["GyroX"])
        # plotting here
        if self.np_data.shape[0] > 500:
            self.plot_data(self.index_data["GyroX"])

    # currently the data is put in and got in this order
    def init_from_queue(self):
        self.norm_const = self.init_queue.get()
        self.index_data = self.init_queue.get()
        self.calibration_data = self.init_queue.get()
        self.gravity = self.init_queue.get()
        self.gyro = self.init_queue.get()
        self.init_done = True

    def plot_data(self, direction):
        far_back = 500
        data_to_use = self.moving_averages[-far_back:, direction]
        time_to_use = self.np_data[-far_back:, self.index_data["Time"]]
        if self.graph is None:
            # put plt in interactive mode
            plt.ion()
            self.graph = plt.plot(time_to_use, data_to_use)[0]
        self.graph.set_ydata(data_to_use)
        self.graph.set_xdata(time_to_use)
        plt.axis([min(time_to_use), max(time_to_use), -250, 250])
        plt.draw()
        plt.pause(0.01)

    # calculates and sets the moving average
    # direction: tells us which axis we are getting data from (int)
    # call after we set and received acceleration data
    def calculate_moving_average(self, direction, num_average_over=20):
        if self.np_data.shape[0] < num_average_over:
            return

        # here we set the window through which we will convolve and also normalize scalars
        # TODO do a nonlinear normalization. e.g. an exponentially increasing scaling which gives more recent
        # Todo datapoints more importance.
        window = np.repeat(1, num_average_over) / num_average_over

        if self.moving_averages.shape[0] < num_average_over:
            data = self.np_data[direction, self.moving_averages.shape[0]:]
            data = data * self.np_data[self.index_data["Time"]][self.moving_averages.shape[0]:, ]
            temp = np.convolve(data, window, 'same')
        else:
            # need to append extra data from what we have to make moving averages more accurate
            data = self.np_data[direction, self.moving_averages.shape[0] - (num_average_over-1):]
            data = data * self.np_data[self.index_data["Time"]][self.moving_averages.shape[0] - (num_average_over-1):, ]
            temp = np.convolve(data, window, 'valid')
        self.moving_averages = np.append(self.moving_averages, np.empty([temp.shape[0], 7]), axis=0)
        self.moving_averages[-temp.shape[0]:, direction] = temp

    def start_communication(self):
        # not setting it as instance variable since we can not
        # properly communicate with it anyway.
        espClient = esp.EspClient()
        play = DataPlayground()
        play.init_queue = mp.Queue()
        play.esp_data = mp.Queue()
        p = mp.Process(target=espClient.start_esp, args=(play.esp_data, play.init_queue,))
        p.start()
        while True:
            # need to know how many things will be put in the queue beforehand.
            if play.init_queue.qsize() == 5:
                play.init_from_queue()
            if play.init_done:
                play.get_new_data()



if __name__ == "__main__":
    # not setting it as instance variable since we can not
    # properly communicate with it anyway.
    espClient = esp.EspClient(raw_data=True)
    play = DataPlayground()
    play.init_queue = mp.Queue()
    play.esp_data = mp.Queue()
    p = mp.Process(target=espClient.start_esp, args=(play.esp_data, play.init_queue,))
    p.start()
    while True:
        # need to know how many things will be put in the queue beforehand.
        if play.init_queue.qsize() == 5:
            play.init_from_queue()
        if play.init_done:
            play.get_new_data()
        time.sleep(1)
