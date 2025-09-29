#!/usr/bin/env bash
set -e
echo "[INFO] 🚀 Lancement du proxy Tsun Gen3..."
# Activer l'environnement Python de l'add-on
cd /app
# Exécuter ton script principal (à adapter si le nom change)
exec python3 -m src.main