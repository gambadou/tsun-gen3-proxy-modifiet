ARG BUILD_FROM=ghcr.io/hassio-addons/base:15.0.3
FROM $BUILD_FROM

WORKDIR /app

# Copier les fichiers nécessaires dans l’image
COPY requirements.txt /app/
COPY app /app/app
COPY src /app/src

# Installer les dépendances Python
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copier le script de démarrage
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
