import argparse
import logging
import paho.mqtt.client as mqtt

parser = argparse.ArgumentParser()
parser.add_argument("--mqtt-host", required=True)
parser.add_argument("--mqtt-port", type=int, required=True)
parser.add_argument("--mqtt-user", required=True)
parser.add_argument("--mqtt-password", required=True)
parser.add_argument("--log-level", default="info")
args = parser.parse_args()

logging.basicConfig(
    level=getattr(logging, args.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("tsun-proxy")

# Connexion MQTT
client = mqtt.Client()
client.username_pw_set(args.mqtt_user, args.mqtt_password)
client.connect(args.mqtt_host, args.mqtt_port, 60)

logger.info(f"Connecté à MQTT {args.mqtt_host}:{args.mqtt_port}")

try:
    client.loop_forever()
except KeyboardInterrupt:
    logger.info("Arrêt du TSUN Gen3 Proxy")
