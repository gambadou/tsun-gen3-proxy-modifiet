ARG BUILD_FROM=ghcr.io/hassio-addons/base:15.0.3
FROM $BUILD_FROM

WORKDIR /app

# Installer Python et pip (obligatoire sur Alpine)
RUN apk add --no-cache python3 py3-pip

# Copier requirements.txt
COPY ../../requirements.txt /app/

# Installer les dépendances Python
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copier le script de lancement
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]