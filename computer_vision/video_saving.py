import cv2
import numpy as np
import slotcar_control as sc
import os
import time

video_location = '../'
video_file_name = 'output.m4v'

# turn off to get higher frame rate
should_display = False

# if you set it to 0 then it will go indefinitely.
num_seconds = 10

frame_rate = 10

should_drive = True

# find the port by going to bash and typing ls /dev/tty.* in mac
slot = sc.SlotcarClient(port="/dev/tty.usbserial-AI05FT0P")
speed = 12  # this is usually a fine speed to go with.

print("Getting VideoCapture.")
cap = cv2.VideoCapture(0)

try:
    os.remove(video_location + video_file_name)
    print("Removed: " + video_file_name)
except:
    print(video_file_name + " does not exist in given location yet.")

size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
# got the codec  from https://gist.github.com/takuma7/44f9ecb028ff00e2132e
fourcc = cv2.VideoWriter_fourcc(*'avc1')
out = cv2.VideoWriter(video_location + video_file_name, fourcc, frame_rate, size)
print("Created: " + video_file_name)

print("Setting car in motion.")
wait_seconds = 1000 / frame_rate * pow(10, -3)
if should_drive:
    slot.write_packet(secondCar=slot.car_byte(brake=False, laneChange=False, power=speed),
                      ledByte=slot.led_byte(1, 0, 0, 0, 0, 0, 1, 0))
print("Starting to record.")
start_time = time.time()
last_time = start_time
while cap.isOpened() and (num_seconds > (time.time() - start_time) or num_seconds == -1):
    last_time += wait_seconds
    if last_time < time.time():
        raise Exception("The frame rate is too high.")
    time.sleep(last_time - time.time())
    ret, frame = cap.read()
    if ret:
        out.write(frame)
    else:
        print("Did not receive an image.")
        break
    if should_display:
        cv2.imshow("frame", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break


print("Ending.")

slot.write_packet(reset=True)
cap.release()
out.release()
cv2.destroyAllWindows()
