import time
import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
BUTTON_PIN = 22
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
while True:
    if GPIO.input(BUTTON_PIN) == GPIO.HIGH:
        print("Button was pushed!")
        time.sleep(0.5)
