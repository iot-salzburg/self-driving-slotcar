import slotcar_control as scc
import esp_connection as esp
import multiprocessing as mp
import time
import numpy as np


class BaseAI:
    """This class should be the parent class of all other algorithms. 
    It provides the standard way of accessing the data and initializing all other classes that are needed.
    Extend this class if you want to extend functionality of the hardware components, so that the algorithm classes
    will not need to be changed. 
    Attributes:
            self.slotcar_client:
                            Field to communicate with the slotcar
            self.carID:
                    The carID of the car we are working with. Needed for slotcar Control.
            self.gravity:
                        The gravity range settings of the MPU.
            self.gyro:
                    The gyro range settings of the MPU.
            self.index_data:
                        A mapping of the names AcX, AcY, AcZ, GyroX, GyroY, GyroZ, Time to the index in the 
                        numpy array self.data on the second level.
            self.data:
                    The sensor data which is received from the ESP client. A 2D array where the second level 
                    stores the actual data in an array for which the index mappings are provided by self.index_data.
                    The higher the index, the newer the data. The time field is the time relative to the last time
                    reset was pressed on the ESP.
            self.__esp_data:
                        A queue from Multiprocessing to get the data from the ESP client.
            self.__init_queue:
                            A queue from Multiprocessing to get all other relevant data from the ESP client
                            to initialize the class.
            self.__esp_client:
                            The esp_client.
            self.norm_const:
                           If we choose to work with raw data, we will get the information of how to scale the
                           data from here. Again, work with self.index_data to know which index to use.
            self.calibration_data:
                           If we choose to work with raw data, we can get the information of how to offset the
                           data from here. Again, work with self.index_data to know which index to use.
            
    """
    def __init__(self, carID=2, raw_data=False):
        self.slotcar_client = scc.SlotcarClient()
        self.carID = carID

        # set in init_from_queue
        self.gravity = -1
        self.gyro = -1
        self.index_data = None

        self.data = None
        self.__esp_data = None
        self.__init_queue = None

        self.initialized = False

        self.__esp_client = None
        self.calibration_data = None
        self.norm_const = None

        self.raw_data = raw_data

    def __get_new_data__(self):
        """Gets all the sensor data that is in the queue from ESP."""
        size = self.__esp_data.qsize()
        # because we have 7 datapoints
        temp = np.empty([size, 7])
        for i in range(size):
            data = self.__esp_data.get()
            temp[i] = data
        if self._data is None or self._data == []:
            self._data = temp
        else:
            self._data = np.append(self._data, temp, axis=0)

    def init_from_queue(self):
        """Initializes all the variables by getting the information from the ESP_Client.
        This is the current order in which the items are put in.
        When called, it will wait until it gets the initialization data.
        If we already initialized, return (could also raise exception)."""
        if self.initialized:
            return
        while self.__init_queue.qsize() < 1:
            time.sleep(0.5)
        to_expect = self.__init_queue.get()
        while self.__init_queue.qsize() != to_expect:
            time.sleep(1)
        if not self.raw_data:
            if to_expect != 3:
                raise Exception("We have not received the right number of init items.")
            self.index_data = self.__init_queue.get()
            self.gravity = self.__init_queue.get()
            self.gyro = self.__init_queue.get()
        elif self.raw_data:
            if to_expect != 5:
                raise Exception("We have not received the right number of init items.")
            self.norm_const = self.__init_queue.get()
            self.index_data = self.__init_queue.get()
            self.calibration_data = self.__init_queue.get()
            self.gravity = self.__init_queue.get()
            self.gyro = self.__init_queue.get()
        self.initialized = True

    def start(self):
        """Starts the communication with the ESP client. Should be called before AI starts in order
        to start the data transfer.
        Also sets all needed attributes."""
        self.__esp_client = esp.EspClient(debugging=False, raw_data = self.raw_data)
        self.__init_queue = mp.Queue()
        self.__esp_data = mp.Queue()
        p = mp.Process(target=self.__esp_client.start_esp, args=(self.__esp_data, self.__init_queue,))
        p.start()
        self.init_from_queue()

    @property
    def data(self):
        """I am the data property. Store all sensor data received from esp.
        Each time you access me, I will update myself to all the new data received from the esp_client."""
        self.__get_new_data__()
        return self._data

    @data.setter
    def data(self, value):
        self._data = value



