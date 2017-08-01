import pandas as pd
import numpy as np
import multiprocessing as mp
import time




class DataManipulation:
    def __init__(self):
        return



    # calculates and sets the moving average
    # direction: tells us which axis we are getting data from (int)
    # call after we set and received acceleration data
    # data parameter expects it in a certain format
    def calculate_moving_average(self, to_average_data, time_data, far_back, num_average_over=20):
        if to_average_data.shape[0] < num_average_over:
            return

        # here we set the window through which we will convolve and also normalize scalars
        # TODO do a nonlinear normalization. e.g. an exponentially increasing scaling which gives more recent
        # Todo datapoints more importance.
        window = np.repeat(1, num_average_over) / num_average_over

        if to_average_data.shape[0] < num_average_over:
            data = to_average_data[far_back:]
            data = data * time_data[far_back:, ]
            temp = np.convolve(data, window, 'same')
        else:
            # need to append extra data from what we have to make moving averages more accurate
            data = to_average_data[far_back - (num_average_over-1):]
            data = data * time_data[far_back - (num_average_over-1):, ]
            temp = np.convolve(data, window, 'valid')
        return temp

