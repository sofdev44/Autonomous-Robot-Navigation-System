import RPi.GPIO as GPIO

HAT_LED_PINS = {
    11: 9,
    12: 25,
    13: 11
}

RGB_LED_PINS = {
    14: 0,    # left_R
    15: 19,   # left_G
    16: 13,   # left_B
    17: 1,    # right_R
    18: 5,    # right_G
    19: 6     # right_B
}


def switchSetup():

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    for pin in HAT_LED_PINS.values():
        GPIO.setup(pin, GPIO.OUT)

    for pin in RGB_LED_PINS.values():
        GPIO.setup(pin, GPIO.OUT)

    set_all_switch_off()


def switch_hat_led(code, status):

    pin = HAT_LED_PINS[code]

    if status == 1:
        GPIO.output(pin, GPIO.HIGH)
    else:
        GPIO.output(pin, GPIO.LOW)


def switch_rgb_led(code, status):

    pin = RGB_LED_PINS[code]

    if status == 1:
        GPIO.output(pin, GPIO.LOW)
    else:
        GPIO.output(pin, GPIO.HIGH)


def individual_led_guiding(command):

    action = command // 10
    led_number = command % 10

    status = 1 if action == 1 else 0

    code = 10 + led_number

    if code in HAT_LED_PINS:
        switch_hat_led(code, status)

    elif code in RGB_LED_PINS:
        switch_rgb_led(code, status)

    else:
        print("Invalid LED code")


def set_all_switch_off():

    for code in HAT_LED_PINS:
        switch_hat_led(code, 0)

    for code in RGB_LED_PINS:
        switch_rgb_led(code, 0)


def print_menu():

    print()
    print("==============================================")
    print("MANUAL LED CONTROL")
    print("==============================================")
    print("11  ON  LED1")
    print("12  ON  LED2")
    print("13  ON  LED3")
    print("14  ON  left_R")
    print("15  ON  left_G")
    print("16  ON  left_B")
    print("17  ON  right_R")
    print("18  ON  right_G")
    print("19  ON  right_B")
    print()
    print("21  OFF LED1")
    print("22  OFF LED2")
    print("23  OFF LED3")
    print("24  OFF left_R")
    print("25  OFF left_G")
    print("26  OFF left_B")
    print("27  OFF right_R")
    print("28  OFF right_G")
    print("29  OFF right_B")
    print()
    print("0   EXIT")
    print("==============================================")


def main():

    switchSetup()

    print_menu()

    try:

        while True:

            cmd = input("Command : ").strip()

            if cmd == "0":
                break

            if not cmd.isdigit():
                print("Enter a number")
                continue

            cmd = int(cmd)

            if (11 <= cmd <= 19) or (21 <= cmd <= 29):
                individual_led_guiding(cmd)
            else:
                print("Unknown command")

    except KeyboardInterrupt:
        pass

    finally:
        set_all_switch_off()
        GPIO.cleanup()
        print("GPIO released")


if __name__ == "__main__":
    main()
