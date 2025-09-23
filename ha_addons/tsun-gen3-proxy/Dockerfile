FROM ghcr.io/home-assistant/aarch64-base:latest

RUN apk add --no-cache python3 py3-pip bash bashio

WORKDIR /app

COPY requirements.txt /app/
COPY . /app/

RUN pip install --no-cache-dir --break-system-packages -r /app/requirements.txt

# Copier le script de démarrage et le rendre exécutable
COPY run.sh /run.sh
RUN chmod a+x /run.sh

# Le point d’entrée pour s6-overlay
CMD [ "/run.sh" ]
