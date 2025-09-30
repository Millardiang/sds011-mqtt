#!/usr/bin/python -u
# coding=utf-8
# SDS011 particulate matter sensor reader
# Outputs latest values to JSON file and publishes to MQTT
#
# Dependencies:
#   pip install paho-mqtt pyserial
#
# JSON file format:
#   {"pm25": 6.4, "pm10": 9.2, "time": "30.09.2025 17:23:42"}

from __future__ import print_function
import serial, struct, sys, time, json
import paho.mqtt.client as mqtt

DEBUG = 0
CMD_MODE = 2
CMD_QUERY_DATA = 4
CMD_DEVICE_ID = 5
CMD_SLEEP = 6
CMD_FIRMWARE = 7
CMD_WORKING_PERIOD = 8
MODE_ACTIVE = 0
MODE_QUERY = 1
PERIOD_CONTINUOUS = 0

JSON_FILE = '/var/www/html/aqi.json'

# MQTT settings
MQTT_HOST = "192.168.1.150"   # your broker IP
MQTT_PORT = 1883
MQTT_TOPIC = "/weather/particulatematter"
MQTT_CLIENT_ID = "sds011_sensor"

# Serial settings
ser = serial.Serial()
ser.port = "/dev/ttyUSB0"
ser.baudrate = 9600
ser.open()
ser.flushInput()

def dump(d, prefix=''):
    print(prefix + ' '.join(x.encode('hex') for x in d))

def construct_command(cmd, data=[]):
    assert len(data) <= 12
    data += [0,] * (12-len(data))
    checksum = (sum(data) + cmd - 2) % 256
    ret = "\xaa\xb4" + chr(cmd)
    ret += ''.join(chr(x) for x in data)
    ret += "\xff\xff" + chr(checksum) + "\xab"

    if DEBUG:
        dump(ret, '> ')
    return ret

def process_data(d):
    r = struct.unpack('<HHxxBB', d[2:])
    pm25 = r[0]/10.0
    pm10 = r[1]/10.0
    return [pm25, pm10]

def process_version(d):
    r = struct.unpack('<BBBHBB', d[3:])
    print("Firmware:", r)

def read_response():
    byte = 0
    while byte != "\xaa":
        byte = ser.read(size=1)
    d = ser.read(size=9)
    if DEBUG:
        dump(d, '< ')
    return byte + d

def cmd_set_mode(mode=MODE_QUERY):
    ser.write(construct_command(CMD_MODE, [0x1, mode]))
    read_response()

def cmd_query_data():
    ser.write(construct_command(CMD_QUERY_DATA))
    d = read_response()
    values = []
    if d[1] == "\xc0":
        values = process_data(d)
    return values

def cmd_set_sleep(sleep):
    mode = 0 if sleep else 1
    ser.write(construct_command(CMD_SLEEP, [0x1, mode]))
    read_response()

def cmd_set_working_period(period):
    ser.write(construct_command(CMD_WORKING_PERIOD, [0x1, period]))
    read_response()

def cmd_firmware_ver():
    ser.write(construct_command(CMD_FIRMWARE))
    d = read_response()
    process_version(d)

def cmd_set_id(id):
    id_h = (id>>8) % 256
    id_l = id % 256
    ser.write(construct_command(CMD_DEVICE_ID, [0]*10+[id_l, id_h]))
    read_response()

# ----- MQTT setup -----
client = mqtt.Client(MQTT_CLIENT_ID)

def mqtt_connect():
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        client.loop_start()
        print("Connected to MQTT broker:", MQTT_HOST)
    except Exception as e:
        print("MQTT connection failed:", e)

def pub_mqtt(jsonrow):
    payload = json.dumps(jsonrow)
    result = client.publish(MQTT_TOPIC, payload, qos=1, retain=True)
    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        print("MQTT publish failed:", result.rc)

# ----------------------

if __name__ == "__main__":
    mqtt_connect()

    cmd_set_sleep(0)
    cmd_firmware_ver()
    cmd_set_working_period(PERIOD_CONTINUOUS)
    cmd_set_mode(MODE_QUERY)

    while True:
        cmd_set_sleep(0)
        values = None

        # Collect a few samples, keep last valid one
        for t in range(15):
            v = cmd_query_data()
            if v and len(v) == 2:
                values = v
                print("PM2.5:", values[0], ", PM10:", values[1])
            time.sleep(2)

        if values:
            jsonrow = {
                'pm25': values[0],
                'pm10': values[1],
                'time': time.strftime("%d.%m.%Y %H:%M:%S")
            }

            # Save JSON file (overwrite with current value only)
            with open(JSON_FILE, 'w') as outfile:
                json.dump(jsonrow, outfile)

            # Publish to MQTT
            pub_mqtt(jsonrow)

        print("Going to sleep for 1 min...")
        cmd_set_sleep(1)
        time.sleep(60)
