
import RPi.GPIO as GPIO
import time

GPIO.setwarnings(False)

MOTOR1B = 31 #IN1
MOTOR1E = 33 #IN2
MOTOR2B = 35 #IN3
MOTOR2E = 37 #IN4

GPIO.setmode(GPIO.BOARD)

GPIO.setup(MOTOR1B, GPIO.OUT)
GPIO.setup(MOTOR1E, GPIO.OUT)
GPIO.setup(MOTOR2B, GPIO.OUT)
GPIO.setup(MOTOR2E, GPIO.OUT)


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


print("forward")
forward()
time.sleep(8)
print("reverse")
reverse()
time.sleep(8)
print("left")
left_turn()
time.sleep(8)
print("right")
right_turn()
time.sleep(8)
stop()
