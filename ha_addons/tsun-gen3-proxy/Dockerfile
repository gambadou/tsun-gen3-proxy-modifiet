FROM ghcr.io/home-assistant/aarch64-base:latest

# Installer python3, pip et venv
RUN apk add --no-cache python3 py3-pip python3-venv

# Définir le répertoire de travail
WORKDIR /app

# Copier requirements et ton code
COPY requirements.txt /app/
COPY . /app/

# Créer un virtualenv et installer les dépendances dedans
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Ajouter le venv au PATH pour que python/pip pointent dessus
ENV PATH="/opt/venv/bin:$PATH"

# Commande de lancement
CMD ["python3", "/app/run.py"]
