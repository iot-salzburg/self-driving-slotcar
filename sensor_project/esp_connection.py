import paho.mqtt.client as paho
import sys as sys
import time
import multiprocessing as mp

import numpy as np
import json


# names.keys of items in messages "Time", "GyroX", "GyroY", "GyroZ", "AcX", "AcY", "AcZ"

# possible improvement. Only loop data when ready to process data. otherwise we will get an issue with queues.
# solution would be to send data less frequently but in bigger packets or
# to have multiple mqtt queues. something to consider for later. does not seem significant now.

class EspClient:
    """The class which handles the communication with the ESP device.
    Relevant attributes:
        self.server_ip:
                    The ip address of the mqtt host. In the current case, we are using a Raspberry pi, which 
                    has to be connected over sensornet.
        self.port:
                The port for mqtt services. Standard is 1883.
        self.debugging:
                    Whether to print certain statements and print all the data which is received.
        self.raw_data:
                    Should the data be put in the queue for the algorithm without being normalized and offset.
        self.num_cal:
                How many data points should be used to calibrate (can be modified if wanted).
        self.data:
                Is the queue which we receive from the baseAI class through which we can communicate the data we 
                receive.
        self.gravity:
                The gravity range setting of the MPU. We get +/-self.gravity m/s^2 values.
        self.gyro:
                The gyroscope range setting of the MPU. We get +/-self.gyro degrees/second.
        self.index_data:
                    A mapping of names  "Time", "GyroX", "GyroY", "GyroZ", "AcX", "AcY", "AcZ" to indexes in the 
                    self.data array (2nd level). 
        self.norm_const:
                    The normalization constants for calculating the adjusted data values received from the esp.
                    e.g. AcX_data has to be transformed to (AcX_data - offset) * norm_const = 
                    (AcX_data - offset)/self.range_pos * self. gravity.
        self.init_queue:
                    The multiprocessing queue through which all
                    relevant data which is not sensor data will be transmitted. The first item will tell
                    how many elements to expect.

        """

    def __init__(self, server_ip="192.168.48.188", port=1883, debugging=False, raw_data=False):
        self.server_ip = server_ip
        self.port = port

        self.client = paho.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.server_ip = server_ip
        self.port = port
        self.client.connect(server_ip, self.port)

        self.calibrating = True  # we are setting it to true from the beginning on. So it will start with calibration.
        self.num_cal = 100  # can change how many data points to use for calibration
        self.num_cal_so_far = 0  # using it to keep track of how many data points I have used so far.

        # Use this for both summing up the initial data and then storing the calibration values.
        # will be initialized in calibration process.
        self.calibration_data = None

        self.data = None

        # MPU additional numbers which can be adjusted
        self.gravity = 2  # we get values of +/-self.gravity values
        self.gyro = 250  # we get +/-self.gyro degrees/second

        # the range of the device. We are getting 16 bit values
        self.range_positive = pow(2, 15) - 1
        self.range_negative = pow(2, 15)

        self.debugging = debugging

        self.index_data = {}
        self.norm_const = np.empty([7])

        # the time at which i started to wait. make -1 if not yet started.
        self.wait_time = -1

        # whether to return only raw data
        self.raw_data = raw_data

        self.init_queue = None

    def on_connect(self, client, userdata, flags, rc):
        """subscription will always be automatically renewed here. even
        by connection failure"""
        client.subscribe("Test_topic")
        print("Connected to broker and topic")

    # TODO Note, we are not recalibrating when the device restarts.
    # the call back for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
        """Will be called when we receive a message. 
        This method calibrates, transforms and stores the data accoridingly."""
        decoded_msg = msg.payload.decode(errors="replace")
        # if decoding fails, just wait for next message. 
        if decoded_msg == "U+FFFD":
            return
        true_msg = json.loads(decoded_msg)

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
                    self.calibration_data[self.index_data["AcZ"]] = self.calibration_data[self.index_data["AcZ"]] - (
                        self.range_positive / self.gravity)
                    # next 2 lines end loading output
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    print("Calibration has ended.")
                    print("Data transfer will start in one second.")
                    self.wait_time = time.time()
                    if self.raw_data:
                        self.init_queue.put(self.calibration_data)
                    self.init_queue.put(self.gravity)
                    self.init_queue.put(self.gyro)
                elif time.time() - self.wait_time >= 1:
                    self.wait_time = -1
                    self.num_cal_so_far = 0
                    self.calibrating = False

            # handles the middle part of the calibration
            else:
                true_msg[0]["Time"] = 0
                # set calibration np
                if self.num_cal_so_far == 1:
                    keys = list(true_msg[0].keys())
                    # so arithmatic will be easier later on
                    # doing two things at once. setting const_norm and setting index_data
                    for i in range(len(keys)):
                        if "Ac" in keys[i]:
                            self.norm_const[i] = self.gravity / self.range_positive
                        elif "Gyro" in keys[i]:
                            self.norm_const[i] = self.gyro / self.range_positive
                        else:
                            self.norm_const[i] = 1
                        self.index_data[keys[i]] = i
                    if self.raw_data:
                        self.init_queue.put(self.norm_const)
                    self.init_queue.put(self.index_data)
                    self.calibration_data = np.array(list(true_msg[0].values()), float)
                else:
                    self.calibration_data = self.calibration_data + np.array(list(true_msg[0].values()), float)
                self.num_cal_so_far = self.num_cal_so_far + 1

                # next 2 lines handle the loading screen output
                sys.stdout.write("#")
                sys.stdout.flush()

        else:
            temp_data = np.array(list(true_msg[0].values()), float)
            if self.raw_data:
                self.data.put(temp_data)  # message is sent in a list.
            else:
                self.data.put((temp_data - self.calibration_data) * self.norm_const)
            if self.debugging:
                print(list(true_msg[0].values()))
                print(temp_data)

    def start_esp(self, data_queue, init_queue):
        """Call this method to start the communication with the ESP device. Also, provide a 
        multiprocessing queue through which the esp can communicate its data. If we are handling raw input
        we put 5 items in the init_queue, otherwise 3. This will be told to the receiver by putting the number of
        items to expect at the beginning of the queue."""
        self.data = data_queue
        self.init_queue = init_queue
        # put in how many elements to expect.
        if self.raw_data:
            self.init_queue.put(5)
        else:
            self.init_queue.put(3)
        self.client.loop_forever()



if __name__ == "__main__":
    client = EspClient(debugging=True)
    # good loop function since it handles reconnection for us
    client.client.loop_forever()
