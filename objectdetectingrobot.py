import cv2
import numpy as np
import time
import math
import RPi.GPIO as GPIO
from picamera import PiCamera
from picamera.array import PiRGBArray

GPIO.setwarnings(False)

#color_aim = (120, 75, 110)
video_capture = PiCamera()
video_width = 640
video_height = 480
video_capture.resolution = (video_width, video_height)  # 16-32 fps
raw_capture = PiRGBArray(video_capture, size=(video_width, video_height))
middle = video_capture.resolution[0] / 2
previous_radius = None

GPIO.setmode(GPIO.BOARD)

MOTOR1B = 31  # IN2
MOTOR1E = 29  # IN1
MOTOR2B = 35  # IN4
MOTOR2E = 33  # IN3
BUTTON_PIN = 22

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


def left_turn():
    GPIO.output(MOTOR1B, GPIO.LOW)
    GPIO.output(MOTOR1E, GPIO.HIGH)
    GPIO.output(MOTOR2B, GPIO.HIGH)
    GPIO.output(MOTOR2E, GPIO.LOW)


def right_turn():
    GPIO.output(MOTOR1B, GPIO.HIGH)
    GPIO.output(MOTOR1E, GPIO.LOW)
    GPIO.output(MOTOR2B, GPIO.LOW)
    GPIO.output(MOTOR2E, GPIO.HIGH)


def stop():
    GPIO.output(MOTOR1E, GPIO.LOW)
    GPIO.output(MOTOR1B, GPIO.LOW)
    GPIO.output(MOTOR2E, GPIO.LOW)
    GPIO.output(MOTOR2B, GPIO.LOW)


def color_process(x, y, width, height, color_frame):
    radius = (width+height)/2
    center = (x+radius, y+radius)

    red = green = blue = length = 0

    for w in range(x, x+width, 10):
        for h in range(y, y+height, 10):
            if math.sqrt((w-center[0])**2+(h-center[1])**2) <= radius:
                red += color_frame[h][w][0]
                green += color_frame[h][w][1]
                blue += color_frame[h][w][2]
                length += 1

    if length > 0:
        red /= length
        green /= length
        blue /= length

    return (red, green, blue)


def calibrate():
    global radius_aim
    global color_aim
    # allow the camera to warmup
    time.sleep(0.01)
    calibration_frame = np.empty(
        (video_height, video_width, 3), dtype=np.uint8)
    video_capture.capture(calibration_frame, 'rgb')
    x, y, w, h = find_blob(segment_colour(calibration_frame))
    # r, g, b = color_check(x, y, w, h, calibration_frame)
    # color_aim=(r, g, b)
    color_aim = color_process(x, y, w, h, calibration_frame)
    print(color_aim)
    radius_aim = (w+h)/4


def segment_colour(frame):  # returns only the pink colors in the frame
    hsv_roi = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    mask_1 = cv2.inRange(hsv_roi, np.array(
        [160, 100, 10]), np.array([190, 255, 255]))

    ycr_roi = cv2.cvtColor(frame, cv2.COLOR_RGB2YCrCb)
    mask_2 = cv2.inRange(ycr_roi, np.array((141., 177., 154.)),
                         np.array((218., 148., 136.)))

    mask = mask_1 | mask_2
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

    for w in range(x, x+width, 10):
        for h in range(y, y+height, 10):
            if math.sqrt((w-center[0])**2+(h-center[1])**2) <= radius:
                red += color_frame[h][w][0]
                green += color_frame[h][w][1]
                blue += color_frame[h][w][2]
                length += 1

    if length > 0:
        red /= length
        green /= length
        blue /= length

    #print(red, green, blue, sep="\n")

    # diff = abs(color_aim[0]-red) + \
    #     abs(color_aim[1]-green)+abs(color_aim[2]-blue)
    # return diff < 150
    allowed_color_diff = 60
    # print("abvals", abs(
    #     color_aim[0]-red), abs(color_aim[1]-green), abs(color_aim[2]-blue), sep="\n")
    return abs(color_aim[0]-red) < allowed_color_diff and abs(color_aim[1]-green) < allowed_color_diff and abs(color_aim[2]-blue) < allowed_color_diff

# look for the ball if it is likely the ball has left fov
# if ball completely leaves fov, will likely constantly trigger
# search because there will be no other proper circles to follow, causing a ton of variability


def search():
    print("searching")
    right_turn()
    start = time.time()
    found = False
    search_raw_capture = PiRGBArray(video_capture, size=(320, 240))
    for image in video_capture.capture_continuous(search_raw_capture, format="rgb"):
        frame = image.array
        frame = cv2.flip(frame, 1)

        mask_pink = segment_colour(frame)
        x, y, w, h = find_blob(mask_pink)

        search_raw_capture.truncate(0)

        if color_check(x, y, w, h, frame):
            found = True
            break

        # change time to make it a 360° rotation
        if time.time()-start >= 5:
            break
        if GPIO.input(BUTTON_PIN) == 1:
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


stop()

while GPIO.input(BUTTON_PIN) == 0:
    pass

print("button read")
# time.sleep(1)

calibrate()
print(radius_aim)

time.sleep(0.5)  # let button be released

while GPIO.input(BUTTON_PIN) == 0:
    pass
print("button read second")
time.sleep(0.5)

for image in video_capture.capture_continuous(raw_capture, format="rgb"):
    start = time.time()
    frame = image.array
    frame = cv2.flip(frame, 1)

    mask_pink = segment_colour(frame)
    x, y, w, h = find_blob(mask_pink)
    radius = w/2

    if previous_radius is None:
        previous_radius = radius
    elif previous_radius < radius/2 or previous_radius > radius*2:
        # print("radius_check")
        if search() is False:
            print("Couldn't find =(")
            # maybe try to make an algorithm to chase
            break
    elif color_check(x, y, w, h, frame) is False:
        # print("color_check")
        if search() is False:
            print("Couldn't find =(")
            # maybe try to make an algorithm to chase
            break

    move_toward(x+radius)

    previous_radius = radius

    if radius >= radius_aim and abs(x+radius-middle) < 50:
        print("stopped")
        stop()
    raw_capture.truncate(0)

    print(time.time()-start)

    if GPIO.input(BUTTON_PIN) == 1:
        break

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

stop()
GPIO.cleanup()
