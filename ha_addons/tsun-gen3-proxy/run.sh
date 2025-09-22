#!/usr/bin/with-contenv bashio
set -e

bashio::log.info "Lancement du Tsun Gen3 Proxy..."

python3 -m app.src.main
