import cv2
import numpy as np
import slotcar_control as sc
import os
import time


name='output.m4v'
path='../'



cap = cv2.VideoCapture(path + name)

# use the background subtractors. values were chosen such that we have a clearer detection of the moving car.
fgbg = cv2.createBackgroundSubtractorMOG2(history=20, varThreshold = 100, detectShadows=False)

print("Video processing should start now.")
last_frame = None
while cap.isOpened():
    ret, frame = cap.read()
    if ret:
        # frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        fgmask = fgbg.apply(frame)
        # if last_frame is None:
        #     print("Set last_frame.")
        #     last_frame = frame
        # else:
        # new_frame = cv2.subtract(last_frame, frame)
        # last_frame = frame
        cv2.imshow('frame', fgmask)
        if cv2.waitKey(1) & 0xFF == 'q':
            break

    else:
        print("No more images found in video.")
        break

cap.release()
cv2.destroyAllWindows()
