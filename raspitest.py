import RPi.GPIO as GPIO
import time

MOTOR1B = 29
MOTOR1E = 31
GPIO.setmode(GPIO.BOARD)

GPIO.setup(MOTOR1B, GPIO.OUT)
GPIO.setup(MOTOR1E, GPIO.OUT)

while True:
    GPIO.output(MOTOR1B, GPIO.HIGH)
    GPIO.output(MOTOR1E, GPIO.LOW)
    time.sleep(0.5)
    GPIO.output(MOTOR1B, GPIO.LOW)
    GPIO.output(MOTOR1E, GPIO.HIGH)
    time.sleep(0.5)

GPIO.cleanup()
