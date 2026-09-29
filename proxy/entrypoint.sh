#!/bin/sh
set -eu
for name in fullchain.pem privkey.pem passwords allowed-clients.txt; do
    if [ ! -s "/run/secrets/$name" ]; then
        echo "Falta el archivo privado requerido: $name" >&2
        exit 1
    fi
done
/usr/sbin/squid -k parse -f /etc/squid/squid.conf
exec /usr/sbin/squid -N -f /etc/squid/squid.conf
