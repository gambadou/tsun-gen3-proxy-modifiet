ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:15.0.3
FROM $BUILD_FROM

WORKDIR /app

# Installer Python et pip dans l'image de base
RUN apk add --no-cache python3 py3-pip

# Copier et installer les dépendances Python
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Copier ton code source et le script de démarrage
COPY app /app/app
COPY src /app/src
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]

