"""Sensor module – abstracts the PIR motion sensor GPIO interaction.

On non-Raspberry Pi hosts the ``RPi.GPIO`` library is unavailable, so a
software stub is used automatically to allow unit-testing and development on
ordinary computers.
"""

import time
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GPIO backend selection
# ---------------------------------------------------------------------------
try:
    import RPi.GPIO as _GPIO  # type: ignore
    _GPIO_AVAILABLE = True
except (ImportError, RuntimeError):  # RuntimeError on non-RPi hardware
    _GPIO_AVAILABLE = False

    class _GPIO:  # noqa: N801  # software stub
        BCM = "BCM"
        IN = "IN"
        OUT = "OUT"

        @staticmethod
        def setmode(mode: str) -> None:  # noqa: D401
            logger.debug("[STUB] GPIO.setmode(%s)", mode)

        @staticmethod
        def setup(pin: int, direction: str) -> None:
            logger.debug("[STUB] GPIO.setup(%s, %s)", pin, direction)

        @staticmethod
        def input(pin: int) -> bool:  # noqa: A003
            return False

        @staticmethod
        def cleanup() -> None:
            logger.debug("[STUB] GPIO.cleanup()")


class PIRSensor:
    """Wraps a PIR (passive infrared) motion sensor connected to a GPIO pin.

    Parameters
    ----------
    pin:
        BCM GPIO pin number where the PIR sensor data line is connected.
    poll_interval:
        Seconds to wait between consecutive GPIO reads.  Lower values
        give faster response but consume more CPU.
    """

    def __init__(self, pin: int = 17, poll_interval: float = 0.1) -> None:
        self.pin = pin
        self.poll_interval = poll_interval
        self._running = False
        self._motion_callback: Optional[Callable[[], None]] = None

        _GPIO.setmode(_GPIO.BCM)
        _GPIO.setup(self.pin, _GPIO.IN)
        logger.info("PIR sensor initialised on GPIO pin %d", self.pin)

    def on_motion(self, callback: Callable[[], None]) -> None:
        """Register *callback* to be invoked whenever motion is detected."""
        self._motion_callback = callback

    def read(self) -> bool:
        """Return ``True`` if the sensor is currently reporting motion."""
        return bool(_GPIO.input(self.pin))

    def start_monitoring(self) -> None:
        """Block the calling thread, polling the sensor and firing callbacks."""
        self._running = True
        logger.info("PIR sensor monitoring started (pin %d)", self.pin)
        try:
            while self._running:
                if self.read():
                    logger.debug("Motion detected on pin %d", self.pin)
                    if self._motion_callback is not None:
                        self._motion_callback()
                try:
                    time.sleep(self.poll_interval)
                except KeyboardInterrupt:
                    break
        finally:
            _GPIO.cleanup()
            logger.info("PIR sensor monitoring stopped")

    def stop_monitoring(self) -> None:
        """Signal the monitoring loop to exit on its next iteration."""
        self._running = False
