FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends squid-openssl apache2-utils ca-certificates && rm -rf /var/lib/apt/lists/*
COPY squid.conf /etc/squid/squid.conf
COPY entrypoint.sh /usr/local/bin/proxy-entrypoint
RUN chmod 755 /usr/local/bin/proxy-entrypoint
EXPOSE 3129
ENTRYPOINT ["/usr/local/bin/proxy-entrypoint"]
