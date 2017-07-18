import sys as sys
import time
import matplotlib

# have to do this to set backend of matplotlib. otherwise now graph is displayed
matplotlib.use("TKAgg")
import matplotlib.pyplot as plt
import numpy as np
import json


# for now, to get the data we should first call esp_connection. press reset when we want to
# stop the data transfer and save the data. then we can run this script.

# Note. once we get forward_velocity, for the velocity at index i we have time[i]/2 driven before and after.

# for now it handles given data. no live updating feature. needs to be implemented

class analyzing_acceleration():
    def __init__(self):
        with open("mylist.txt") as f:  # in read mode, not in write mode, careful. 'r' is assumed
            pre_data = json.load(f)
            self.data = np.array(pre_data)
        self.data[0] = self.data[0] * 0.001  # scaling milliseconds
        self.data[1:] = self.data[1:] * [9.8]  # scaling gravity
        # self.data[2] = self.data[2] #seemed to be negative. not anymore?
        self.forward_dir = 2
        # self.set_as_moving_average()
        self.thetas = None  # in radians
        self.velocity_forward = None
        self.delta_forward_distance = None
        self.y_displacement = None
        self.x_displacement = None
        self.set_position()

    # provides a list of horizontal velocity data. Assuming that we had never turned.
    # will be used by other algorithms.
    # use time as the time from the last data point to the current. so we could use a left handed rieman sum.
    # due to noise i will choose the midpoint one though and weigh by the
    # time with the same index as the later data point.
    # forward direction is given by y axis from accelerometer
    def set_velocity_data(self):

        # a_acc = self.data[forward_dir]
        # b_acc = np.append([0], a_acc[:-1])
        # self.combined_acc = (a_acc + b_acc)/2 #getting averages. might be dangerous to get combined acc here
        self.velocity_forward = np.cumsum(self.data[self.forward_dir] * self.data[0])

    def set_delta_forward_distance(self):
        if self.velocity_forward == None:
            self.set_velocity_data()
        self.delta_forward_distance = self.velocity_forward * self.data[0]

    # calculates teh angle of the car from it's initial forward direction.
    # using formula theta*r = l (arc)
    def set_direction_angles(self):
        if self.velocity_forward == None:
            self.set_velocity_data()
        if self.delta_forward_distance == None:
            self.set_delta_forward_distance()
        radii = self.velocity_forward ** 2 / self.data[self.forward_dir]
        self.thetas = self.delta_forward_distance / radii

    # calculates the y and x displacement
    def set_position(self):
        if self.velocity_forward == None:
            self.set_velocity_data()
        if self.delta_forward_distance == None:
            self.set_delta_forward_distance()
        if self.thetas == None:
            self.set_direction_angles()
        y_weights = np.cos(self.thetas)
        x_weights = np.sin(self.thetas)
        self.y_displacement = np.cumsum(y_weights * self.delta_forward_distance)
        self.x_displacement = np.cumsum(x_weights * self.delta_forward_distance)

    def plot_data(self):
        self.graph = plt.plot(np.cumsum(self.data[0]), (self.data[2]), '.')[0]
        plt.show()

    # calculates and sets the moving average
    # direction: tells us which axis we are getting data from (int)
    # acc_curr: the data we received (float)
    # call after we set and received acceleration data
    # only to be done if we are plotting
    def set_as_moving_average(self):
        how_far = 50
        for j in range(1, 4):
            for i in range(how_far, len(self.data[j])):
                self.data[j][i - how_far - 1] = np.cumsum(self.data[j][i - how_far:i] * self.data[0][i - how_far:i])[
                                                -1:]


if __name__ == "__main__":
    analyze_acc = analyzing_acceleration()
    analyze_acc.plot_data()
