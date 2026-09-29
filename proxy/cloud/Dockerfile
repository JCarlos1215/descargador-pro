FROM ghcr.io/erebe/wstunnel:v11.0.0@sha256:e0714a3b3309f331b72293a08d6e60b5e519b1e21b27380d49679e1c2fde58b5 AS tunnel
FROM python:3.12-slim-trixie
RUN apt-get update && apt-get install -y --no-install-recommends squid ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=tunnel /home/app/wstunnel /usr/local/bin/wstunnel
WORKDIR /app
COPY proxy/cloud/run.py proxy/cloud/squid.conf ./
USER proxy
ENV PORT=8080
EXPOSE 8080
CMD ["python", "run.py"]
