#!/usr/bin/with-contenv bashio
set -e

MQTT_HOST=$(bashio::config 'mqtt_host')
MQTT_PORT=$(bashio::config 'mqtt_port')
MQTT_USER=$(bashio::config 'mqtt_user')
MQTT_PASSWORD=$(bashio::config 'mqtt_password')
LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "Lancement du TSUN Gen3 Proxy vers MQTT ${MQTT_HOST}:${MQTT_PORT}"

exec python3 /app/run.py \
    --mqtt-host "$MQTT_HOST" \
    --mqtt-port "$MQTT_PORT" \
    --mqtt-user "$MQTT_USER" \
    --mqtt-password "$MQTT_PASSWORD" \
    --log-level "$LOG_LEVEL"
