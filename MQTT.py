"""
MQTT.py - MQTT listener, meant to run on its own thread.

start_mqtt_listener(message_queue, gateway_type) connects to the broker,
subscribes to SensorData/<gateway_type>/#, and for every message received,
pushes (topic, payload_str) onto message_queue. It does NOT parse or insert
anything itself - that's left to a separate consumer thread, so this stays
fast and never blocks on slower work.

Usage from another script - one call per gateway type, each on its own
thread with its own queue:

    import threading, queue
    from MQTT import start_mqtt_listener

    zb1_queue = queue.Queue()
    threading.Thread(
        target=start_mqtt_listener, args=(zb1_queue, "ZB1"), daemon=True
    ).start()

    while True:
        topic, payload_str = zb1_queue.get()
        # parse + insert into DB here, on the consumer side
        ...
"""

import logging
import os

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

MQTT_HOST = os.getenv("MQTT_BROKER_HOST")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USERNAME")
MQTT_PASS = os.getenv("MQTT_PASSWORD")
MQTT_CA = os.getenv("MQTT_TLS_CA_CERT")

def start_mqtt_listener(message_queue, gateway_type):
    topic = f"SensorData/{gateway_type}/#"

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            logging.info(f"Connected to MQTT broker, subscribing to {topic}")
            client.subscribe(topic)
        else:
            logging.error(f"Failed to connect to MQTT broker: {reason_code}")

    def on_disconnect(client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            logging.warning(f"Unexpectedly disconnected from MQTT broker: {reason_code}")

    def on_message(client, userdata, msg):
        payload_str = msg.payload.decode(errors="ignore")
        message_queue.put((msg.topic, payload_str))

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    if MQTT_USER and MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    if MQTT_CA and os.path.exists(MQTT_CA):
        client.tls_set(ca_certs=MQTT_CA)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(MQTT_HOST, MQTT_PORT)
    except Exception as e:
        logging.error(f"Could not connect to MQTT broker at {MQTT_HOST}:{MQTT_PORT}: {e}")
        return

    client.loop_forever()
