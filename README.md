# Descargador Pro

Aplicación Flask para descargar un archivo de audio MP3 o video MP4 mediante yt-dlp y FFmpeg.

## Render

Desplegar como servicio Docker usando el Dockerfile incluido. Incluye Python 3.12,
FFmpeg, Deno y yt-dlp con los scripts EJS necesarios para YouTube.
El servidor escucha en `PORT` (10000 por defecto). La ruta de salud es `/health`.

Tras subir los cambios al repositorio conectado, ejecutar un nuevo despliegue.
Si Render conserva dependencias antiguas, reconstruir sin caché.

Las cookies son opcionales: configurar `YTDLP_COOKIE_FILE` con la ruta de un
archivo privado de cookies en formato Netscape (por ejemplo
`/etc/secrets/cookies.txt`). La aplicación no usa el antiguo `cookies.txt` del
repositorio ni lo copia a la imagen. Si ese archivo contiene sesiones reales y
ya se publicó en Git, cerrar esas sesiones y retirar el archivo del historial.
`.gitignore` no elimina archivos previamente versionados.

YouTube puede rechazar la IP del alojamiento o exigir una sesión. Ni una
actualización de yt-dlp ni las cookies garantizan acceso desde Render. La página
muestra el tipo de fallo y los detalles técnicos se registran en el servidor.

## Desarrollo

Instalar Python 3.12+, FFmpeg y Deno 2.3+ disponibles en PATH.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

## Pruebas

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Las pruebas simulan el proveedor externo y verifican validación, respuestas,
archivos MP3/MP4 y limpieza. No certifican el acceso a YouTube desde Render.
