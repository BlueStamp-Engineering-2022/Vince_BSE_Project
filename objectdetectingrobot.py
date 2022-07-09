from os import readlink
import cv2
import numpy as np
import time
import math
import RPi.GPIO as GPIO
from picamera import PiCamera
from picamera.array import PiRGBArray

color_aim = (240, 125, 186)
#videoCapture = cv2.VideoCapture(0)
videoCapture = PiCamera()
videoCapture.resolution = (320, 240)  # 16-32 fps
rawCapture = PiRGBArray(videoCapture)
middle = videoCapture.resolution[0] / 2
previous_radius = None

GPIO.setmode(GPIO.BOARD)

MOTOR1B = 29
MOTOR1E = 31
MOTOR2B = 33
MOTOR2E = 35
BUTTON_PIN = 32

GPIO.setup(MOTOR1B, GPIO.OUT)
GPIO.setup(MOTOR1E, GPIO.OUT)
GPIO.setup(MOTOR2B, GPIO.OUT)
GPIO.setup(MOTOR2E, GPIO.OUT)

# current feeds into BUTTON_PIN when button is pressed
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


def forward():
    GPIO.output(MOTOR1B, GPIO.HIGH)
    GPIO.output(MOTOR1E, GPIO.LOW)
    GPIO.output(MOTOR2B, GPIO.HIGH)
    GPIO.output(MOTOR2E, GPIO.LOW)


def reverse():
    GPIO.output(MOTOR1B, GPIO.LOW)
    GPIO.output(MOTOR1E, GPIO.HIGH)
    GPIO.output(MOTOR2B, GPIO.LOW)
    GPIO.output(MOTOR2E, GPIO.HIGH)


def right_turn():
    GPIO.output(MOTOR1B, GPIO.LOW)
    GPIO.output(MOTOR1E, GPIO.HIGH)
    GPIO.output(MOTOR2B, GPIO.HIGH)
    GPIO.output(MOTOR2E, GPIO.LOW)


def left_turn():
    GPIO.output(MOTOR1B, GPIO.HIGH)
    GPIO.output(MOTOR1E, GPIO.LOW)
    GPIO.output(MOTOR2B, GPIO.LOW)
    GPIO.output(MOTOR2E, GPIO.HIGH)


def stop():
    GPIO.output(MOTOR1E, GPIO.LOW)
    GPIO.output(MOTOR1B, GPIO.LOW)
    GPIO.output(MOTOR2E, GPIO.LOW)
    GPIO.output(MOTOR2B, GPIO.LOW)


def calibrate():
    global radius_aim
    # allow the camera to warmup
    time.sleep(0.1)
    #radius_aim = 300
    # for image in videoCapture.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    # frame = image.array
    # frame = cv2.flip(frame, 1)
    # x, y, w, h = find_blob(segment_colour(frame))
    calibration_frame = np.empty((720, 1280, 3), dtype=np.uint8)
    videoCapture.capture(calibration_frame, 'bgr')
    x, y, w, h = find_blob(segment_colour(calibration_frame))
    radius_aim = (w+h)/4


def segment_colour(frame):  # returns only the pink colors in the frame
    hsv_roi = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask_1 = cv2.inRange(hsv_roi, np.array(
        [160, 100, 10]), np.array([190, 255, 255]))
    # mask_1 = cv2.inRange(hsv_roi, np.array(
    #     [145, 100, 20]), np.array([160, 255, 255]))

    ycr_roi = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    mask_2 = cv2.inRange(ycr_roi, np.array((141., 177., 154.)),
                         np.array((218., 148., 136.)))

    # gray_roi = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # gray_roi = cv2.GaussianBlur(gray_roi, (17, 17), 0)
    # mask_2 = cv2.inRange(gray_roi, 101.873, 206.124)

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
    contours, hierarchy = cv2.findContours(
        blob, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if (area > largest_contour):
            largest_contour = area

            cont_index = i

    r = (0, 0, 2, 2)
    if len(contours) > 0:
        r = cv2.boundingRect(contours[cont_index])

    return r


def color_check(x, y, width, height, color_frame):
    radius = (width+height)/2
    center = (x+radius, y+radius)

    red = green = blue = length = 0

    for w in range(x, x+width, int((x+width)/50+1)+1):
        for h in range(y, y+height, int((y+height)/50)+1):
            if math.sqrt((w-center[0])**2+(h-center[1])**2) <= radius:
                red += color_frame[h][w][0]
                green += color_frame[h][w][1]
                blue += color_frame[h][w][2]
                length += 1

    if length > 0:
        red /= length
        green /= length
        blue /= length

    diff = abs(color_aim[0]-red) + \
        abs(color_aim[1]-green)+abs(color_aim[2]-blue)
    return diff < 200

# look for the ball if it is likely the ball has left fov
# if ball completely leaves fov, will likely constantly trigger
# search because there will be no other proper circles to follow, causing a ton of variability


def search():
    print("searching")
    right_turn()
    start = time.time()
    found = False
    for image in videoCapture.capture_continuous(rawCapture, format="bgr"):
        frame = image.array
        frame = cv2.flip(frame, 1)

        mask_pink = segment_colour(frame)
        x, y, w, h = find_blob(mask_pink)

        if color_check(x, y, w, h, frame):
            found = True
            break
        # change time to make it a 360° rotation
        if time.time()-start >= 2:
            break

    return found


def move_toward(circle_center):
    if abs(circle_center-middle) < middle/4:
        print("straight")
        forward()
    elif circle_center < middle:
        print("left")
        left_turn()
    else:
        print("right")
        right_turn()


if GPIO.input(10) == GPIO.high:
    calibrate()

time.sleep(0.5)  # let button be released

if GPIO.input(10) == GPIO.high:
    for image in videoCapture.capture_continuous(rawCapture, format="bgr"):
        # while (True):
        #ret, frame = videoCapture.read()
        frame = image.array
        frame = cv2.flip(frame, 1)

        mask_pink = segment_colour(frame)

        # circles = cv2.HoughCircles(mask_pink, cv2.HOUGH_GRADIENT, 1.2,
        #                            100, param1=500, param2=200, minRadius=50, maxRadius=500)

        # print(circles)
        #find_blob(frame, mask_pink)
        x, y, w, h = find_blob(mask_pink)
        radius = w/2
        if previous_radius is None:
            previous_radius = radius
        elif previous_radius < radius/2 or previous_radius > radius*2:
            if search() is False:
                print("Couldn't find =(")
                # maybe try to make an algorithm to chase
                break
        elif color_check(x, y, w, h, frame):
            if search() is False:
                print("Couldn't find =(")
                # maybe try to make an algorithm to chase
                break

        displayx = int(x+w)
        displayy = int(y)
        cv2.putText(mask_pink, "Radius: "+str(radius), (displayx, displayy),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (117, 192, 255), 3)
        cv2.circle(mask_pink, (int(x+radius), int(y+radius)),
                   int(radius), (117, 192, 255), 3)

        cv2.imshow('mask', mask_pink)
        # cv2.putText(frame, "Radius: "+str(radius), (displayx, displayy),
        #             cv2.FONT_HERSHEY_SIMPLEX, 1, (245, 132, 243), 3)

        # cv2.imshow('frame', frame)

        move_toward(x+radius)

        previous_radius = radius

        if radius >= radius_aim and abs(x+radius-middle) < 50:
            print("stopped")
            stop()
        rawCapture.truncate(0)

        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break

# videoCapture().release
# cv2.destroyAllWindows()
