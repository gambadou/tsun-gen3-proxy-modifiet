ARG BUILD_FROM=ghcr.io/hassio-addons/base:15.0.3
FROM $BUILD_FROM

WORKDIR /app

COPY ../../app /app/app
COPY ../../src /app/src
COPY ../../requirements.txt /app/

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY run.sh /run.sh
RUN chmod a+x
