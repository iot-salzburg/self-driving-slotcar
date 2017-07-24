# self-driving-slotcar
Code base for the self-driving slotcar project.

Introduction:
This project is intended to be the base for algorithms which will control slotcars which work with the 6CPB from Scalextric.

The current setup has a communication loop as follows:

On the slotcar we have mounted a 3D printed case which hosts the sensors needed (TODO Provide Link to 3D file).
Acceleration and Gyroscope data are provided by the MPU6050
 and are transmitted through the ESP-8266-01 with MQTT. (TODO Provide link to hardware setup)
A provided RaspberryPi serves as the host for MQTT. The current topic used is "Test_topic", which can be
changed at any time.
The RaspberryPi then receives the data from the ESP. The scripts are created in such a way that one can
create an arbitrary algorithm and get the data easily from the script currently provided. Hence, on the
Raspberry Pi the data is received and evaluated.
After the data is processed, we start sending a commands to the 6CPB through the protocol they provide.
We received messages from the 6CPB, from which we can extract the lap times.

How to use:
For normal operation.

• Connect the battery to the hardware setup on the slotcar. The ESP should automatically
    setup a connection and transmit data.
  TODO maybe more specific











The ESP-8266-01 is programmed to connect to the sensornet and poll data from the MPU-6050 as