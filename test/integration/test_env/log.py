from datetime import datetime
from sys import stdout
from typing import TextIO
from os import write

logging_target = stdout


def set_logging_target(file: TextIO):
    global logging_target
    logging_target = file


def close_logging_target():
    global logging_target
    logging_target.close()


def log(message, lvl):
    write(logging_target.fileno(), bytes(f"[{lvl}] {datetime.now()}: {message}\n", encoding="utf-8"))


def info(message):
    log(message, "INFO")


def warn(message):
    log(message, "WARN")


def error(message):
    log(message, "ERROR")


def debug(message):
    log(message, "DEBUG")


def log_net(lvl_callable, message, service, port):
    lvl_callable(f"communication with {service} at {port}: {message}")
