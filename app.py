import os
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, jsonify, render_template, request, send_file
import yt_dlp

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024


@app.get('/')
def index():
    return render_template('index.html')


@app.get('/health')
def health():
    return jsonify({'status': 'ok'})


def download_error(error):
    message = str(error).lower()
    if any(text in message for text in ('not a bot', 'confirm you’re', "confirm you're", 'sign in', 'login required')):
        return 'YouTube solicita iniciar sesión o bloqueó la IP del servidor. El administrador debe revisar las cookies y el acceso desde Render.'
    if '429' in message or 'too many requests' in message:
        return 'El sitio limitó las descargas del servidor. Inténtalo más tarde.'
    if '403' in message:
        return 'El sitio rechazó el acceso desde el servidor (403). Inténtalo más tarde o utiliza otro enlace.'
    if any(text in message for text in ('unavailable', 'private video', 'removed', 'not available')):
        return 'El contenido no está disponible, es privado o tiene restricciones de acceso.'
    if 'unsupported url' in message:
        return 'Este enlace no pertenece a un sitio compatible.'
    return 'No se pudo descargar el contenido. Prueba otro enlace; si persiste, revisa los registros del servidor.'


@app.post('/download')
def download():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='Envía una URL y un formato válidos.'), 400
    url = data.get('url')
    format_type = data.get('format')
    if not isinstance(url, str) or not url.strip():
        return jsonify(error='Por favor ingresa una URL.'), 400
    url = url.strip()
    try:
        parsed = urlsplit(url)
        valid_url = parsed.scheme in ('http', 'https') and bool(parsed.hostname) and not parsed.username
    except ValueError:
        valid_url = False
    if not valid_url:
        return jsonify(error='Ingresa un enlace HTTP o HTTPS válido.'), 400
    if format_type not in ('mp3', 'mp4'):
        return jsonify(error='Selecciona MP3 o MP4.'), 400
    if not shutil.which('ffmpeg'):
        app.logger.error('FFmpeg no está instalado')
        return jsonify(error='Falta FFmpeg en el servidor. El administrador debe actualizar el despliegue.'), 503

    workdir = Path(tempfile.mkdtemp(prefix='descargador-'))
    try:
        options = {
            'outtmpl': str(workdir / 'media.%(ext)s'),
            'noplaylist': True,
            'socket_timeout': 30,
            'retries': 2,
            'js_runtimes': {'deno': {}},
        }
        # A private copy allows yt-dlp to update cookies without modifying a
        # read-only Render secret or sharing a cookie jar between requests.
        cookiefile = os.environ.get('YTDLP_COOKIE_FILE')
        if cookiefile:
            shutil.copyfile(cookiefile, workdir / 'cookies.txt')
            options['cookiefile'] = str(workdir / 'cookies.txt')
        if format_type == 'mp3':
            options.update({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            })
        else:
            options.update({
                'format': 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b',
                'merge_output_format': 'mp4',
                'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
            })
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
        filename = workdir / f'media.{format_type}'
        if not filename.is_file():
            raise RuntimeError('No se generó el archivo final solicitado')
        title = yt_dlp.utils.sanitize_filename((info or {}).get('title') or 'archivo', restricted=True)[:150]
        response = send_file(filename, as_attachment=True, download_name=f'{title}.{format_type}', conditional=False)
        response.headers['Cache-Control'] = 'no-store'
        # Close the file before deleting its directory, after streaming completes.
        response.direct_passthrough = False
        response.call_on_close(lambda: shutil.rmtree(workdir, ignore_errors=True))
        return response
    except yt_dlp.utils.DownloadError as error:
        app.logger.exception('El proveedor rechazó la descarga')
        message, code = download_error(error), 502
    except Exception:
        app.logger.exception('Fallo al procesar la descarga')
        message, code = 'Error interno al procesar la descarga. Revisa los registros del servidor.', 500
    shutil.rmtree(workdir, ignore_errors=True)
    return jsonify(error=message), code


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '10000')))
