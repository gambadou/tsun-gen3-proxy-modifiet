# Utiliser l'image officielle Home Assistant Add-on
ARG BUILD_FROM=ghcr.io/hassio-addons/base-python:15.0.3
FROM $BUILD_FROM

# Répertoire de travail
WORKDIR /app

# Copier le code et les dépendances
COPY ../../requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ../../app /app/app
COPY ../../src /app/src

# Script de démarrage
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
