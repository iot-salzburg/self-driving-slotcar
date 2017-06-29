import sys as sys
import time
import matplotlib
#have to do this to set backend of matplotlib. otherwise now graph is displayed
matplotlib.use("TKAgg")
import matplotlib.pyplot as plt
import numpy as np
import json

#for now, to get the data we should first call esp_connection. press reset when we want to 
#stop the data transfer and save the data. then we can run this script.

#Note. once we get forward_velocity, for the velocity at index i we have time[i]/2 driven before and after.

#for now it handles given data. no live updating feature. needs to be implemented

class analyzing_acceleration():
	
	def __init__(self): 
		with open("mylist.txt") as f: #in read mode, not in write mode, careful. 'r' is assumed
			data=json.load(f)
		self.data = np.array(data)
		self.thetas = None #in radians
		self.velocity_forward = None
		self.delta_forward_distance = None
		self.y_displacement = None
		self.x_displacement = None
		self.set_position()
		
	#
	def process_data(self):
		
	#provides a list of horizontal velocity data. Assuming that we had never turned.
	#will be used by other algorithms. 
	#use time as the time from the last data point to the current. so we could use a left handed rieman sum. 
	#due to noise i will choose the midpoint one though and weigh by the
	#time with the same index as the later data point.
	#forward direction is given by y axis from accelerometer
	def set_velocity_data(self):
		forward_dir = 1
		a_acc = self.data[forward_dir + 1]
		b_acc = np.append([0], a_acc[:-1])
		self.combined_acc = (a_acc + b_acc)/2 #getting averages. might be dangerous to get combined acc here
		self.velocity_forward = np.cumsum(self.combined_acc*self.data[0])
		
	def set_delta_forward_ditance(self):
		if self.velocity_forward == None:
			self.set_velocity_data()
		self.delta_forward_distance = velocity_forward*self.data[0]
	
	#calculates teh angle of the car from it's initial forward direction.
	#using formula theta*r = l (arc)
	def set_direction_angles(self):
		if self.velocity_foward == None:
			self.set_velocity_data()
		if self.delta_forward_distance == None:
			self.set_delta_forward_distance()
		radii = velocity_forward**2/self.combined_acc
		self.thetas = delta_forward_distance/radii
		
	#calculates the y and x displacement
	def set_position(self):
		if self.velocity_foward == None:
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
		self.graph = plt.plot(self.x_displacement, self.y_displacement)[0]
		plt.show()

		
		


analyze_acc = analyzing_acceleration()
analyze_acc.plot_data()
