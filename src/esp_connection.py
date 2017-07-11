import paho.mqtt.client as paho
import sys as sys
import time
import matplotlib
import pandas as pd

# have to do this to set backend of matplotlib. otherwise now graph is displayed
matplotlib.use("TKAgg")
import matplotlib.pyplot as plt
import numpy as np
import json
import simple_ai_algorithm as ai


# possible improvement. Only loop data when ready to process data. otherwise we will get an issue with queues.
# solution would be to send data less frequently but in bigger packets or
# to have multiple mqtt queues. something to consider for later. does not seem significant now.


# directions are: 0 for y and cross acc, 1 for x and forward acc, and 2 for z and upward acc.

class EspClient:
    # need to store calibration data


    graph = None

    fig = None

    # server_ip of mqtt host, type string.
    # port number, type int. (usually the mqtt port)
    def __init__(self, server_ip="192.168.48.188", port=1883, plot=False, store=False, plot_dir=0,
                 plot_raw=False, debugging=False):
        self.server_ip = server_ip
        self.port = port

        self.client = paho.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.client.connect(server_ip, 1883)

        self.calibrating = True  # we are setting it to true from the beginning on. So it will start with calibration.
        self.num_cal = 100  # can change how many data points to use for calibration
        self.num_cal_so_far = 0  # using it to keep track of how many data points I have used so far.

        # Use this for both summing up the initial data and then storing the calibration values.
        # will be initialized in calibration process.
        self.calibration_data = None

        # will be initialized after calibration
        self.data = None

        # MPU additional numbers which should be adjusted
        self.gravity = 2  # we get values of +/-self.gravity values
        self.gyro = 250  # we get +/-self.gyro degrees/second

        # the range of the device. We are getting 16 bit values
        self.range_positive = pow(2,15) - 1
        self.range_negative = pow(2,15)

        # the names of the keys in the messages
        self.data_time = ["Time"]
        self.data_gyro = ["GyroX", "GyroY", "GyroZ"]
        self.data_acceleration = ["AcX", "AcY", "AcZ"]

        self.should_plot = plot
        self.should_store = store
        self.plot_dir = plot_dir

        self.plot_raw = plot_raw

        self.debugging = debugging

    def on_connect(self, client, userdata, flags, rc):
        # subscription will always be automatically renewed here. even
        # by connection failure
        client.subscribe("Test_topic")
        print("Connected to broker and topic")
# TODO when the device restarts i have to build something in to recalibrate and all.

    # unsubscribe and subscribe to a topic quickly when there might be issues with a message jam.
    def unsub_sub(self, topic="Test_topic"):
        self.client.unsubscribe(topic)
        self.client.subscribe(topic)


    # the call back for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
        # to have the message in the right format. The first item in the split string is the type of message sent.
        # More info in ESP8266 code
        decoded_msg = msg.payload.decode(errors="replace")
        # if decoding fails, just wait for next message. 
        if decoded_msg == "U+FFFD":
            return
        true_msg = json.loads(decoded_msg)

        # I MIGHT HAVE ISSUES WITH DOING THE SLEEP HERE. MAYBE THE DATA TRAFFIC WILL JAM.
        if self.calibrating:
            # handles first iteration to warn user 
            if self.num_cal_so_far == 0:
                print("Place the object on a flat surface. Calibration will start in 3 seconds.")
                time.sleep(1)
                print("1")
                time.sleep(1)
                print("2")
                time.sleep(1)
                print("3")
                print("Calibration will start now. Do not move the object.")
                self.unsub_sub()
                self.num_cal_so_far = self.num_cal_so_far + 1

            # handles the last cycle
            elif self.num_cal_so_far == self.num_cal:

                self.num_cal_so_far = 0
                self.calibrating = False
                self.calibration_data.drop(["Time"], axis=1)
                if self.debugging:
                    print(self.calibration_data)
                self.calibration_data = self.calibration_data.applymap(lambda x: x / self.num_cal)
                if self.debugging:
                    print(self.calibration_data)

                self.calibration_data["AcZ"] = self.calibration_data["AcZ"].map(
                    lambda x: x - (self.range_positive / 2))
                if self.debugging:
                    print(self.calibration_data)

                # next 2 lines end loading output
                sys.stdout.write("\n")
                sys.stdout.flush()
                # just to set the data, in case we have to calibrate while the program is running
                # but someone pressed RST on the ESP.
                self.data = pd.DataFrame()
                print(self.calibration_data)
                print("Calibration has ended.")
                time.sleep(3)
            # handles the middle part of the calibration
            else:
                # next 2 lines handle the loading screen output
                sys.stdout.write("#")
                sys.stdout.flush()
                
                if self.num_cal_so_far == 1:
                    # Also initializing pd.DataFrame here.
                    self.calibration_data = pd.DataFrame.from_dict(true_msg)
                else:
                    self.calibration_data += pd.DataFrame.from_dict(true_msg)
                self.num_cal_so_far = self.num_cal_so_far + 1
            
        else:
            temp_df = pd.DataFrame.from_dict(true_msg)
            if self.debugging:
                print(temp_df)
            temp_df[self.data_acceleration] = (temp_df[self.data_acceleration] - self.calibration_data[
                self.data_acceleration]) / self.range_positive * self.gravity
            if self.debugging:
                print(temp_df)
            temp_df[self.data_gyro] = (temp_df[self.data_gyro] - self.calibration_data[
                self.data_gyro]) / self.range_positive * self.gyro
            if self.debugging:
                print(temp_df)
            self.data = self.data.append(temp_df)
            if self.debugging:
                print(temp_df)





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
            # # calculates and sets the moving average
            # # direction: tells us which axis we are getting data from (int)
            # # acc_curr: the data we received (float)
            # # call after we set and received acceleration data
            # # only to be done if we are plotting
            # def calculate_moving_average(self, direction, acc_curr):
            #
            #     N = 20  # how many data points to use for moving average
            #     if len(self.acc_data[direction]) <= N:
            #         self.moving_average[direction].append(acc_curr)
            #     else:
            #         sum_time = 0
            #         acc_np = np.array(self.acc_data[direction][-N:])
            #         time_np = np.array(self.delta_time_data[-N:])
            #         average = np.cumsum(acc_np * time_np)[-1:] / (
            #         np.cumsum(time_np)[-1:][0])  # maybe weird to index again. don't like the denominator
            #         # average = np.cumsum(acc_np)[-1:][0]/N
            #         self.moving_average[direction].append(average)
            #
            # # handles the plotting of the given data
            # def plot_data(self, direction):
            #     if not (self.should_plot and (len(self.acc_data[self.plot_dir]) >= 500 and direction == self.plot_dir and (
            #             self.last_update == 0 or time.time() - self.last_update > 1))):
            #         return
            #     far_back = 500
            #     data_to_use = None
            #     if self.plot_raw:
            #         data_to_use = self.acc_data[direction][-far_back:]
            #     else:
            #         data_to_use = self.moving_average[direction][-far_back:]
            #     self.last_update = time.time()
            #     if self.graph == None:
            #         # put plt in interactive mode
            #         plt.ion()
            #         self.graph = plt.plot(self.time_data[-far_back:], data_to_use, '.')[0]
            #     self.graph.set_ydata(data_to_use)
            #     self.graph.set_xdata(self.time_data[-far_back:])
            #     plt.axis([min(self.time_data[-far_back:]), max(self.time_data[-far_back:]), -2, 2])
            #     plt.draw()
            #     plt.pause(0.01)
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
    client = EspClient()
    # good loop function since it handles reconnection for us
    client.client.loop_forever()
