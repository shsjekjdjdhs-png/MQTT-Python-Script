"""
InfluxDB.py - reusable InfluxDB write helper.

Connects once, at import time, and reuses the same write_api for every
insert_data() call afterward - reconnecting per insert would be wasteful,
since each connection has real network/auth overhead.

insert_data(sensor_id, field_name, value, gateway_id, gateway_type, sensor_type="")
writes one point. gateway_type is the measurement (e.g. "Tasmota1");
gateway_id is the physical gateway's own number (e.g. "1", "2", "6").
sensor_type can be left blank where it doesn't apply (e.g. Zigbee sensors).

Usage:

    from InfluxDB import insert_data

    insert_data("0x8F3A", "BatteryPercentage", 100, "1", "Tasmota1")
"""
import logging
import os

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

try:
    if client.ping():
        logging.info(f"Connected to InfluxDB at {INFLUXDB_URL}")
    else:
        logging.error(f"InfluxDB at {INFLUXDB_URL} did not respond to ping")
except Exception as e:
    logging.error(f"Could not reach InfluxDB at {INFLUXDB_URL}: {e}")


def insert_data(sensor_id, field_name, value, gateway_id, gateway_type, sensor_type=""):
    # InfluxDB locks a field's type on first write - int vs float mixed under
    # the same field name gets writes rejected. Always store numbers as
    # float here, once, so no caller needs to remember to do it themselves.
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = float(value)

    point = (
        Point(gateway_type)
        .tag("gateway_id", gateway_id)
        .tag("sensor_id", sensor_id)
        .tag("sensor_type", sensor_type)
        .field(field_name, value)
    )
    write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
