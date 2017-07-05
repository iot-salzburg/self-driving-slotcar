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

class espClient():
    # need to store calibration data
    num_g = 2
    norm = [0, 0, 0]
    offsets = [0, 0, 0]
    cal = False
    upper_bound = 32767
    lower_bound = -32768
    start = False

    # PANDAS dataframe to store all data
    data = pd.DataFrame()
    # moving_average = [[], [], []]
    # time_data = []
    # delta_time_data = []  # to compute moving average. might be solved differently/better
    graph = None
    last_update = 0

    fig = None

    # server_ip of mqtt host, type string.
    # port number, type int. (usually the mqtt port)
    def __init__(self, server_ip="192.168.48.188", port=1883, plot=False, store=False, plot_dir=0, should_ai=False,
                 plot_raw=False):
        self.server_ip = server_ip
        self.port = port

        self.simpleAI = ai.simpleAI()

        self.client = paho.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.client.connect(server_ip, 1883)

        self.should_plot = plot
        self.should_store = store
        self.plot_dir = plot_dir

        self.last_ai_time = 0
        self.should_ai = should_ai
        self.plot_raw = plot_raw

    def on_connect(self, client, userdata, flags, rc):
        # subscription will always be automatically renewed here. even
        # by connection failure
        client.subscribe("Test_topic")
        print("Connected to broker and topic")

    # the call back for when a PUBLISH message is re   ceived from the server.
    def on_message(self, client, userdata, msg):
        # to have the message in the right format. The first item in the split string is the type of message sent.
        # More info in ESP8266 code
        true_msg = json.load(msg.payload.decode())
        print(true_msg)
        return
        # command that tells us that we should get ready. calibration will start soon.
        if msg_indicator == "0":
            print(msg_body)
            self.start = False
            self.store_data()
        # the command that calibration will now begin.
        # (Maybe esp should send a message with how many calibration messages i will get. actually,
        # shouldn't matter, i should be able to decide when to start.)
        elif msg_indicator == "2":
            print(msg_body)
            self.cal = True
            self.norm = [0, 0, 0]
            self.offsets = [0, 0, 0]
        # ending calibration. Setting all relevent calibration data
        elif msg_indicator == "3":
            self.cal = False
            for i in range(3):
                # for the z axis to make it calibrated to 1g
                if (i == 2):
                    self.offsets[i] = self.offsets[i] / 20 - self.upper_bound / 2
                else:
                    self.offsets[i] = self.offsets[i] / 20
                self.norm[i] = (self.upper_bound) / self.num_g
            sys.stdout.write("\n")
            sys.stdout.flush()
            print(msg_body)
        # storing the values from calibration. I could combine it with "print correct acceleration" if statement.
        elif self.cal:
            time_split = msg_body.split(".|")
            split_msg = time_split[0].split(" ")
            direction = ord(split_msg[0]) - ord('X')
            self.offsets[direction] += int(split_msg[2])
            sys.stdout.write("#")
            sys.stdout.flush()
        # I want to get rid of this. For now it helps me start data transfer
        elif msg_indicator == "4":
            print(msg_body)
            self.start = True

        # print correct acceleration
        elif not self.cal and self.start:
            time_split = msg_body.split(".|")
            split_msg = time_split[0].split(" ")
            direction = ord(split_msg[0]) - ord('X')

            new_acc = (int(split_msg[2]) - self.offsets[direction]) / self.norm[direction]

            if len(self.acc_data[0]) == 0 and direction != 0:
                return

            self.acc_data[direction].append(new_acc)

            self.set_time_data(direction, int(time_split[1]))

            self.calculate_moving_average(direction, new_acc)

            if direction == 0 and len(
                    self.moving_average[direction]) > 0 and time.time() - self.last_ai_time > 0.05 and self.should_ai:
                self.last_ai_time = time.time()
                temp_time = time.time()
                self.simpleAI.main(self.moving_average[0][-1:][
                                       0] * 9.8)
                # calling the simple algorithm here. kinda weird. should make it more lean, kinda too bulcky
            # print("Delta time: " + str(time.time() - temp_time))

            self.plot_data(direction)
            if self.should_plot:
                print("time: " + str(time_split[1]))
                print(msg.topic + " " + chr(direction + ord('X')) + ": " + str(new_acc))

    def set_time_data(self, direction, time):
        # should be updated once i will fix how the esp transmits data. we will only use one time
        # data point for all 3 axis.
        if direction != 0:
            return
        self.delta_time_data.append(time)
        # doing this since i am assuimnig that one addition is faster than calling
        # cumsum all the time. this is only needed to plot data anyway
        if not self.should_plot:
            return
        if len(self.time_data) == 0:
            self.time_data.append(time)
        else:
            last_time = self.time_data[-1:][0]  # maybe inefficient
            self.time_data.append(time + last_time)

    # calculates and sets the moving average
    # direction: tells us which axis we are getting data from (int)
    # acc_curr: the data we received (float)
    # call after we set and received acceleration data
    # only to be done if we are plotting
    def calculate_moving_average(self, direction, acc_curr):

        N = 20  # how many data points to use for moving average
        if len(self.acc_data[direction]) <= N:
            self.moving_average[direction].append(acc_curr)
        else:
            sum_time = 0
            acc_np = np.array(self.acc_data[direction][-N:])
            time_np = np.array(self.delta_time_data[-N:])
            average = np.cumsum(acc_np * time_np)[-1:] / (
            np.cumsum(time_np)[-1:][0])  # maybe weird to index again. don't like the denominator
            # average = np.cumsum(acc_np)[-1:][0]/N
            self.moving_average[direction].append(average)

    # handles the plotting of the given data
    def plot_data(self, direction):
        if not (self.should_plot and (len(self.acc_data[self.plot_dir]) >= 500 and direction == self.plot_dir and (
                self.last_update == 0 or time.time() - self.last_update > 1))):
            return
        far_back = 500
        data_to_use = None
        if self.plot_raw:
            data_to_use = self.acc_data[direction][-far_back:]
        else:
            data_to_use = self.moving_average[direction][-far_back:]
        self.last_update = time.time()
        if self.graph == None:
            # put plt in interactive mode
            plt.ion()
            self.graph = plt.plot(self.time_data[-far_back:], data_to_use, '.')[0]
        self.graph.set_ydata(data_to_use)
        self.graph.set_xdata(self.time_data[-far_back:])
        plt.axis([min(self.time_data[-far_back:]), max(self.time_data[-far_back:]), -2, 2])
        plt.draw()
        plt.pause(0.01)

    # stores n data points locally. To store data, let the program run and the press reset.
    def store_data(self):
        if not self.should_store:
            return
        t = self.delta_time_data
        a = self.acc_data
        how_long = min(len(t), len(a[0]), len(a[1]), len(a[2]))
        to_store = [t[:how_long], a[0][:how_long], a[1][:how_long], a[2][:how_long]]
        with open("mylist.txt", "w") as f:  # in write mode
            f.write(json.dumps(to_store))


client = espClient(store=True)
# good loop function since it handles reconnection for us
client.client.loop_forever()
