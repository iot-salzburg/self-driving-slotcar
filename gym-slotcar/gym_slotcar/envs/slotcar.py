"""
http://incompleteideas.net/sutton/MountainCar/MountainCar1.cp
permalink: https://perma.cc/6Z2N-PFWC
"""

import math
import gym
from gym import error, spaces, utils
from gym.utils import seeding

import serial
import numpy as np
import time


class Slotcar(gym.Env):
    metadata = {

    }

    def __init__(self):
        worker = SlotcarClient(port="/dev/tty.usbserial-AI05FT0P")

        self.max_power = 30
        self.min_power = 1


        self.action_space = spaces.MultiDiscrete([self.min_power, self.max_power+1])
        #index 0 = radius, index 1 = angle, index 2 = power
        self.observation_space = spaces.MultiDiscrete([[0, 500], [0,360], [self.min_power, self.max_power+1]])

        self._seed()
        self.reset()

    def _seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def _step(self, action):
        assert self.action_space.contains(action), "%r (%s) invalid" % (action, type(action))

        radius, angle, power = self.state
        power += action
        power = np.clip(power, self.min_power, self.max_power)
        worker.write_packet(secondCar=worker.car_byte(False, False, power))
        worker.read_packet()

        #angle, radius = # get position from hannes

        done = bool(angle == 0)
        reward = -1.0

        self.state = (radius, angle, power)
        return np.array(self.state), reward, done, {}

    def _reset(self):
        self.state = np.array([0, 0, self.np_random.uniform(low=self.min_power, high=self.max_power)])
        return np.array(self.state)






