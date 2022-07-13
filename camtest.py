import RPi.GPIO as GPIO
from picamera import PiCamera
from picamera.array import PiRGBArray
import cv2
import numpy as np
import time
import math

color_aim = (240, 125, 186)
video_capture = PiCamera()
video_capture.resolution = (320, 240)  # 60fps
# video_capture.framerate = 60 #ends up being 5-7 fps at 720p
#raw_capture = PiRGBArray(video_capture, size=(1280, 720))
raw_capture = PiRGBArray(video_capture)
middle = video_capture.resolution[0] / 2
print(video_capture.framerate, sep="\n")
#print("middle", middle, sep="\n")
previous_radius = None


def calibrate():
    global radius_aim
    radius_aim = 250


def segment_colour(frame):  # returns only the red colors in the frame
    hsv_roi = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask_1 = cv2.inRange(hsv_roi, np.array(
        [160, 100, 10]), np.array([190, 255, 255]))

    ycr_roi = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    mask_2 = cv2.inRange(
        ycr_roi, np.array((141.0, 177.0, 154.0)), np.array(
            (218.0, 148.0, 136.0))
    )

    mask = mask_1 | mask_2
    # mask = mask_1
    kern_dilate = np.ones((8, 8), np.uint8)
    kern_erode = np.ones((3, 3), np.uint8)
    mask = cv2.erode(mask, kern_erode)  # Eroding
    mask = cv2.dilate(mask, kern_dilate)  # Dilating
    # cv2.imshow('mask',mask)
    return mask


def find_blob(blob):  # returns the pink colored circle
    largest_contour = 0
    cont_index = 0
    _, contours, _ = cv2.findContours(
        blob, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )

    # contours, hierarchy = cv2.findContours(
    #     blob, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    # )
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area > largest_contour:
            largest_contour = area

            cont_index = i

    r = (0, 0, 2, 2)
    if len(contours) > 0:
        r = cv2.boundingRect(contours[cont_index])

    return r


def color_check(x, y, width, height, color_frame):
    radius = (width + height) / 2
    center = (x + radius, y + radius)

    red = green = blue = length = 0

    for w in range(x, x + width, int((x + width) / 50 + 1) + 1):
        for h in range(y, y + height, int((y + height) / 50) + 1):
            if math.sqrt((w - center[0]) ** 2 + (h - center[1]) ** 2) <= radius:
                red += color_frame[h][w][0]
                green += color_frame[h][w][1]
                blue += color_frame[h][w][2]
                length += 1

    if length > 0:
        red /= length
        green /= length
        blue /= length

    diff = (
        abs(color_aim[0] - red) + abs(color_aim[1] - green) +
        abs(color_aim[2] - blue)
    )
    return diff < 200


# look for the ball if it is likely the ball has left fov
# if ball completely leaves fov, will likely constantly trigger
# search because there will be no other proper circles to follow, causing a ton of variability


def search():
    print("searching", "\n", "\n")
    # searchindex += 1


def move_toward(circle_center):
    if abs(circle_center - middle) < middle/4:
        print("straight")
    elif circle_center < middle:
        print("left")
        # moveleft
    else:
        print("right")


calibrate()

for image in video_capture.capture_continuous(raw_capture, format="bgr"):
    start = time.time()
    frame = image.array
    #frame = cv2.flip(frame, 1)

    mask_pink = segment_colour(frame)

    x, y, w, h = find_blob(mask_pink)
    #print(x, y, w, h, sep="\n")
    radius = w / 2
    if previous_radius is None:
        previous_radius = radius
    elif previous_radius < radius / 3 or previous_radius > radius * 3:
        search()
        print("radius")
    elif color_check(x, y, w, h, frame):
        search()
        print("color")

    move_toward(x + radius)

    previous_radius = radius

    if radius >= radius_aim and abs(x + radius - middle) < 50:
        print("stopped")
    raw_capture.truncate(0)
    print(time.time()-start, "\n")
