#!/usr/bin/with-contenv bashio
# Script de démarrage du TSUN Gen3 Proxy

MQTT_HOST=$(bashio::config 'mqtt_host')
MQTT_PORT=$(bashio::config 'mqtt_port')
MQTT_USER=$(bashio::config 'mqtt_user')
MQTT_PASS=$(bashio::config 'mqtt_password')
LOG_LEVEL=$(bashio::config 'log_level')

export MQTT_HOST MQTT_PORT MQTT_USER MQTT_PASS LOG_LEVEL

exec python3 /app/run.py