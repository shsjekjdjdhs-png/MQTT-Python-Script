"""
log.py - reusable logging setup.

Call setup_logging(log_file) once, near the start of your script. It writes
logs into Logs/<log_file>, next to this file, and also prints them to the
terminal.

Then log as normal - as many times as you want, from anywhere in your
script. Since each script writes to its own file, there's no need to name a
logger to tell messages apart - just use the module functions directly:

    from log import setup_logging
    import logging

    setup_logging("myscript.log")

    logging.info("normal message")
    logging.warning("something looks off")
    logging.error("something failed")

Pass level=logging.DEBUG to see debug() messages too (they're hidden by
default):

    setup_logging("myscript.log", level=logging.DEBUG)
"""

import logging
import os

def setup_logging(log_file, level=logging.INFO):
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(),
        ],
    )
