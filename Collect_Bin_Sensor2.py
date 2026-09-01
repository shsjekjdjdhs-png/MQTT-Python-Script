import json
import logging
import queue
import threading

from log import setup_logging

setup_logging("Bin_Sensor2.log")  # must run before importing InfluxDB - it logs a connection check at import time

from InfluxDB import insert_data
from MQTT import start_mqtt_listener

SENSOR_TYPE = "Ding Tek Bin sensor DF703"

# only actual sensor readings are stored - config/threshold fields (e.g.
# threshold_full, interval_upload) are dropped
READING_FIELDS = {
    "air_height",
    "volt",
    "temperature",
    "tilt_angle",
    "longitude",
    "latitude",
    "alarm_full",
    "alarm_battery",
    "alarm_fire",
    "alarm_fall",
    "frame_counter",
}


def _coerce(value):
    """Config/threshold fields arrive as strings (e.g. "threshold_full": "20") -
    convert anything numeric-looking to float, drop anything that isn't."""
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


class SensorReading:
    def __init__(self, gateway_id, sensor_id, field_name, value):
        self.gateway_id = gateway_id
        self.sensor_id = sensor_id
        self.field_name = field_name
        self.value = value

    def __str__(self):
        return f"gateway {self.gateway_id}, {self.sensor_id} ({SENSOR_TYPE}): {self.field_name}={self.value}"


def parse_message(topic, payload_str):
    topic_parts = topic.split("/")
    if len(topic_parts) < 3:
        return []
    sensor_id = topic_parts[2]  # e.g. "12" in SensorData/Bin_Sensor2/12/Pub

    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        logging.warning(f"malformed JSON payload on {topic}: {payload_str!r}")
        return []

    if not isinstance(payload, dict):
        return []

    datas = payload.get("datas")
    if not isinstance(datas, dict):
        return []

    readings = []
    for field_name, raw_value in datas.items():
        if field_name not in READING_FIELDS:
            continue
        value = _coerce(raw_value)
        if value is None:
            continue
        readings.append(SensorReading("nil", sensor_id, field_name, value))

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
                "Bin_Sensor2",
                SENSOR_TYPE,
            )
        except Exception as e:
            logging.error(f"failed to insert {reading}: {e}")


if __name__ == "__main__":
    message_queue = queue.Queue()

    threading.Thread(
        target=start_mqtt_listener,
        args=(message_queue, "Bin_Sensor2"),
        daemon=True,
    ).start()

    try:
        while True:
            topic, payload_str = message_queue.get()
            parse_and_insert(topic, payload_str)
    except KeyboardInterrupt:
        logging.info("Stopping Bin_Sensor2 collector...")
