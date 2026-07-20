#!/bin/sh
set -eu
cd /opt/openhems

echo "[OpenHEMS] Starting version 0.5.0"
echo "[OpenHEMS] Python: $(python --version 2>&1)"
python -c "from openhems_core.main import app; print('[OpenHEMS] Python application import OK:', app.title)"

exec python -m uvicorn openhems_core.main:app \
  --app-dir /opt/openhems/backend \
  --host 0.0.0.0 \
  --port 8099 \
  --proxy-headers \
  --forwarded-allow-ips='*'
