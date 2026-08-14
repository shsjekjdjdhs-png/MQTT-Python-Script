import json
import logging
import queue
import threading

from log import setup_logging

setup_logging("Tasmota1.log")  # must run before importing InfluxDB - it logs a connection check at import time

from InfluxDB import insert_data
from MQTT import start_mqtt_listener

IGNORED_KEYS = {"Device", "Endpoint"}

class SensorReading:
    def __init__(self, gateway_id, sensor_id, field_name, value):
        self.gateway_id = gateway_id
        self.sensor_id = sensor_id
        self.field_name = field_name
        self.value = value

    def __str__(self):
        return f"gateway {self.gateway_id}, {self.sensor_id}: {self.field_name}={self.value}"

def parse_message(topic, payload_str):
    if not topic.endswith("/tele/SENSOR"):
        return []

    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        logging.warning(f"malformed JSON payload on {topic}: {payload_str!r}")
        return []

    zb_received = payload.get("ZbReceived")  # fixed key name from the Tasmota firmware
    if not zb_received:
        return []

    gateway_id = topic.split("/")[2]  # SensorData/Tasmota1/<gateway_id>/tele/SENSOR

    readings = []
    for sensor_id, data in zb_received.items():
        for field_name, value in data.items():
            if field_name in IGNORED_KEYS or not isinstance(value, (int, float)):
                continue
            if isinstance(value, bool):
                value = int(value)
            readings.append(SensorReading(gateway_id, sensor_id, field_name, value))

    return readings

def parse_and_insert(topic, payload_str):
    for reading in parse_message(topic, payload_str):
        logging.info(reading)
        try:
            insert_data(
                reading.sensor_id,
                reading.field_name,
                reading.value,
                reading.gateway_id,
                "Tasmota1",
            )
        except Exception as e:
            logging.error(f"failed to insert {reading}: {e}")

if __name__ == "__main__":
    message_queue = queue.Queue()

    threading.Thread(
        target=start_mqtt_listener,
        args=(message_queue, "Tasmota1"),
        daemon=True,
    ).start()

    try:
        while True:
            topic, payload_str = message_queue.get()
            parse_and_insert(topic, payload_str)
    except KeyboardInterrupt:
        logging.info("Stopping Tasmota1 collector...")
