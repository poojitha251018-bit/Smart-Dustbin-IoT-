from machine import Pin, PWM, time_pulse_us
import network
import time
import urequests


# ==========================================
# SMART DUSTBIN
# ESP32 + HC-SR04 + SERVO + THINGSPEAK
# ==========================================


# ==========================================
# 1. PIN CONFIGURATION
# ==========================================

TRIG_PIN = 22
ECHO_PIN = 23
SERVO_PIN = 18


# ==========================================
# 2. WIFI SETTINGS
# ==========================================

SSID = "Wokwi-GUEST"
PASSWORD = ""


# ==========================================
# 3. THINGSPEAK SETTINGS
# ==========================================

# Put your NEW ThingSpeak WRITE API KEY here
API_KEY = "WUGGEPBSGXP91OUH"

THINGSPEAK_URL = "http://api.thingspeak.com/update"


# ==========================================
# 4. HARDWARE SETUP
# ==========================================

trig = Pin(TRIG_PIN, Pin.OUT)
echo = Pin(ECHO_PIN, Pin.IN)

servo = PWM(Pin(SERVO_PIN), freq=50)


# ==========================================
# 5. SERVO FUNCTION
# ==========================================

def servo_angle(angle):

    min_duty = 26
    max_duty = 128

    duty = int(
        min_duty +
        (angle / 180) *
        (max_duty - min_duty)
    )

    servo.duty(duty)


# ==========================================
# 6. ULTRASONIC SENSOR FUNCTION
# ==========================================

def get_distance():

    # Make sure trigger is LOW
    trig.value(0)
    time.sleep_us(2)

    # Send 10 microsecond pulse
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)

    try:

        duration = time_pulse_us(
            echo,
            1,
            30000
        )

        # Invalid measurement
        if duration < 0:
            return -1

        # Convert time to distance in cm
        distance = (duration * 0.0343) / 2

        return distance

    except Exception as error:

        print("Sensor error:", error)

        return -1


# ==========================================
# 7. WIFI CONNECTION
# ==========================================

def connect_wifi():

    wifi = network.WLAN(network.STA_IF)

    wifi.active(True)

    print("Starting WiFi...")

    if not wifi.isconnected():

        print("Connecting to Wokwi-GUEST...")

        wifi.connect(SSID, PASSWORD)

        timeout = 15

        while not wifi.isconnected() and timeout > 0:

            print("Connecting...")

            time.sleep(1)

            timeout = timeout - 1

    if wifi.isconnected():

        print("WiFi connected!")

        print("IP:", wifi.ifconfig()[0])

    else:

        print("WiFi connection FAILED!")

    return wifi


# ==========================================
# 8. SEND DATA TO THINGSPEAK
# ==========================================

def send_to_thingspeak(distance, lid_status):

    response = None

    try:

        url = (
            THINGSPEAK_URL
            + "?api_key=" + API_KEY
            + "&field1=" + str(round(distance, 2))
            + "&field2=" + str(lid_status)
        )

        print("Sending data to ThingSpeak...")
        print("Distance:", round(distance, 2), "cm")
        print("Lid Status:", lid_status)

        response = urequests.get(url)

        status = response.status_code
        result = response.text

        print("HTTP status:", status)
        print("ThingSpeak response:", result)

        response.close()
        response = None

        if status == 200 and result != "0":

            print("Data uploaded successfully!")

            return True

        else:

            print("ThingSpeak rejected the update.")

            return False

    except Exception as error:

        print("ThingSpeak error:", error)

        if response is not None:

            try:
                response.close()
            except:
                pass

        return False


# ==========================================
# 9. START WIFI
# ==========================================

wifi = connect_wifi()


# ==========================================
# 10. START WITH LID CLOSED
# ==========================================

servo_angle(0)

print("--------------------------------")
print("SMART DUSTBIN STARTED")
print("--------------------------------")


# ==========================================
# 11. FIRST UPLOAD
# ==========================================
# Wait 16 seconds before the first upload.
# This avoids an immediate ThingSpeak
# update after restarting the simulation.

last_upload = time.time()


# ==========================================
# 12. MAIN PROGRAM LOOP
# ==========================================

while True:

    # Get distance
    distance = get_distance()


    # ======================================
    # VALID DISTANCE
    # ======================================

    if distance > 0:

        print("--------------------------------")

        print(
            "Distance:",
            round(distance, 2),
            "cm"
        )


        # ==================================
        # OBJECT WITHIN 20 CM
        # ==================================

        if distance <= 20:

            servo_angle(90)

            lid_status = 1

            print("Lid: OPEN")


        # ==================================
        # OBJECT MORE THAN 20 CM
        # ==================================

        else:

            servo_angle(0)

            lid_status = 0

            print("Lid: CLOSED")


        # ==================================
        # THINGSPEAK UPLOAD
        # ==================================

        current_time = time.time()

        if current_time - last_upload >= 16:

            # Check Wi-Fi
            if not wifi.isconnected():

                print("WiFi disconnected!")

                wifi = connect_wifi()


            # Upload only if Wi-Fi is connected
            if wifi.isconnected():

                success = send_to_thingspeak(
                    distance,
                    lid_status
                )

                if success:

                    last_upload = current_time

                else:

                    print("Data upload failed.")


    # ======================================
    # INVALID DISTANCE
    # ======================================

    else:

        print("Distance measurement failed.")


    # Wait 1 second before next measurement
    time.sleep(1)
