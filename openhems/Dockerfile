FROM python:3.13-alpine

WORKDIR /opt/openhems

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/opt/openhems/backend

COPY requirements.txt /opt/openhems/requirements.txt
RUN pip install --no-cache-dir -r /opt/openhems/requirements.txt

COPY backend /opt/openhems/backend
COPY run.sh /run.sh
RUN chmod 0755 /run.sh \
    && python -c "from openhems_core.main import app; print('OpenHEMS build import OK:', app.title)"

EXPOSE 8099
CMD ["/run.sh"]
