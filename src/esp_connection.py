import paho.mqtt.client as paho
import sys as sys
import time
import matplotlib
#have to do this to set backend of matplotlib. otherwise now graph is displayed
#TODO make it a live update

matplotlib.use("TKAgg")
import matplotlib.pyplot as plt

server_ip = "192.168.48.188"

#need to store calibration data
num_g = 2
norm = [0,0,0]
offsets = [0,0,0]
cal = False
upper_bound = 32767
lower_bound = -32768
start = False
stdout = sys.stdout

#store last 100 acceleration values to display in a graph
acc_data = [[], [], []]
time_data = [[], [], []]
plot_counter = 0
graph = None
last_update = 0

fig = None


def on_connect(client, userdata, flags, rc):
	#subscription will always be automatically renewed here. even 
	#by connection failure
	client.subscribe("Test_topic")
	print("Connected to broker and topic")

#the call back for when a PUBLISH message is re   ceived from the server.
def on_message(client, userdata, msg):
	global norm, offsets, cal, start, plot_counter, graph, last_update
	#to have the messgae in the right format. The first item in the split string is the type of message sent. 
	#More info in ESP8266 code
	true_msg = msg.payload.decode().split("/")
	msg_indicator = str(true_msg[0])
	msg_body = (true_msg[1])
	if msg_indicator == "0":
		print(msg_body)
		start = False
	#we are calibrating here since we can not use float on esp
	elif msg_indicator == "2":
		print(msg_body)
		cal = True
		norm = [0,0,0]
		offsets = [0,0,0]
	#ending calibration. Setting all relevent calibration data
	elif msg_indicator== "3":
		cal = False
		for i in range(3):
			if(i == 2):
				offsets[i] = offsets[i]/20 - upper_bound/2
			else:
				offsets[i] = offsets[i]/20
			norm[i] = (upper_bound)/num_g
		sys.stdout.write("\n")
		sys.stdout.flush()
		print(msg_body)	
	#storing the values from calibration. I could combine it with "print correct acceleration" if statement.
	elif cal:
		time_split = msg_body.split(".|")
		split_msg = time_split[0].split(" ")
		direction = ord(split_msg[0]) - ord('X')
		offsets[direction] += int(split_msg[2])
		sys.stdout.write("#")
		sys.stdout.flush()
	#I want to get rid of this. For now it helps me start data transfer
	elif msg_indicator == "4":
		print(msg_body)
		start = True
		
	#print correct acceleration
	elif not cal and start:
		time_split = msg_body.split(".|")
		split_msg = time_split[0].split(" ")
		direction = ord(split_msg[0]) - ord('X')
		new_acc = (int(split_msg[2]) - offsets[direction])/norm[direction]
		acc_data[direction].append(new_acc)
		if len(time_data[direction]) == 0:
			time_data[direction].append(int(time_split[1]))
		else:
			last_time = time_data[direction][len(time_data[direction]) -1]
			time_data[direction].append(int(time_split[1]) + last_time)
		if len(acc_data[0]) == 101 :
			acc_data[direction].pop(0)
			time_data[direction].pop(0)
		#if len(acc_data[0]) == 100 and direction == 0 and (last_update == 0 or time.time() - last_update > 0.5):
			#last_update = time.time()
			#if graph == None:
				##put plt in interactive mode
				#plt.ion()
				#graph = plt.plot(time_data[direction], acc_data[0])[0]
			#graph.set_ydata(acc_data[0])
			#graph.set_xdata(time_data[direction])
			#plt.axis([min(time_data[direction]), max(time_data[direction]), -2, 2])
			#plt.draw()
			#plt.pause(0.01)
		print("time: " + str(time_split[1]))
		print(msg.topic + " " + chr(direction + ord('X')) + ": " + str(new_acc))

 
client = paho.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(server_ip, 1883) 

#fig = plt.figure()
#ax_x = plt.add_subplot(211)
#ax_y = plt.add_subplot(212)


#good loop function since it handles reconnection for us
client.loop_forever()
