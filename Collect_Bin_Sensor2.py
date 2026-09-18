import json
import logging
import queue
import threading
from datetime import datetime

from log import setup_logging

setup_logging("Bin_Sensor2.log")  # must run before importing InfluxDB - it logs a connection check at import time

from GoogleSheets import append_row
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


# Columns written to the Google Sheet, in order. This is separate from
# READING_FIELDS (which controls InfluxDB) so a field can be dropped from
# the sheet without affecting InfluxDB - just comment out its line.
SHEET_FIELDS = [
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
]

SHEET_HEADER = ["date", "time", "bin_status", "sensor_id"] + SHEET_FIELDS


def _bin_status(alarm_full_value):
    if alarm_full_value is None:
        return ""
    return "Full" if alarm_full_value >= 1 else "Normal"


def parse_and_insert(topic, payload_str):
    readings = parse_message(topic, payload_str)

    for reading in readings:
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

    if readings:
        sensor_id = readings[0].sensor_id
        values_by_field = {reading.field_name: reading.value for reading in readings}
        now = datetime.now()
        row = [
            now.strftime("%d/%m/%Y"),
            now.strftime("%H:%M:%S"),
            _bin_status(values_by_field.get("alarm_full")),
            sensor_id,
        ] + [values_by_field.get(field, "") for field in SHEET_FIELDS]
        try:
            append_row(row, "Bin_Sensor2", "Bin_Sensor2", header=SHEET_HEADER)
        except Exception as e:
            logging.error(f"failed to append row to Google Sheet: {e}")


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