# TODO reset the slotcar client when initialized
class SlotcarClient:
    """
    The class which handles the communication with the SlotCar track (currently 6 car power base).
    Protocol based on http://ssdc.jackaments.com/saved/C7042_6CarPowerBase_SNC_Protocol_v01-public.pdf .

    Attributes:
        port:
            Check on your machine on which USB slot you connect the serial device for the 6CPB.
            Find the port by going to bash and typing ls /dev/tty.* for mac (linux, etc).
        self.handsets_on:
                        Which handsets are being used (not important).
        self.handsets_info:
                        Information about the ith handset. information in the array. index 0: brake boolean, 
                        index1: lane_change boolean index2: power int.
        self.response:
                    The response received from 6CPB.
        self.aux_current:
                    Indicates the auxiliary port current (in mA) consumed (not important).
        self.carID:
                The id of the car which passed the SF (start finish) line between the last and current received 
                packet from the 6CPB. If no car passed it, then 000 indicates the game timer. Otherwise, 111
                indicates an invalid id.
        self.received_time:
                        The time we received with the current packet, decoded and converted to a valid int, after 
                        calling self.compute_response_time(). The time only makes sense relative to a starting 
                        point at which the timer started. That starting point is different for every different
                        carID we can receive. More explanation with the attribute self.game_timer and 
                        self.car_times.
        self.crc8/lookup_table:
                            Needed to compute checksum for packets. Refer to manual.
        self.time_increment:
                        Needed to decode the time received from packet. Defined in 
                        protocol documentation for game timer.
        self.last_packet_sent:
                            The last packet we sent. Needed in case we received an invalid packet from 6CPB.
        self.game_time:
                    The time since we started the game. Set when we receive a packet which has as its carID
                    0000 which indicates the game timer, and then setting self.received_time.
        self.car_times:
                    2D array where the first level detrmines the car, e.g. i=0 for car1 etc. and 
                    second level has form [last_lap_time, last_global_time]
                    (global time is the time since when the car passed SF line for the first time). Lap_time
                    is computed by subtracting the previous last_global_time with the current one.
        self.checksum_tries:
                        Counting the number of times we received an invalid packet. 6CPB will resend the
                        packet at most 2 times.
        self.track_power_status:
                        Whether power is properly delivered to the tracks (boolean).
        self.print_update:
                        A boolean which tells wether or not to print the lap updates when they are received. This
                        means printing the current lap time for a car.
    """

    # the lookup table for the crc checksum
    lookup_table = [0x00, 0x07, 0x0e, 0x09, 0x1c, 0x1b, 0x12, 0x15, 0x38, 0x3f, 0x36, 0x31, 0x24, 0x23, 0x2a, 0x2d,
                    0x70, 0x77, 0x7E, 0x79, 0x6C, 0x6B, 0x62, 0x65, 0x48, 0x4F, 0x46, 0x41, 0x54, 0x53, 0x5A, 0x5D,
                    0xE0, 0xE7, 0xEE, 0xE9, 0xFC, 0xFB, 0xF2, 0xF5, 0xD8, 0xDF, 0xD6, 0xD1, 0xC4, 0xC3, 0xCA, 0xCD,
                    0x90, 0x97, 0x9E, 0x99, 0x8C, 0x8B, 0x82, 0x85, 0xA8, 0xAF, 0xA6, 0xA1, 0xB4, 0xB3, 0xBA, 0xBD,
                    0xC7, 0xC0, 0xC9, 0xCE, 0xDB, 0xDC, 0xD5, 0xD2, 0xFF, 0xF8, 0xF1, 0xF6, 0xE3, 0xE4, 0xED, 0xEA,
                    0xB7, 0xB0, 0xB9, 0xBE, 0xAB, 0xAC, 0xA5, 0xA2, 0x8F, 0x88, 0x81, 0x86, 0x93, 0x94, 0x9D, 0x9A,
                    0x27, 0x20, 0x29, 0x2E, 0x3B, 0x3C, 0x35, 0x32, 0x1F, 0x18, 0x11, 0x16, 0x03, 0x04, 0x0D, 0x0A,
                    0x57, 0x50, 0x59, 0x5E, 0x4B, 0x4C, 0x45, 0x42, 0x6F, 0x68, 0x61, 0x66, 0x73, 0x74, 0x7D, 0x7A,
                    0x89, 0x8E, 0x87, 0x80, 0x95, 0x92, 0x9B, 0x9C, 0xB1, 0xB6, 0xBF, 0xB8, 0xAD, 0xAA, 0xA3, 0xA4,
                    0xF9, 0xFE, 0xF7, 0xF0, 0xE5, 0xE2, 0xEB, 0xEC, 0xC1, 0xC6, 0xCF, 0xC8, 0xDD, 0xDA, 0xD3, 0xD4,
                    0x69, 0x6E, 0x67, 0x60, 0x75, 0x72, 0x7B, 0x7C, 0x51, 0x56, 0x5F, 0x58, 0x4D, 0x4A, 0x43, 0x44,
                    0x19, 0x1E, 0x17, 0x10, 0x05, 0x02, 0x0B, 0x0C, 0x21, 0x26, 0x2F, 0x28, 0x3D, 0x3A, 0x33, 0x34,
                    0x4E, 0x49, 0x40, 0x47, 0x52, 0x55, 0x5C, 0x5B, 0x76, 0x71, 0x78, 0x7F, 0x6A, 0x6D, 0x64, 0x63,
                    0x3E, 0x39, 0x30, 0x37, 0x22, 0x25, 0x2C, 0x2B, 0x06, 0x01, 0x08, 0x0F, 0x1A, 0x1D, 0x14, 0x13,
                    0xAE, 0xA9, 0xA0, 0xA7, 0xB2, 0xB5, 0xBC, 0xBB, 0x96, 0x91, 0x98, 0x9F, 0x8A, 0x8D, 0x84, 0x83,
                    0xDE, 0xD9, 0xD0, 0xD7, 0xC2, 0xC5, 0xCC, 0xCB, 0xE6, 0xE1, 0xE8, 0xEF, 0xFA, 0xFD, 0xF4, 0xF3]

    def __init__(self, print_lap_update=False, port='/dev/ttyUSB0'):
        # set the serial. check for which port. In the raspberry put it in the top slot. TODO
        # find the port by going to bash and typing ls /dev/tty.* in mac
        self.ser = serial.Serial(port=port, baudrate=19200)
        self.handsets_on = [0, 0, 0, 0, 0, 0]  # if the connection to the ith handset is established
        self.handsets_info = [[0], [0], [0], [0], [0], [0]]
        self.response = None
        self.aux_current = None
        self.carID = None
        self.received_time = None
        self.crc8 = None
        self.timer_increment = 6.4 / pow(10, 6)  # defined in protocol documentation for game timer
        self.last_packet_sent = None
        self.game_timer = None
        self.car_times = np.zeros((6, 2),
                                  dtype=np.float)  # 2D array where the first level detrmines the car i=0 for car1 etc. and second level has form [last_lap_time, last_global_time] (global time is the time since when the car passed SF line for the first time)
        self.checksum_tries = 0
        self.track_power_status = -1

        self.print_update = print_lap_update

        self.write_packet(reset=True)  # reset and initialize the track.

    def write_packet(self, as_is=None, sucIndicator=True, reset=False, firstCar=0xFF, secondCar=0xFF,
                     thirdCar=0xFF, fourthCar=0xFF, fifthCar=0xFF, sixthCar=0xFF,
                     ledByte=0x00):
        """
        writes 9bytes
        sucIndicator = boolean whether we received previous packet successfully
        start = boolean whether we are starting transmission
        firstCar, secondCar,..., = the byte to send for the given car
        ledByte is the byte to send for the led control
        as_is = is either a packet or None. If it is a packet, then just send it as it is.
                 otherwise send a normal packet.
        reset = Initializes and resets the track to a default state.
        """
        if as_is is None:
            pre_output = []
            if sucIndicator or reset:
                pre_output.append(0xFF)
            else:
                pre_output.append(0x7F)
            cars = [firstCar, secondCar, thirdCar, fourthCar, fifthCar, sixthCar]
            pre_output = pre_output + cars
            if reset:
                pre_output.append(self.led_byte())
            else:
                pre_output.append(ledByte)
            pre_output.append(self.checksum_calc(pre_output))
            self.last_packet_sent = bytearray(pre_output)
        else:
            self.last_packet_sent = as_is
        self.ser.write(self.last_packet_sent)
        self.response = self.ser.read(15)  # manual says that there are 14 bytes. I tried it and there seems to be an
        # an extra byte after the 9th byte.

    def read_packet(self):
        """Reads the packet we received according to the protocol. Sets all relevant attributes in the proccess."""
        # The following part seems to give errors at times, because we are working with 15 bytes instead of 14
        # and the 6CPB seems to be working inconsistently at times.
        if self.response[14] != self.checksum_calc(self.response[:-1]):
            if self.checksum_tries == 2:
                self.checksum_tries = 0
                return
            self.checksum_tries += 1
            self.write_packet(bytearray([0x7F] + list(self.last_packet_sent[1:])))
            self.read_packet()
        self.track_power_status = self.get_bits(self.response[0], 0)  # get the last bit. boolean
        self.aux_current = self.response[7]
        self.handsets_info
        self.handsets_on
        self.carID = self.get_bits(self.response[8], 2, 0)  # 000 is game timer and 111 is invalid ID
        self.received_time = self.compute_response_time()
        self.set_all_times()

    # -----------------------------
    # helper functions

    def car_byte(self, brake=False, laneChange=False, power=0):
        """
        Returns a byte which gives instruction to the car when using write_packet
           brake boolean
           laneChange boolean
           power int [0-63]
        """
        pre_output = 0
        if brake:
            pre_output = 1
        else:
            pre_output = 0
        if laneChange:
            pre_output = (pre_output << 1) | 1
        else:
            pre_output = (pre_output << 1) | 0
        pre_output = (pre_output << 6) | power
        return pre_output ^ 0xFF

    def led_byte(self, greenLed=True, redLed=True, led6=False, led5=False, led4=False, led3=False, led2=False,
                 led1=False):
        """Returns the led_byte to be used in a write_packet. To start a game,
        turn off the red light and turn on the green one."""
        return greenLed << 7 | redLed << 6 | led6 << 5 | led5 << 4 | led4 << 3 | led3 << 2 | led2 << 1 | led1

    def checksum_calc(self, packet):
        """Calculates the checksum for the packet to be sent, as seen in the
            Protocol.
            Input is an array of the packet bytes to be used."""
        self.crc8 = self.lookup_table[packet[0]]
        if len(packet) == 8:
            for i in range(1, 8):
                self.crc8 = self.lookup_table[self.crc8 ^ packet[i]]
        else:
            for i in range(1, 14):
                self.crc8 = self.lookup_table[self.crc8 ^ packet[i]]
        return self.crc8

    def set_all_times(self, print_update=False):
        """Set all the relevant times and computes the lap times for the cars."""
        if self.carID == 0:
            self.game_timer = self.received_time
            return
        # invalid carID. just ignore for now
        if self.carID == 0b111:
            return
        else:
            self.car_times[self.carID - 1] = [self.received_time - self.car_times[self.carID - 1][1],
                                              self.received_time]
            if self.print_update:
                print("Last lap time for car " + str(self.carID) + ": " + str(self.car_times[self.carID - 1][0]))

    def get_lap_time(self, carID):
        """Will return a tuple. The first element is the last lap time and the second is how many seconds ago
         the lap time was updated."""
        return self.car_times[carID][0], self.game_timer - self.car_times[carID][1]

    def compute_response_time(self, bytes_times=None):
        """Computes the real time from the encoded byte time as given by the last response."""
        if bytes_times is None:
            bytes_times = list(self.response)[9:13][::-1]
        temp_time = 0
        for elem in bytes_times:
            temp_time = (temp_time << 8) | elem
        temp_time = temp_time if temp_time != 0xFFFFFFFF else 0
        return temp_time * self.timer_increment


    def get_bits(self, bitstring, start_pos, end_pos=None):
        """Given the bitstring, get the bits starting at start_pos to end_pos.
           The least significant bit has index 0. end_position inclusive. Start_pos > end_pos.
           If no end_pos given, then assume end position is the LSB."""
        if end_pos == None:
            return (bitstring & (1 << start_pos)) >> start_pos
        else:
            mask = (0xFFFF ^ (0xFFFF << (start_pos - end_pos + 1))) & 0xFFFF  # this is ridiculous
            return (bitstring & (mask << end_pos)) >> end_pos

    @property
    def handsets_on(self):
        for i in range(1, 7):
            self._handsets_on[i - 1] = self.get_bits(self.response[0], i)
        return self._handsets_on

    @handsets_on.setter
    def handsets_on(self, value):
        self._handsets_on = value

    @property
    def handsets_info(self):
        for i in range(1, 7):
            self._handsets_info[i - 1] = [self.get_bits(self.response[i], 7),
                                          self.get_bits(self.response[i], 6),
                                          self.get_bits(self.response[i], 5, 0)]
        return self._handsets_info

    @handsets_info.setter
    def handsets_info(self, value):
        self._handsets_info = value



# tests the class
if __name__ == "__main__":
    worker = SlotcarClient()
    do = 0
    worker.ser.flushOutput()
    worker.ser.flushInput()
    if do:
        worker.write_packet(sucIndicator=True, secondCar=worker.car_byte(0, 0, 10),
                            ledByte=worker.led_byte(1, 1, 0, 0, 1, 0, 1, 0))
        print(worker.response[13])
        worker.read_packet()

    if do != 1:

        started = False
        time_last_lap = 0
        while True:
            if not started:
                worker.write_packet(sucIndicator=True, ledByte=worker.led_byte(1, 1, 0, 0, 0, 0, 1, 0))
                worker.write_packet(sucIndicator=True, firstCar=worker.car_byte(0, 0, 12),
                                    secondCar=worker.car_byte(0, 0, 13),
                                    ledByte=worker.led_byte(1, 0, 0, 0, 0, 0, 1, 1))
                started = True

            worker.write_packet(sucIndicator=True, firstCar=worker.car_byte(0, 0, 12),
                                secondCar=worker.car_byte(0, 0, 13), ledByte=worker.led_byte(1, 0, 0, 0, 0, 0, 1, 1))
            worker.read_packet()


