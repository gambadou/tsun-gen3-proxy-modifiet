FROM ghcr.io/home-assistant/aarch64-base:latest

# Installer Python + pip + bash + npm (pour bashio)
RUN apk add --no-cache python3 py3-pip bash nodejs npm

# Installer bashio via npm
RUN npm install -g bashio

WORKDIR /app

COPY requirements.txt /app/
COPY . /app/

# Installer les dépendances Python
RUN pip install --no-cache-dir --break-system-packages -r /app/requirements.txt

# Copier le script de démarrage et le rendre exécutable
COPY run.sh /run.sh
RUN chmod a+x /run.sh

# Le point d’entrée
CMD [ "/run.sh" ]
