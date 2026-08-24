import json
import logging
import queue
import threading

from log import setup_logging

setup_logging("CSTFeedbackPanel1.log")  # must run before importing InfluxDB - it logs a connection check at import time

from influxdb_client import Point

from InfluxDB import write_api, INFLUXDB_BUCKET, INFLUXDB_ORG
from MQTT import start_mqtt_listener

# fields that carry a list of reported issues, keyed by feedback category
LIST_CATEGORIES = ("cleaning", "maintenance", "feedback")


class FeedbackEvent:
    def __init__(self, panel_id, booth_type, attendance, category, issue):
        self.panel_id = panel_id
        self.booth_type = booth_type
        self.attendance = attendance
        self.category = category
        self.issue = issue

    def __str__(self):
        return f"panel {self.panel_id} ({self.booth_type}): {self.category}={self.issue}"


def parse_message(topic, payload_str):
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        logging.warning(f"malformed JSON payload on {topic}: {payload_str!r}")
        return []

    panel_id = payload.get("id")
    if not panel_id:
        return []
    booth_type = payload.get("type", "")
    attendance = payload.get("attendance", "")

    events = []
    rating = payload.get("rating")
    if rating:
        events.append(("rating", rating))

    for category in LIST_CATEGORIES:
        issues = payload.get(category)
        if isinstance(issues, list):
            for issue in issues:
                events.append((category, str(issue)))

    return [
        FeedbackEvent(panel_id, booth_type, attendance, category, issue)
        for category, issue in events
    ]


def parse_and_insert(topic, payload_str):
    for event in parse_message(topic, payload_str):
        logging.info(event)
        try:
            point = (
                Point("CSTFeedbackPanel1")
                .tag("id", event.panel_id)
                .tag("type", event.booth_type)
                .tag("toilet", f"{event.panel_id}_{event.booth_type}")
                .tag("category", event.category)
                .tag("attendance", event.attendance)
                .field(event.issue, 1.0)
            )
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        except Exception as e:
            logging.error(f"failed to insert {event}: {e}")


if __name__ == "__main__":
    message_queue = queue.Queue()

    threading.Thread(
        target=start_mqtt_listener,
        args=(message_queue, "CSTFeedbackPanel1"),
        daemon=True,
    ).start()

    try:
        while True:
            topic, payload_str = message_queue.get()
            parse_and_insert(topic, payload_str)
    except KeyboardInterrupt:
        logging.info("Stopping CSTFeedbackPanel1 collector...")
