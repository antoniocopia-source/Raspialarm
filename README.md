# RaspiAlarm

> Repositorio para el conjunto de códigos utilizados en el proyecto RaspiAlarm.
> *Repository for the set of codes used in the RaspiAlarm project.*

RaspiAlarm is a modular Raspberry Pi alarm system written in Python.  It reads
a PIR (passive infrared) motion sensor, fires configurable notifications
(log file and/or email), and supports automatic arm/disarm scheduling.

---

## Features

- **Motion detection** via a PIR sensor connected to a GPIO pin
- **Notifications** – plain-text log file and/or email (SMTP/SSL)
- **Scheduler** – automatically arm/disarm on a daily HH:MM schedule
- **Software GPIO stub** – runs and is testable on any PC without Raspberry Pi hardware
- **JSON configuration** – all settings in one `config.json` file

---

## Hardware Requirements

| Component        | Example part   | GPIO pin (default) |
|------------------|----------------|--------------------|
| PIR motion sensor | HC-SR501       | GPIO 17 (BCM)      |
| Buzzer (optional) | 5 V piezo      | GPIO 18 (BCM)      |

---

## Project Structure

```
Raspialarm/
├── raspialarm/
│   ├── __init__.py      # Package metadata
│   ├── alarm.py         # Central Alarm controller
│   ├── sensor.py        # PIR sensor / GPIO abstraction
│   ├── notifier.py      # Log-file and email notifications
│   └── scheduler.py     # Daily arm/disarm scheduling
├── tests/
│   └── test_alarm.py    # Unit tests (no hardware needed)
├── main.py              # Entry point
├── config.json          # Default configuration
└── requirements.txt     # Python dependencies
```

---

## Quick Start

### 1. Clone and install dependencies

```bash
git clone https://github.com/antoniocopia-source/Raspialarm.git
cd Raspialarm
pip install -r requirements.txt   # RPi.GPIO only needed on real hardware
```

### 2. Edit the configuration

```bash
cp config.json my_config.json
nano my_config.json
```

Key settings:

| Key              | Default  | Description                              |
|------------------|----------|------------------------------------------|
| `pir_pin`        | `17`     | BCM GPIO pin for the PIR sensor          |
| `buzzer_pin`     | `18`     | BCM GPIO pin for the buzzer              |
| `log_file`       | `"alarm_events.log"` | Path for the event log        |
| `arm_time`       | `"22:00"` | Daily arm time (`"HH:MM"`)              |
| `disarm_time`    | `"07:00"` | Daily disarm time (`"HH:MM"`)           |
| `smtp_host`      | `""`     | SMTP server for email alerts (optional)  |
| `recipient_email`| `""`     | Destination address for email alerts     |

### 3. Run

```bash
python main.py --config my_config.json
```

Press **Ctrl-C** to stop.

---

## Running the Tests

No Raspberry Pi hardware is required – the GPIO layer is automatically stubbed
on non-RPi hosts.

```bash
python -m pytest tests/ -v
```

---

## License

This project is released under the [MIT License](LICENSE).
