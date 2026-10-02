# Descargador Pro

Aplicación Flask para descargar archivos MP3 y MP4 utilizando yt-dlp y FFmpeg.

## Características

- **Descarga directa**: Soporta MP3 y MP4 desde YouTube y otras fuentes.
- **Backend en Flask**: Servidor ligero que gestiona las solicitudes de descarga.
- **Integración yt-dlp**: Extrae metadatos y descarga archivos de manera eficiente.
- **FFmpeg integrado**: Convierte y procesa los archivos descargados si es necesario.
- **Despliegue con Docker**: Arquitectura lista para desplegar en contenedores.
- **Configuración flexible**: Variable `YTDLP_PROXY` para controlar el proxy de red.

## Tecnologías

- **Python 3.12**
- **Flask** (framework web)
- **yt-dlp** (descarga de medios)
- **FFmpeg** (procesamiento de vídeo/audio)
- **Docker** (contenedores)

## Configuración

```sh
# Crear entorno virtual
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Ejecutar la aplicación
.venv/bin/python app.py
```

## Pruebas

```sh
.venv/bin/python -m unittest discover -s tests -v
```

## Despliegue

Desplegar como servicio Docker. El servidor escucha en `PORT` (por defecto 10000) y tiene una ruta de salud `/health`.

## Página Pública

Mantener la URL pública en Render con un proxy privado configurado para `YTDLP_PROXY`.

### Mejoras futuras

- Agregar soporte para más formatos de archivo.
- Implementar interfaz gráfica simple para mejor experiencia de usuario.
- Añadir logging detallado para depuración.
- Optimizar rendimiento con caché de metadatos.
- Documentar más escenarios de uso en la documentación.