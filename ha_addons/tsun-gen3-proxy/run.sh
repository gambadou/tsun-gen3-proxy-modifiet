#!/usr/bin/with-contenv bashio
# Script de démarrage de l’add-on TSUN Gen3 Proxy

# Lire la config depuis options.json
MQTT_HOST=$(bashio::config 'mqtt_host')
MQTT_PORT=$(bashio::config 'mqtt_port')
MQTT_USER=$(bashio::config 'mqtt_user')
MQTT_PASS=$(bashio::config 'mqtt_password')
LOG_LEVEL=$(bashio::config 'log_level')

# Exporter en variables d’environnement (optionnel)
export MQTT_HOST MQTT_PORT MQTT_USER MQTT_PASS LOG_LEVEL

# Lancer ton script Python
exec python3 /app/run.py

