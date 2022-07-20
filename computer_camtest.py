from os import readlink
import cv2
import numpy as np
import time
import math

color_aim = (240, 125, 186)
videoCapture = cv2.VideoCapture(0)
videoCapture.set(3, 640)
videoCapture.set(4, 360)
middle = videoCapture.get(3) / 2
previous_radius = None

# searchindex = 0


def calibrate():
    global radius_aim
    radius_aim = 300


def segment_colour(frame):  # returns only the red colors in the frame
    hsv_roi = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask_1 = cv2.inRange(hsv_roi, np.array(
        [160, 100, 10]), np.array([190, 255, 255]))
    # mask_1 = cv2.inRange(hsv_roi, np.array(
    #     [145, 100, 20]), np.array([160, 255, 255]))

    ycr_roi = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    mask_2 = cv2.inRange(
        ycr_roi, np.array((141.0, 177.0, 154.0)), np.array(
            (218.0, 148.0, 136.0))
    )

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
        blob, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area > largest_contour:
            largest_contour = area

            cont_index = i

    r = (0, 0, 2, 2)
    if len(contours) > 0:
        r = cv2.boundingRect(contours[cont_index])

    return r

    # lowest_diff = None

    # for i, contour in enumerate(contours):
    #     x, y, width, height = cv2.boundingRect(contour)
    #     radius = (width+height)/2
    #     center = (x+radius, y+radius)

    #     # pixel_colors=[]
    #     red = green = blue = length = 0

    #     for w in range(x, x+width, int((x+width)/50+1)+1):
    #         for h in range(y, y+height, int((y+height)/50)+1):
    #             if math.sqrt((w-center[0])**2+(h-center[1])**2) <= radius:
    #                 # rgb = [color_frame[h, w, 0],
    #                 #        color_frame[h, w, 1], color_frame[h, w, 2]]
    #                 red += color_frame[h][w][0]
    #                 green += color_frame[h][w][1]
    #                 blue += color_frame[h][w][2]
    #                 length += 1

    #                 # pixel_colors.append(rgb)

    #     if length > 0:
    #         red /= length
    #         green /= length
    #         blue /= length

    #     diff = abs(color_aim[0]-red) + \
    #         abs(color_aim[1]-green)+abs(color_aim[2]-blue)

    #     #print(diff, "\n")
    #     if lowest_diff is None:
    #         lowest_diff = diff
    #         cont_index = i
    #         #print("None", red, green, blue, "\n", sep="\n")

    #     elif diff < lowest_diff:
    #         lowest_diff = diff
    #         cont_index = i

    #         #print("Lowest Diff", red, green, blue, "\n", sep="\n")

    # #print(cont_index, len(contours), sep="\n")
    # best_fit_rect = (0, 0, 0, 0)
    # if len(contours) > 0:
    #     best_fit_rect = cv2.boundingRect(contours[cont_index])
    # return best_fit_rect


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
    print("searching")
    # searchindex += 1


def move_toward(circle_center):
    if abs(circle_center - middle) < 50:
        print("straight")
    elif circle_center < middle:
        print("left")
        # moveleft
    else:
        print("right")


calibrate()

while True:
    ret, frame = videoCapture.read()
    frame = cv2.flip(frame, 1)

    mask_pink = segment_colour(frame)

    # circles = cv2.HoughCircles(mask_pink, cv2.HOUGH_GRADIENT, 1.2,
    #                            100, param1=500, param2=200, minRadius=50, maxRadius=500)

    # print(circles)
    # find_blob(frame, mask_pink)
    x, y, w, h = find_blob(mask_pink)
    #print(x, y, w, h, sep="\n")
    radius = w / 2
    if previous_radius is None:
        previous_radius = radius
    elif previous_radius < radius / 2 or previous_radius > radius * 2:
        search()
    elif color_check(x, y, w, h, frame):
        search()

    displayx = int(x + w)
    displayy = int(y)
    cv2.putText(
        mask_pink,
        "Radius: " + str(radius),
        (displayx, displayy),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (117, 192, 255),
        3,
    )
    cv2.circle(
        mask_pink, (int(x + radius), int(y + radius)
                    ), int(radius), (117, 192, 255), 3
    )

    cv2.imshow("mask", mask_pink)
    # cv2.putText(frame, "Radius: "+str(radius), (displayx, displayy),
    #             cv2.FONT_HERSHEY_SIMPLEX, 1, (245, 132, 243), 3)

    # cv2.imshow('frame', frame)

    move_toward(x + radius)

    if radius >= radius_aim and abs(x + radius - middle) < 50:
        print("stopped")

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# videoCapture().release
cv2.destroyAllWindows()
