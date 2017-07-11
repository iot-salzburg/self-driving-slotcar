import paho.mqtt.client as paho
import sys as sys
import time
import pandas as pd
import multiprocessing as mp



import numpy as np
import json




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
        self.server_ip=server_ip
        self.port = 1883
        self.client.connect(server_ip, 1883)

        self.calibrating = True  # we are setting it to true from the beginning on. So it will start with calibration.
        self.num_cal = 100  # can change how many data points to use for calibration
        self.num_cal_so_far = 0  # using it to keep track of how many data points I have used so far.

        # Use this for both summing up the initial data and then storing the calibration values.
        # will be initialized in calibration process.
        self.calibration_data = None

        # will be set by process which initializes this class. We are not
        # going to worry about the case where the esp resets and will hence
        # not reinitialize this.
        self.data = None

        # MPU additional numbers which can be adjusted
        self.gravity = 2  # we get values of +/-self.gravity values
        self.gyro = 250  # we get +/-self.gyro degrees/second

        # the range of the device. We are getting 16 bit values
        self.range_positive = pow(2,15) - 1
        self.range_negative = pow(2,15)

        # the names of the keys in the messages
        self.data_time = ["Time"]
        self.data_gyro = ["GyroX", "GyroY", "GyroZ"]
        self.data_acceleration = ["AcX", "AcY", "AcZ"]

        self.debugging = debugging

        self.index_data = {}
        self.norm_const = np.empty([7])

        # the time at which i started to wait. make -1 if not yet started.
        self.wait_time = -1

    def on_connect(self, client, userdata, flags, rc):
        # subscription will always be automatically renewed here. even
        # by connection failure
        client.subscribe("Test_topic")
        print("Connected to broker and topic")
# TODO when the device restarts i have to build something in to recalibrate and all.



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
                if self.wait_time == -1:
                    print("Place the object on a flat surface. Calibration will start in 3 seconds.")
                    self.wait_time = time.time()
                elif time.time() - self.wait_time >= 3:
                    print("Calibration will start now. Do not move the object.")
                    self.num_cal_so_far = self.num_cal_so_far + 1
                    self.wait_time = -1


            # handles the last cycle
            elif self.num_cal_so_far == self.num_cal:
                if self.wait_time == -1:
                    self.calibration_data = self.calibration_data / self.num_cal
                    self.calibration_data[self.index_data["AcZ"]] = self.calibration_data[self.index_data["AcZ"]]- (self.range_positive / 2)
                    # next 2 lines end loading output
                    sys.stdout.write("\n")
                    sys.stdout.flush() 
                    print("Calibration has ended.")
                    print("Data transfer will start in one second.")
                    self.wait_time = time.time()
                    self.init_queue.put(self.calibration_data)
                elif time.time() - self.wait_time >= 1:
                    self.wait_time = -1
                    self.num_cal_so_far = 0
                    self.calibrating = False

            # handles the middle part of the calibration
            else:
                #set calibration np
                if self.num_cal_so_far == 1:
                    keys = list(true_msg[0].keys())
                    # so arithmatic will be easier later on
                    true_msg[0]["Time"] = 0
                    for i in range(len(keys)):
                        if "Ac" in keys[i]:
                            self.norm_const[i] = self.gravity/self.range_positive
                        elif "Gyro" in keys[i]:
                            self.norm_const[i] = self.gyro/self.range_positive
                        else:
                            self.norm_const[i] = 1
                        self.index_data[keys[i]] = i
                    self.init_queue.put(self.norm_const)
                    self.init_queue.put(self.index_data)
                    self.calibration_data = np.array(list(true_msg[0].values()),float)
                else:
                    self.calibration_data = self.calibration_data + np.array(list(true_msg[0].values()),float)
                self.num_cal_so_far = self.num_cal_so_far + 1

                 # next 2 lines handle the loading screen output
                sys.stdout.write("#")
                sys.stdout.flush()
            
        else:
            temp_data = np.array(list(true_msg[0].values()), float)
            self.data.put(temp_data) # message is sent in a list.
            if self.debugging:
                print(temp_data)

    # set the queue through which data should be received.
    def start_esp(self, data_queue,init_queue):
        self.data = data_queue
        self.init_queue = init_queue
        self.client.loop_forever()


    def disconnect(self):
        self.client.disconnect()

    def connect():
        self.client.connect(self.server_ip, self.port)







if __name__ == "__main__":
    client = EspClient(debugging=True)
    # good loop function since it handles reconnection for us
    client.client.loop_forever()
