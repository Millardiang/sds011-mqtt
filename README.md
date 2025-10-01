# SDS011 Air Quality Sensor — JSON + MQTT Publisher

```
==============================================================================
   SDS011 Air Quality Sensor JSON + MQTT Publisher
   Version: 1.0.0
   Copyright (C) 2025  Ian Millard
   License: GPL v3.0  (https://www.gnu.org/licenses/gpl-3.0.html)
==============================================================================
```

## 📖 Overview

This package reads particulate matter data from a **Nova Fitness SDS011** air quality sensor (via USB serial), outputs the latest measurement to a JSON file, and publishes it to an MQTT broker for integration into dashboards and weather station systems such as **WeeWX / DivumWX**.

### Features
- Queries **PM2.5** and **PM10** values from the SDS011.
- Stores the latest reading in `aqi.json` (single object, not rolling history).
- Publishes readings via MQTT with `retain` flag set (so subscribers get the last known value instantly).
- Designed to run continuously as a **systemd service**.

---

## 📂 File Layout

```
sds011/
├── bin/
│   └── user/
│       └── sds011.py       # main Python script
├── etc/
│   └── systemd/
│       └── sds011.service  # systemd unit file
├── LICENSE                 # GPL v3
└── README.md               # this documentation
```

---

## ⚙️ Requirements

- Python ≥ 3.8 (tested on 3.13)
- Virtual environment recommended
- Packages:
  - `pyserial`
  - `paho-mqtt`

Install inside venv:

```bash
source ~/particles-venv/bin/activate
pip install pyserial paho-mqtt
```

---

## 🖥️ Installation

1. **Copy script**  
   Place `sds011.py` into:

   ```
   /home/particles/airquality/bin/user/sds011.py
   ```

2. **Permissions**  
   Ensure script is executable:

   ```bash
   chmod +x /home/particles/airquality/bin/user/sds011.py
   ```

3. **JSON output directory**  
   Ensure JSON file path is writable:

   ```python
   JSON_FILE = '/var/www/html/aqi.json'
   ```

4. **Configure systemd service**  
   Create `/etc/systemd/system/sds011.service`:

   ```ini
   [Unit]
   Description=SDS011 Air Quality Sensor Publisher
   After=network.target

   [Service]
   Type=simple
   ExecStart=/home/particles/particles-venv/bin/python /home/particles/airquality/bin/user/sds011.py
   WorkingDirectory=/home/particles/airquality/bin/user
   Restart=always
   RestartSec=10
   User=particles
   Group=particles
   StandardOutput=journal
   StandardError=journal
   Environment="PYTHONUNBUFFERED=1"

   [Install]
   WantedBy=multi-user.target
   ```

5. **Enable & start service**  

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable sds011.service
   sudo systemctl start sds011.service
   ```

---

## 🌐 MQTT Details

- **Broker**: configured via `MQTT_HOST` and `MQTT_PORT`  
- **Topic**: `/weather/particulatematter` (customizable)  
- **QoS**: 1 (at-least-once delivery)  
- **Retain flag**: `True` (broker always stores the last reading)  

### Example payload

```json
{
  "pm25": 6.4,
  "pm10": 9.2,
  "time": "30.09.2025 17:23:42"
}
```

Subscribers will immediately receive this object upon subscription.

---

## 📜 Logging

Check logs via systemd:

```bash
journalctl -u sds011.service -f
```

Typical output:

```
PM2.5:  5.2 , PM10:  7.8
MQTT: Connected successfully to broker.
Going to sleep for 1 min...
```

---

## 🛠️ Troubleshooting

### No `/dev/ttyUSB0` found

- Check device connection:

  ```bash
  ls /dev/ttyUSB*
  dmesg | grep ttyUSB
  ```

- Adjust `ser.port` in `sds011.py` to correct device path.
- For persistent naming, add a `udev` rule to create `/dev/sds011`.

### Permission denied on `/dev/ttyUSB0`

Add user to `dialout` group:

```bash
sudo usermod -aG dialout particles
```

Then log out/in.

### MQTT not publishing

- Verify broker address (`MQTT_HOST`).
- Use `mosquitto_sub` to test:

  ```bash
  mosquitto_sub -h 192.168.1.150 -t /weather/particulatematter -v
  ```

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0** — see LICENSE for details.

```
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License v3 as published by
the Free Software Foundation.
```
