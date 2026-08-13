import json
import logging
import queue
import threading

from log import setup_logging

setup_logging("Bin_Sensor1.log")  # must run before importing InfluxDB - it logs a connection check at import time

from InfluxDB import insert_data
from MQTT import start_mqtt_listener


def _coerce(value):
    """Numeric fields sometimes arrive as strings (e.g. "volt": "4.19") -
    convert anything numeric-looking to float, drop anything that isn't."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


class SensorReading:
    def __init__(self, gateway_id, sensor_id, sensor_type, field_name, value):
        self.gateway_id = gateway_id
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.field_name = field_name
        self.value = value

    def __str__(self):
        return f"gateway {self.gateway_id}, {self.sensor_id} ({self.sensor_type}): {self.field_name}={self.value}"


def parse_message(topic, payload_str):
    topic_parts = topic.split("/")
    if len(topic_parts) < 3:
        return []
    gateway_id = topic_parts[2]  # e.g. "4" in Sensor/Bin_Sensor1/4

    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        logging.warning(f"malformed JSON payload on {topic}: {payload_str!r}")
        return []

    datas = payload.get("datas")
    if not isinstance(datas, dict):
        return []

    device_info = payload.get("device_info", {})
    sensor_id = device_info.get("unique_id")
    if not sensor_id:
        return []
    sensor_type = device_info.get("sensor_type", "")

    readings = []
    for field_name, raw_value in datas.items():
        value = _coerce(raw_value)
        if value is None:
            continue
        readings.append(SensorReading(gateway_id, sensor_id, sensor_type, field_name, value))

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
                "Bin_Sensor1",
                reading.sensor_type,
            )
        except Exception as e:
            logging.error(f"failed to insert {reading}: {e}")


if __name__ == "__main__":
    message_queue = queue.Queue()

    threading.Thread(
        target=start_mqtt_listener,
        args=(message_queue, "Bin_Sensor1"),
        daemon=True,
    ).start()

    try:
        while True:
            topic, payload_str = message_queue.get()
            parse_and_insert(topic, payload_str)
    except KeyboardInterrupt:
        logging.info("Stopping Bin_Sensor1 collector...")
