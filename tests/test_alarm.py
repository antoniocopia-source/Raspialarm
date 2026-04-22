"""Unit tests for the RaspiAlarm package.

These tests run entirely without Raspberry Pi hardware by relying on the
software GPIO stub that is loaded automatically when ``RPi.GPIO`` is absent.
"""

import threading
import time
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# raspialarm.notifier
# ---------------------------------------------------------------------------
class TestNotifier(unittest.TestCase):

    def test_notify_writes_log_file(self):
        import tempfile
        import os
        from raspialarm.notifier import Notifier

        with tempfile.NamedTemporaryFile(mode="r", suffix=".log", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            notifier = Notifier(log_file=tmp_path)
            notifier.notify("test event")
            with open(tmp_path) as fh:
                content = fh.read()
            self.assertIn("test event", content)
        finally:
            os.unlink(tmp_path)

    def test_notify_no_log_file(self):
        from raspialarm.notifier import Notifier

        # Should not raise even without a log file
        notifier = Notifier()
        notifier.notify("no file test")

    def test_email_disabled_when_config_incomplete(self):
        from raspialarm.notifier import Notifier

        notifier = Notifier(smtp_host="smtp.example.com")  # missing other fields
        self.assertFalse(notifier._email_enabled)

    def test_email_enabled_when_fully_configured(self):
        from raspialarm.notifier import Notifier

        notifier = Notifier(
            smtp_host="smtp.example.com",
            smtp_user="user@example.com",
            smtp_password="secret",
            recipient_email="dest@example.com",
        )
        self.assertTrue(notifier._email_enabled)


# ---------------------------------------------------------------------------
# raspialarm.scheduler
# ---------------------------------------------------------------------------
class TestScheduler(unittest.TestCase):

    def test_validate_time_string_valid(self):
        from raspialarm.scheduler import Scheduler

        self.assertTrue(Scheduler.validate_time_string("07:30"))
        self.assertTrue(Scheduler.validate_time_string("00:00"))
        self.assertTrue(Scheduler.validate_time_string("23:59"))

    def test_validate_time_string_invalid(self):
        from raspialarm.scheduler import Scheduler

        self.assertFalse(Scheduler.validate_time_string("25:00"))
        self.assertFalse(Scheduler.validate_time_string("not-a-time"))
        self.assertFalse(Scheduler.validate_time_string(""))

    def test_start_stop_no_times(self):
        from raspialarm.scheduler import Scheduler

        # Scheduler with no times configured should start and stop silently
        s = Scheduler()
        s.start()
        s.stop()

    def test_scheduler_calls_on_arm(self):
        from raspialarm.scheduler import Scheduler

        arm_called = threading.Event()
        now_str = time.strftime("%H:%M")

        s = Scheduler(
            arm_time=now_str,
            disarm_time="00:01",
            on_arm=lambda: arm_called.set(),
            check_interval=1,
        )
        s.start()
        try:
            triggered = arm_called.wait(timeout=5)
        finally:
            s.stop()

        self.assertTrue(triggered, "on_arm callback was not called within timeout")


# ---------------------------------------------------------------------------
# raspialarm.sensor (stub GPIO)
# ---------------------------------------------------------------------------
class TestPIRSensor(unittest.TestCase):

    def test_read_returns_bool(self):
        from raspialarm.sensor import PIRSensor

        sensor = PIRSensor(pin=17)
        result = sensor.read()
        self.assertIsInstance(result, bool)

    def test_on_motion_registered(self):
        from raspialarm.sensor import PIRSensor

        sensor = PIRSensor(pin=17)
        cb = MagicMock()
        sensor.on_motion(cb)
        self.assertIs(sensor._motion_callback, cb)

    def test_stop_monitoring_ends_loop(self):
        from raspialarm.sensor import PIRSensor

        sensor = PIRSensor(pin=17, poll_interval=0.05)
        t = threading.Thread(target=sensor.start_monitoring, daemon=True)
        t.start()
        time.sleep(0.2)
        sensor.stop_monitoring()
        t.join(timeout=2)
        self.assertFalse(t.is_alive())


# ---------------------------------------------------------------------------
# raspialarm.alarm
# ---------------------------------------------------------------------------
class TestAlarm(unittest.TestCase):

    def _make_alarm(self):
        from raspialarm.alarm import Alarm

        return Alarm(pir_pin=17, buzzer_pin=18, poll_interval=0.05)

    def test_initially_disarmed(self):
        alarm = self._make_alarm()
        self.assertFalse(alarm.armed)

    def test_arm_disarm(self):
        alarm = self._make_alarm()
        alarm.arm()
        self.assertTrue(alarm.armed)
        alarm.disarm()
        self.assertFalse(alarm.armed)

    def test_motion_triggers_notification_when_armed(self):
        alarm = self._make_alarm()
        alarm.notifier = MagicMock()
        alarm.arm()
        alarm._handle_motion()
        alarm.notifier.notify.assert_called()

    def test_motion_ignored_when_disarmed(self):
        alarm = self._make_alarm()
        alarm.notifier = MagicMock()
        # alarm is disarmed by default
        alarm._handle_motion()
        # arm notification was never sent (disarmed, so _handle_motion skips)
        alarm.notifier.notify.assert_not_called()

    def test_start_stop(self):
        alarm = self._make_alarm()
        alarm.start()
        time.sleep(0.1)
        alarm.stop()


# ---------------------------------------------------------------------------
# main module
# ---------------------------------------------------------------------------
class TestMain(unittest.TestCase):

    def test_main_runs_with_defaults(self):
        """main() should start and stop cleanly (no GPIO hardware required)."""
        import threading
        from main import main

        result_holder = []

        def _run():
            # Patch time.sleep only in the main module so daemon threads are unaffected
            with patch("main.time.sleep", side_effect=KeyboardInterrupt):
                result_holder.append(main([]))

        t = threading.Thread(target=_run)
        t.start()
        t.join(timeout=10)
        self.assertFalse(t.is_alive(), "main() did not exit in time")
        self.assertEqual(result_holder[0], 0)

    def test_main_invalid_arm_time(self):
        """main() with an empty/blank config file should exit cleanly with return code 0."""
        import threading
        from main import main

        result_holder = []

        def _run():
            with patch("main.time.sleep", side_effect=KeyboardInterrupt):
                result_holder.append(main(["--config", "/dev/null"]))

        t = threading.Thread(target=_run)
        t.start()
        t.join(timeout=10)
        self.assertFalse(t.is_alive(), "main() did not exit in time")
        self.assertEqual(result_holder[0], 0)


if __name__ == "__main__":
    unittest.main()
