# Image de base Home Assistant avec Python 3.11 + pip
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-python:3.11
FROM $BUILD_FROM

# Définir le dossier de travail
WORKDIR /app

# Copier les dépendances
COPY requirements.txt /app/

# Installer les dépendances Python
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Copier ton code source et le script de démarrage
COPY src /app/src
COPY run.sh /run.sh

# Donner les droits d’exécution
RUN chmod a+x /run.sh

# Commande de lancement de l’add-on
CMD [ "/run.sh" ]
