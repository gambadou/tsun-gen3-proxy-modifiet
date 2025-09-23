FROM ghcr.io/home-assistant/aarch64-base:latest

# Installer Python et pip
RUN apk add --no-cache python3 py3-pip bash

WORKDIR /app

# Copier requirements et code
COPY requirements.txt /app/
COPY run.py /app/

# Installer dépendances Python (forcé pour PEP 668)
RUN pip install --no-cache-dir --break-system-packages -r /app/requirements.txt

# Copier le script de démarrage et le rendre exécutable
COPY run.sh /run.sh
RUN chmod a+x /run.sh

# Lancement via s6-overlay
CMD [ "/run.sh" ]
