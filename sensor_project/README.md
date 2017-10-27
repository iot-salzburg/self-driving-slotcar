Code base for the sensors and the corresponding algorithms.

Introduction:
=============
This directory contains the relevant files to work with the movement sensors data.
The code is intended to be run from the provided Raspberry pi, or at least from a computer which is connected to the
sensornet.


The current setup has a communication loop as follows:
======================================================
• On the slotcar we have mounted a 3D printed case which hosts the sensors needed. (./Hardware/CarCover.stl).

• Acceleration and Gyroscope data are provided by the MPU6050
and are transmitted through the ESP-8266-01 with MQTT over the sensornet. (./Hardware/Sensors/esp_mpu_circuit.fzz)
A provided RaspberryPi serves as the host for MQTT. The current topic used is "Test_topic", which can be
changed at any time.

• The RaspberryPi or a computer which is able to set the Raspberry pi as a host,
then receives the data from the ESP. The data is analyzed through a algorithm and then commands are given
to the slotcar through the Scalextric 6CarPowerBase (6CPB).


How to write a custom algorithm:
================================
To write a custom algorithm first view the simple_ai_algorithm.py script as it outlines how to interact with the code.
Generally you will need to inherit from the AI_Base.py script. It will handles all the data polling necessary. Also,
you will be able to communicate with the slotcar through the AI_Base script as
given in the simple_ai_algorithm.py script.


Tips and Common bugs for running scripts:
=========================================
The bugs which are well known are hardware specific (could possibly be prevented by having better software; just don't
know how).
• The most common bug is with the 6CPB. To have everything run smoothly, power off the 6CPB and unplug all other
cables besides the modem cable. Then turn it back on and proceed with the algorithm.
    - We also have issues with how many bytes we receive from the 6CPB. The protocol states that only 14 bytes should be
    expected as a response, but the communication loop only works with 15. So if there are issues with the 6CPB.
    Always unplug everything to clean the pipes.

• When communication doesn't seem to work with the ESP, check if you are connected to sensornet.

Directory Structure:
====================

• The doc folder should have any additional documentation besides this one. To reach the code documenation go to /doc/PythonDocumentation/Sphinx/_build/html/code.html

• The scripts in the current directory are the ones used to handle the running of the algorithms.

• In the not_used directory you can find script which partially implement some functionalities but were not used in the
final implementation.
    - Analyzing acceleration was meant to compute the velocity and position of the slotcar by taking Riemann Sums over
    acceleration. Since the esp is too inaccurate that was not possible.
    - Data_Manipulation and data_playground have the same purpose. To provide a place where general data manipluation
    functions can be written. Could be extended in the future.
    -store_data can be used to store some laps worth of data and then retrieve that data at a later time.
    Useful to work with data offline.

• The ESP_Code directory has the code from the esp.


Notes:
======
• We are using two cores for this implementation. One is used to receive the data from the ESP through mqtt while
the other core handles the algorithm.

• You can change the MPU settings, i.e. you can change up to how high/low you want to measure your g values for
acceleration or the scale of the gyroscope measurements. Check
 https://www.invensense.com/wp-content/uploads/2015/02/MPU-6000-Register-Map1.pdf for more info (registers 27 and 28
 for example).

Challenges/Improvements:
========================
Problem
-------
• The greatest challenge was the data inaccuracy. Even with a moving average the data is very noise and hard to
work with. With the given data it was hard to know where on the track the car is located and hence it would be difficult
to implement a good reinforcement algorithm which would learn how to drive the slotcar.
The reason the slotcar data is so noise is because the car itself shakes lightly when it is driving. It is a high
frequency noise which can and has lead to unwanted inaccuracies.

Potential Solution
------------------
• A solution is to use a camera setup which will detect the car and see where it is located. Johannes and I have started
to work on this project and the progress can be found in gym-slotcar and computer_vision.
• Another solution would be to have a mechanical filter which would cancel out the high frequency noise.

Problem
-------
• Data transfer was too slow and we only achieved a data transfer of 20Hz.

Solution
--------
• Have multiple cores where we have been able to greatly increase the frequency. It oftentimes surpasses 100Hz.

Problem
-------
• The Hardware construction poses a problem. The wires which are soldered on the PCB fall off very often and
someone has to solder them back on.
• Have a printed PCB or other wires.

Problem:
--------
• Sometimes there is a drop of data from the ESP side. e.g., for a second we would not receive any data.
This might be an issue with the ESP as I have implemented some queues which should store all the data the ESP
can poll from the MPU and send them as soon it is reconnected.

Potential Solution:
-------------------
• Check the code again and make sure the queue does what it is supposed to do. Other than that you would have to look
again into the datasheet of the ESP.


6 Car Power Base:
=================
The protocol for reference: http://ssdc.jackaments.com/saved/C7042_6CarPowerBase_SNC_Protocol_v01-public.pdf

Note that we are using RS-485 to communicate with the 6CPB. We have a setup which involves a modem cable and a
USB cable which handles the conversion from USB to RS-485 for us. We simply have to treat the messages as serial
messages then. On the USB converter, make sure to have all the switches on off (closest to the USB outlet). Also,
make sure the cables are connected the right way. This can be checked by looking at the protocol and seeing which
cables are GND, +(A), -(B) and connect those correspondingly (you should be able to see the labels drawn on
the USB right by the green connection, in the middle there should be A, up B and down GND, where
you have to hold the USB connection in your left hand, the green connection should be to your right
and have everything facing upwards).


ESP:
====
All relevant settings for the ESP can be found in its code. It simply connects to the sensornet, polls the
data from the MPU6050 and publishes them to the host (raspberry pi) and to the topic 'Test_Topic'.
To control the ESP check out the Hardware drawing (./Hardware/Sensors/esp_mpu_circuit.fzz) to see how to use
the hardware and check out the code which specifies
what was done and which sources were used. Generally use the Arduino IDE to get all relevant dependencies and treat the
ESP as a arduino object with start and update loop.

