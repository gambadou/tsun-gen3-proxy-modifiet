import os
import logging

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("tsun-proxy")

def main():
    logger.info("Démarrage du TSUN Gen3 Proxy")
    logger.info(f"MQTT → {MQTT_HOST}:{MQTT_PORT} (user={MQTT_USER})")
    # 👉 Ici tu branches ton code proxy/TSUN

if __name__ == "__main__":
    main()
