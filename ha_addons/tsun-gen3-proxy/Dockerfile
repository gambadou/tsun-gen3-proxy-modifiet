FROM ghcr.io/home-assistant/aarch64-base:latest

# Installer Python et pip
RUN apk add --no-cache python3 py3-pip bash

WORKDIR /app

# Copier le code Python et requirements
COPY requirements.txt /app/
COPY run.py /app/

# Installer les dépendances Python (forcer PEP 668)
RUN pip install --no-cache-dir --break-system-packages -r /app/requirements.txt

# Copier script de démarrage et rendre exécutable
COPY run.sh /run.sh
RUN chmod a+x /run.sh

# Le script sera lancé par s6-overlay (Supervisor)
CMD [ "/run.sh" ]
