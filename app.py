import os
import shutil
import tempfile
from collections import deque
from pathlib import Path
from urllib.parse import urlsplit, unquote

from flask import Flask, jsonify, render_template, request, send_file
import yt_dlp
import requests
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC
from mutagen.mp3 import MP3

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024


class DownloadConfigurationError(Exception):
    pass


def configured_proxy():
    proxy = os.environ.get('YTDLP_PROXY', '').strip()
    if not proxy:
        return None
    try:
        parsed = urlsplit(proxy)
        if (parsed.scheme not in ('http', 'https', 'socks5', 'socks5h')
                or not parsed.hostname or not parsed.port
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
            raise ValueError
    except ValueError:
        raise DownloadConfigurationError('Revisa YTDLP_PROXY en Render: usa una URL de proxy con host y puerto.') from None
    return proxy


@app.get('/')
def index():
    return render_template('index.html')


@app.get('/health')
def health():
    return jsonify({'status': 'ok'})


class DownloadLogger:
    """Keep provider warnings per request: the final exception can hide them."""

    def __init__(self, proxy=None):
        self.warnings = deque(maxlen=20)
        self.secrets = []
        if proxy:
            parsed = urlsplit(proxy)
            self.secrets = [proxy, parsed.netloc, parsed.username, parsed.password,
                            unquote(parsed.password or '')]

    def redact(self, message):
        text = str(message)
        for secret in self.secrets:
            if secret:
                text = text.replace(secret, '[redacted]')
        return text

    def debug(self, message):
        app.logger.debug('%s', self.redact(message))

    def warning(self, message):
        message = self.redact(message)
        self.warnings.append(message)
        app.logger.warning('%s', message)

    def error(self, message):
        app.logger.error('%s', self.redact(message))


def download_error(error, warnings=()):
    detail = ' '.join([str(error), *(str(warning) for warning in warnings)]).lower()
    if '407' in detail or 'proxy authentication required' in detail:
        return 'El proxy rechazó la autenticación. Revisa sus credenciales y vuelve a intentar.'
    if '429' in detail or 'too many requests' in detail:
        return 'La plataforma limitó las solicitudes (429). Espera y vuelve a intentar más tarde.'
    if 'sign in to confirm' in detail or 'not a bot' in detail:
        return 'La plataforma exige una verificación para la IP del servidor. Esta descarga no puede continuar.'
    if '403' in detail or 'forbidden' in detail:
        return 'La plataforma rechazó la solicitud (403). Comprueba que el contenido sea público y accesible.'
    return 'No se pudo descargar el contenido. Comprueba el enlace y vuelve a intentar; consulta los registros del servidor si persiste.'


def get_spotify_metadata(url):
    """Extracts track metadata from Spotify API."""
    client_id = os.environ.get('SPOTIFY_CLIENT_ID')
    client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
    if not client_id or not client_secret:
        raise DownloadConfigurationError('Faltan SPOTIFY_CLIENT_ID o SPOTIFY_CLIENT_SECRET en Render.')

    auth_res = requests.post('https://accounts.spotify.com/api/token', 
                             data={'grant_type': 'client_credentials'}, 
                             auth=(client_id, client_secret))
    if auth_res.status_code != 200:
        raise RuntimeError('Error de autenticación con Spotify API')
    token = auth_res.json().get('access_token')

    try:
        item_id = url.split('track/')[1].split('?')[0].split('/')[0]
    except IndexError:
        raise ValueError('El enlace de Spotify no es válido o no es una canción.')

    track_res = requests.get(f'https://api.spotify.com/v1/tracks/{item_id}', 
                             headers={'Authorization': f'Bearer {token}'})
    if track_res.status_code != 200:
        raise RuntimeError('No se pudo obtener la información de la canción desde Spotify')
    
    data = track_res.json()
    return {
        'title': data['name'],
        'artist': data['artists'][0]['name'],
        'album': data['album']['name'],
        'date': data['album'].get('release_date', ''),
        'search_query': f"{data['artists'][0]['name']} - {data['name']} official audio"
    }


def tag_mp3(path, metadata):
    """Applies Spotify metadata to MP3 file."""
    try:
        audio = MP3(path, ID3=ID3)
        try:
            audio.add_tags()
        except:
            pass
        audio.tags.add(TIT2(encoding=3, text=metadata['title']))
        audio.tags.add(TPE1(encoding=3, text=metadata['artist']))
        audio.tags.add(TALB(encoding=3, text=metadata['album']))
        if metadata['date']:
            audio.tags.add(TDRC(encoding=3, text=metadata['date']))
        audio.save()
    except Exception as e:
        app.logger.warning('No se pudieron aplicar etiquetas: %s', e)


@app.post('/download')
def download():
    is_spotify = False
    spotify_meta = None
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
        # Handle Spotify URLs
        if 'open.spotify.com/track/' in url:
            spotify_meta = get_spotify_metadata(url)
            # Search for the track on YouTube instead of using the Spotify URL directly
            url = f"ytsearch1:{spotify_meta['search_query']}"
            is_spotify = True
        else:
            valid_url = parsed.scheme in ('http', 'https') and bool(parsed.hostname) and not parsed.username
            is_spotify = False
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except DownloadConfigurationError as e:
        return jsonify(error=str(e)), 503
    except Exception as e:
        return jsonify(error='Error procesando el enlace de Spotify.'), 400

    if not is_spotify and not valid_url:
        return jsonify(error='Ingresa un enlace HTTP o HTTPS válido.'), 400
    if format_type not in ('mp3', 'mp4'):
        return jsonify(error='Selecciona MP3 o MP4.'), 400
    try:
        proxy = configured_proxy()
    except DownloadConfigurationError as error:
        return jsonify(error=str(error)), 503
    if not shutil.which('ffmpeg'):
        app.logger.error('FFmpeg no está instalado')
        return jsonify(error='Falta FFmpeg en el servidor. El administrador debe actualizar el despliegue.'), 503

    workdir = Path(tempfile.mkdtemp(prefix='descargador-'))
    logger = DownloadLogger(proxy)
    try:
        options = {
            'logger': logger,
            'outtmpl': str(workdir / 'media.%(ext)s'),
            'noplaylist': True,
            'socket_timeout': 30,
            'retries': 3,
            'js_runtimes': {'deno': {}},
        }
        if proxy:
            options['proxy'] = proxy
        
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
            # yt-dlp might name it differently, let's find the file in workdir
            found_files = list(workdir.glob(f'*.{format_type}'))
            if not found_files:
                raise RuntimeError('No se generó el archivo final solicitado')
            filename = found_files[0]

        # If it was a Spotify track and we're exporting as MP3, tag it
        if is_spotify and format_type == 'mp3':
            tag_mp3(filename, spotify_meta)

        title = yt_dlp.utils.sanitize_filename((info or {}).get('title') or 'archivo', restricted=True)[:150]
        response = send_file(filename, as_attachment=True, download_name=f'{title}.{format_type}', conditional=False)
        response.headers['Cache-Control'] = 'no-store'
        # Close the file before deleting its directory, after streaming completes.
        response.direct_passthrough = False
        response.call_on_close(lambda: shutil.rmtree(workdir, ignore_errors=True))
        return response
    except yt_dlp.utils.DownloadError as error:
        app.logger.error('El proveedor rechazó la descarga: %s', logger.redact(error))
        message, code = download_error(logger.redact(error), logger.warnings), 502
    except Exception as error:
        app.logger.error('Fallo al procesar la descarga (%s): %s', type(error).__name__, logger.redact(error))
        message, code = 'Error interno al procesar la descarga. Revisa los registros del servidor.', 500
    shutil.rmtree(workdir, ignore_errors=True)
    return jsonify(error=message), code


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '10000')))
