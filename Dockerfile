FROM denoland/deno:bin-2.7.5 AS deno
FROM ghcr.io/erebe/wstunnel:v11.0.0@sha256:e0714a3b3309f331b72293a08d6e60b5e519b1e21b27380d49679e1c2fde58b5 AS wstunnel
FROM python:3.12-slim-trixie
COPY --from=wstunnel /home/app/wstunnel /usr/local/bin/wstunnel
COPY --from=deno /deno /usr/local/bin/deno
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py server_start.py ./
COPY templates ./templates
EXPOSE 10000
CMD ["python", "server_start.py"]
