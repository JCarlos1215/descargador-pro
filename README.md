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

## Mantener la página pública en Render con un proxy privado

La URL pública y el procesamiento siguen en Render. La variable opcional
`YTDLP_PROXY` configura la salida de red de yt-dlp para obtener los metadatos y
los archivos. No se acepta un proxy enviado por los visitantes de la página.

1. Disponer de un proxy privado que permita conexiones HTTPS y el tráfico de
   las descargas. Confirmar su cuota y coste de transferencia con el proveedor.
2. En Render → servicio → Environment, añadir `YTDLP_PROXY` con la URL facilitada
   por el proveedor: `http://USUARIO:CONTRASENA@HOST:PUERTO` (ejemplo sin datos
   reales). También se admiten `https`, `socks5` y `socks5h`. Los caracteres
   especiales del usuario y la contraseña deben codificarse para una URL.
3. Guardar y desplegar; probar una descarga MP3 corta desde la página pública.
   Un 407 indica credenciales incorrectas; un 429/403 puede indicar que YouTube
   también rechaza esa salida de red. Un proxy no garantiza acceso.
4. Para desactivar esta configuración, eliminar `YTDLP_PROXY` y desplegar otra vez.

Guardar el valor solamente en Render, nunca en GitHub ni en el navegador de los
visitantes. Esta integración no contrata ni activa ningún proveedor por sí sola.
