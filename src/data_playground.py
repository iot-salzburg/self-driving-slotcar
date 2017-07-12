import pandas as pd
import numpy as np
import esp_connection as esp
import multiprocessing as mp
import time

import matplotlib
# have to do this to set backend of matplotlib. otherwise now graph is displayed
matplotlib.use("TKAgg")
import matplotlib.pyplot as plt


class DataPlayground:
    def __init__(self):
        self.index_data = None
        self.norm_const = None
        self.calibtration_data = None

        self.np_data = None
        self.esp_data = None

        self.init_queue = None
        self.init_done = False

        self.graph = None

        self.moving_averages = np.empty([0,7])

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
        
        
    def init_from_queue(self):
        self.norm_const = self.init_queue.get()
        self.index_data = self.init_queue.get()
        self.calibration_data = self.init_queue.get()
        self.init_done = True

        
    def plot_data(self, direction):
        far_back = 500
        data_to_use = self.moving_averages[-far_back:, direction]
        time_to_use = self.np_data[-far_back:, self.index_data["Time"]]
        if self.graph == None:
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
    # acc_curr: the data we received (float)
    # call after we set and received acceleration data
    # only to be done if we are plotting

    #TODO add time scaling
    def calculate_moving_average(self, direction):
        N = 20
        if self.np_data.shape[0] < N:
            return

        data = self.np_data[self.moving_averages.shape[0]:,direction]
        window = np.repeat(1,N)/N
        temp = None

        if self.moving_averages.shape[0] < N:
            data = data * self.data_np[self.index_data["Time"]][self.moving_averages.shape[0]:,]
            temp = np.convolve(data, window, 'same')
        else:
            data = np.append(self.moving_averages[-19:,direction], data)
            temp = np.convolve(data, window, 'valid')
        self.moving_averages = np.append(self.moving_averages, np.empty([temp.shape[0], 7]), axis=0)
        self.moving_averages[-temp.shape[0]:,direction] = temp
        










            


    
            #
            #         self.acc_data[direction].append(new_acc)
            #
            #         self.set_time_data(direction, int(time_split[1]))
            #
            #         self.calculate_moving_average(direction, new_acc)
            #
            #         self.plot_data(direction)
            #
            #
            # def set_time_data(self, direction, time):
            #     # should be updated once i will fix how the esp transmits data. we will only use one time
            #     # data point for all 3 axis.
            #     if direction != 0:
            #         return
            #     self.delta_time_data.append(time)
            #     # doing this since i am assuimnig that one addition is faster than calling
            #     # cumsum all the time. this is only needed to plot data anyway
            #     if not self.should_plot:
            #         return
            #     if len(self.time_data) == 0:
            #         self.time_data.append(time)
            #     else:
            #         last_time = self.time_data[-1:][0]  # maybe inefficient
            #         self.time_data.append(time + last_time)
        #

             # handles the plotting of the given data

            #
            # # stores n data points locally. To store data, let the program run and the press reset.
            # def store_data(self):
            #     if not self.should_store:
            #         return
            #     t = self.delta_time_data
            #     a = self.acc_data
            #     how_long = min(len(t), len(a[0]), len(a[1]), len(a[2]))
            #     to_store = [t[:how_long], a[0][:how_long], a[1][:how_long], a[2][:how_long]]
            #     with open("mylist.txt", "w") as f:  # in write mode
            #         f.write(json.dumps(to_store))

if __name__ == "__main__":
    # not setting it as instance variable since we can not
    # properly communicate with it anyway.
    espClient = esp.EspClient()
    play = DataPlayground()
    play.init_queue = mp.Queue()
    play.esp_data = mp.Queue()
    p = mp.Process(target=espClient.start_esp, args=(play.esp_data,play.init_queue,))
    p.start()
    while True:
        if play.init_queue.qsize() == 3:
            play.init_from_queue()
        if play.init_done:
            play.get_new_data()
        time.sleep(1)
