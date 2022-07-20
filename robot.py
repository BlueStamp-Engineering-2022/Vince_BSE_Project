import cv2
import numpy as np
import time
import math
import RPi.GPIO as GPIO
from picamera import PiCamera
from picamera.array import PiRGBArray

GPIO.setwarnings(False)

#color_aim = (130, 75, 110)
video_capture = PiCamera()
#video_capture.rotation=180
video_width = 640
video_height = 480
video_capture.resolution = (video_width, video_height)  # 40 fps
#video_capture.framerate = 16
raw_capture = PiRGBArray(video_capture, size=(video_width, video_height))
middle = 320
previous_radius = None
left = True


GPIO.setmode(GPIO.BOARD)

MOTOR1B = 31  
MOTOR1E = 33
MOTOR2B = 35 
MOTOR2E = 37
BUTTON_PIN = 22

GPIO.setup(MOTOR1B, GPIO.OUT)
GPIO.setup(MOTOR1E, GPIO.OUT)
GPIO.setup(MOTOR2B, GPIO.OUT)
GPIO.setup(MOTOR2E, GPIO.OUT)

# current feeds into BUTTON_PIN when button is pressed
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


def left_turn():
    GPIO.output(MOTOR1B, GPIO.HIGH)
    GPIO.output(MOTOR1E, GPIO.LOW)
    GPIO.output(MOTOR2B, GPIO.HIGH)
    GPIO.output(MOTOR2E, GPIO.LOW)


def right_turn():
    GPIO.output(MOTOR1B, GPIO.LOW)
    GPIO.output(MOTOR1E, GPIO.HIGH)
    GPIO.output(MOTOR2B, GPIO.LOW)
    GPIO.output(MOTOR2E, GPIO.HIGH)


def reverse():
    GPIO.output(MOTOR1B, GPIO.LOW)
    GPIO.output(MOTOR1E, GPIO.HIGH)
    GPIO.output(MOTOR2B, GPIO.HIGH)
    GPIO.output(MOTOR2E, GPIO.LOW)


def forward():
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
    allowed_color_diff = 50
    # print("abvals", abs(
    #     color_aim[0]-red), abs(color_aim[1]-green), abs(color_aim[2]-blue), sep="\n")
    return abs(color_aim[0]-red) < allowed_color_diff and abs(color_aim[1]-green) < allowed_color_diff and abs(color_aim[2]-blue) < allowed_color_diff

# look for the ball if it is likely the ball has left fov
# if ball completely leaves fov, will likely constantly trigger
# search because there will be no other proper circles to follow, causing a ton of variability


def search():
    print("searching")
    start = time.time()
    found = False
    search_raw_capture = PiRGBArray(
        video_capture, size=(video_width, video_height))
    time.sleep(0.01)
    x_blob = None
    y_blob = None
    w_blob = None
    h_blob = None
    
    for image in video_capture.capture_continuous(search_raw_capture, format="rgb"):
        if left:
            left_turn()
        else:
            right_turn()
        time.sleep(0.04)
        stop()
        
        frame = image.array
        frame = cv2.flip(frame, 1)
        
        mask_pink = segment_colour(frame)
        cv2.imshow("mask", mask_pink)
        x_blob, y_blob, w_blob, h_blob = find_blob(mask_pink)

        search_raw_capture.truncate(0)

        if color_check(x_blob, y_blob, w_blob, h_blob, frame):
            found = True
            break

        # change time to make it a 360° rotation
        if time.time()-start >= 8:
            break
        if GPIO.input(BUTTON_PIN) == 1:
            break

    return x_blob, y_blob, w_blob, h_blob, found


def move_toward(circle_center, radius):
    if abs(circle_center-middle) < middle/3:
        print("straight")

        #doesn't stop until up way closer
        if radius >= radius_aim-150:
            print("stopped")
            stop()
            return
    
        forward()
        time.sleep(0.01)
        #stop()
        
    elif circle_center < middle:
        print("left")
        left = True
        left_raw_capture = PiRGBArray(
            video_capture, size=(video_width, video_height))
        for image in video_capture.capture_continuous(left_raw_capture, format="rgb"):
            left_turn()
            time.sleep(0.04)
            stop()
            frame = image.array
            frame = cv2.flip(frame, 1)
            
            mask_pink = segment_colour(frame)
    
            x, y, w, h = find_blob(mask_pink)
            radius = (w+h)/4
            
            if abs(x+radius-middle) < middle/3:
                stop()
                break
            
            left_raw_capture.truncate(0)
            if GPIO.input(BUTTON_PIN) == 1:
                break
        #stop()
    else:
        print("right")
        left = False
        right_raw_capture = PiRGBArray(
            video_capture, size=(video_width, video_height))
        for image in video_capture.capture_continuous(right_raw_capture, format="rgb"):
            right_turn()
            time.sleep(0.04)
            stop()
            frame = image.array
            frame = cv2.flip(frame, 1)
            
            mask_pink = segment_colour(frame)
    
            x, y, w, h = find_blob(mask_pink)
            radius = (w+h)/4
            
            if abs(x+radius-middle) < middle/3:
                stop()
                break
            
            right_raw_capture.truncate(0)
            if GPIO.input(BUTTON_PIN) == 1:
                break
        #stop()


stop()

while GPIO.input(BUTTON_PIN) == 0:
    pass

print("button read")

calibrate()
print(radius_aim)

time.sleep(0.5)  # let button be released

while GPIO.input(BUTTON_PIN) == 0:
    pass
print("button read second")
time.sleep(0.5)

for image in video_capture.capture_continuous(raw_capture, format="rgb"):
    stop()
    time.sleep(0.01)
    
    frame = image.array
    frame = cv2.flip(frame, 1)

    mask_pink = segment_colour(frame)
    
    cv2.imshow("mask", mask_pink)
    
    x, y, w, h = find_blob(mask_pink)
    radius = (w+h)/4
    print(radius, x, y, sep="\n")

    if previous_radius is None:
        previous_radius = radius
    elif previous_radius < radius/2 or previous_radius > radius*2:
        print("radius_check")
        x_blob, y_blob, w_blob, h_blob, found=search()
        if found:
            radius=(w_blob + h_blob)/4
            x=x_blob
            y=y_blob
        else:
            print("Couldn't find =(")
            # maybe try to make an algorithm to chase
            break
    elif color_check(x, y, w, h, frame) is False:
        print("color_check")
        x_blob, y_blob, w_blob, h_blob, found=search()
        if found:
            radius=(w_blob + h_blob)/4
            x=x_blob
            y=y_blob
        else:
            print("Couldn't find =(")
            # maybe try to make an algorithm to chase
            break

    move_toward(x+radius, radius)
    print("center", x+radius, sep=" ")

    previous_radius = radius
    
    raw_capture.truncate(0)

    if GPIO.input(BUTTON_PIN) == 1:
        raw_capture.truncate(0)
        break

    if cv2.waitKey(1) & 0xFF == ord('q'):
        raw_capture.truncate(0)
        break
    
stop()
GPIO.cleanup()
#cv2.destroyAllWindows()
