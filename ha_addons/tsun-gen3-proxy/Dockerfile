# Image de base avec Python 3.11 et pip déjà installé
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-python:3.11
FROM $BUILD_FROM

# Répertoire de travail
WORKDIR /app

# Copier et installer les dépendances Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copier le code source
COPY app /app/app
COPY src /app/src

# Copier le script de démarrage
COPY run.sh /run.sh
RUN chmod a+x /run.sh

# Démarrage du conteneur
CMD [ "/run.sh" ]
