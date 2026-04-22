"""Scheduler module – arm and disarm the alarm on a daily time window.

The scheduler runs in a background thread and toggles the alarm's armed state
based on configurable ``arm_time`` and ``disarm_time`` strings (``"HH:MM"``
24-hour format).
"""

import logging
import threading
import time
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class Scheduler:
    """Automatically arms/disarms the alarm at configured times.

    Parameters
    ----------
    arm_time:
        Time string (``"HH:MM"``) at which the alarm should be armed each day.
    disarm_time:
        Time string (``"HH:MM"``) at which the alarm should be disarmed each day.
    on_arm:
        Callable invoked when the scheduler arms the alarm.
    on_disarm:
        Callable invoked when the scheduler disarms the alarm.
    check_interval:
        How often (in seconds) the scheduler thread checks the current time.
    """

    def __init__(
        self,
        arm_time: Optional[str] = None,
        disarm_time: Optional[str] = None,
        on_arm: Optional[Callable[[], None]] = None,
        on_disarm: Optional[Callable[[], None]] = None,
        check_interval: int = 30,
    ) -> None:
        self.arm_time = arm_time
        self.disarm_time = disarm_time
        self.on_arm = on_arm
        self.on_disarm = on_disarm
        self.check_interval = check_interval

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_state: Optional[str] = None  # "armed" | "disarmed" | None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background scheduler thread."""
        if not (self.arm_time and self.disarm_time):
            logger.info("Scheduler disabled (no arm/disarm times configured)")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="RaspiAlarm-Scheduler", daemon=True
        )
        self._thread.start()
        logger.info(
            "Scheduler started: arm=%s, disarm=%s",
            self.arm_time,
            self.disarm_time,
        )

    def stop(self) -> None:
        """Signal the scheduler thread to stop and wait for it to exit."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.check_interval + 5)
        logger.info("Scheduler stopped")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run(self) -> None:
        while not self._stop_event.is_set():
            now_str = datetime.now().strftime("%H:%M")
            if now_str == self.arm_time and self._last_state != "armed":
                logger.info("Scheduler arming alarm at %s", now_str)
                self._last_state = "armed"
                if self.on_arm is not None:
                    self.on_arm()
            elif now_str == self.disarm_time and self._last_state != "disarmed":
                logger.info("Scheduler disarming alarm at %s", now_str)
                self._last_state = "disarmed"
                if self.on_disarm is not None:
                    self.on_disarm()
            self._stop_event.wait(timeout=self.check_interval)

    @staticmethod
    def validate_time_string(value: str) -> bool:
        """Return ``True`` if *value* is a valid ``"HH:MM"`` string."""
        try:
            datetime.strptime(value, "%H:%M")
            return True
        except ValueError:
            return False
