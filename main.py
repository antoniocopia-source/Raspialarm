"""RaspiAlarm entry point.

Loads ``config.json`` from the repository root, wires up all components, and
runs the alarm until the user presses Ctrl-C.

Usage
-----
    python main.py [--config PATH]
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from raspialarm.alarm import Alarm
from raspialarm.notifier import Notifier
from raspialarm.scheduler import Scheduler


def _setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=getattr(logging, level.upper(), logging.INFO),
    )


def _load_config(path: Path) -> dict:
    if not path.exists():
        logging.warning("Config file not found at %s – using defaults", path)
        return {}
    with path.open(encoding="utf-8") as fh:
        content = fh.read().strip()
    if not content:
        return {}
    return json.loads(content)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="RaspiAlarm – Raspberry Pi alarm system")
    parser.add_argument(
        "--config",
        default="config.json",
        metavar="PATH",
        help="Path to configuration file (default: config.json)",
    )
    args = parser.parse_args(argv)

    config = _load_config(Path(args.config))
    _setup_logging(config.get("log_level", "INFO"))

    logger = logging.getLogger(__name__)
    logger.info("Starting RaspiAlarm v%s", _get_version())

    # --- Notifier -------------------------------------------------------
    notifier = Notifier(
        log_file=config.get("log_file"),
        smtp_host=config.get("smtp_host"),
        smtp_port=config.get("smtp_port", 465),
        smtp_user=config.get("smtp_user"),
        smtp_password=config.get("smtp_password"),
        recipient_email=config.get("recipient_email"),
    )

    # --- Scheduler ------------------------------------------------------
    arm_time = config.get("arm_time")
    disarm_time = config.get("disarm_time")
    scheduler = None
    if arm_time and disarm_time:
        if not Scheduler.validate_time_string(arm_time):
            logger.error("Invalid arm_time format: %r (expected HH:MM)", arm_time)
            return 1
        if not Scheduler.validate_time_string(disarm_time):
            logger.error("Invalid disarm_time format: %r (expected HH:MM)", disarm_time)
            return 1
        scheduler = Scheduler(arm_time=arm_time, disarm_time=disarm_time)

    # --- Alarm ----------------------------------------------------------
    alarm = Alarm(
        pir_pin=config.get("pir_pin", 17),
        buzzer_pin=config.get("buzzer_pin", 18),
        notifier=notifier,
        scheduler=scheduler,
        poll_interval=config.get("poll_interval", 0.1),
    )

    # Arm immediately if no scheduler is configured
    if scheduler is None:
        alarm.arm()

    alarm.start()

    try:
        logger.info("RaspiAlarm running – press Ctrl-C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        alarm.stop()
        logger.info("RaspiAlarm stopped – goodbye")

    return 0


def _get_version() -> str:
    try:
        from raspialarm import __version__
        return __version__
    except ImportError:
        return "unknown"


if __name__ == "__main__":
    sys.exit(main())
