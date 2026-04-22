"""Core alarm module – orchestrates sensor, notifier, and scheduler."""

import logging
import threading
from typing import Optional

from .notifier import Notifier
from .scheduler import Scheduler
from .sensor import PIRSensor

logger = logging.getLogger(__name__)


class Alarm:
    """Central controller for the RaspiAlarm system.

    Parameters
    ----------
    pir_pin:
        BCM GPIO pin number for the PIR motion sensor.
    buzzer_pin:
        BCM GPIO pin number for the buzzer / alarm output.  Currently
        reserved for future hardware integration.
    notifier:
        A :class:`~raspialarm.notifier.Notifier` instance.  If ``None``,
        a default notifier (logging only, no email) is created.
    scheduler:
        An optional :class:`~raspialarm.scheduler.Scheduler` instance that
        automatically arms/disarms the alarm on a time schedule.
    poll_interval:
        Seconds between PIR sensor reads.
    """

    def __init__(
        self,
        pir_pin: int = 17,
        buzzer_pin: int = 18,
        notifier: Optional[Notifier] = None,
        scheduler: Optional[Scheduler] = None,
        poll_interval: float = 0.1,
    ) -> None:
        self.pir_pin = pir_pin
        self.buzzer_pin = buzzer_pin
        self.notifier = notifier or Notifier()
        self.scheduler = scheduler
        self.poll_interval = poll_interval

        self._armed = False
        self._lock = threading.Lock()
        self._sensor = PIRSensor(pin=pir_pin, poll_interval=poll_interval)
        self._sensor.on_motion(self._handle_motion)
        self._monitor_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def armed(self) -> bool:
        """``True`` when the alarm will respond to motion events."""
        with self._lock:
            return self._armed

    def arm(self) -> None:
        """Arm the alarm so that detected motion triggers a notification."""
        with self._lock:
            self._armed = True
        logger.info("Alarm ARMED")
        self.notifier.notify("Alarm armed.")

    def disarm(self) -> None:
        """Disarm the alarm; motion events are ignored until re-armed."""
        with self._lock:
            self._armed = False
        logger.info("Alarm DISARMED")
        self.notifier.notify("Alarm disarmed.")

    def start(self) -> None:
        """Start background monitoring and the optional scheduler."""
        if self.scheduler is not None:
            self.scheduler.on_arm = self.arm
            self.scheduler.on_disarm = self.disarm
            self.scheduler.start()

        self._monitor_thread = threading.Thread(
            target=self._sensor.start_monitoring,
            name="RaspiAlarm-Monitor",
            daemon=True,
        )
        self._monitor_thread.start()
        logger.info("RaspiAlarm monitoring thread started")

    def stop(self) -> None:
        """Stop sensor monitoring and the scheduler."""
        self._sensor.stop_monitoring()
        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=5)
        if self.scheduler is not None:
            self.scheduler.stop()
        logger.info("RaspiAlarm stopped")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _handle_motion(self) -> None:
        with self._lock:
            armed = self._armed
        if armed:
            logger.warning("Motion detected – alarm triggered!")
            self.notifier.notify("Motion detected – intruder alert!")
        else:
            logger.debug("Motion detected but alarm is disarmed – ignoring")
