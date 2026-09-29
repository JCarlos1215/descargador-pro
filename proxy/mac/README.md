# Proxy en la Mac

Requiere `brew install squid wstunnel cloudflared`. Ejecutar `Iniciar.command`
con doble clic o desde Terminal. Mantener esa ventana abierta y la Mac encendida.
Para detenerlo, pulsar Ctrl+C en esa ventana. No se instala un servicio de inicio
ni se abren puertos del router. `caffeinate -i` evita el reposo por inactividad
mientras está ejecutándose; no garantiza funcionamiento con la tapa cerrada.

Squid escucha solamente en `127.0.0.1:13128` y permite túneles HTTPS al puerto
443 de YouTube/SoundCloud y sus dominios de medios. Wstunnel escucha solamente
en `127.0.0.1:18080`, exige una clave aleatoria de 256 bits y únicamente puede
conectarse al Squid local. Cloudflared publica el transporte WebSocket cifrado.
No hay un proxy abierto a Internet sin autenticación.

La carpeta `runtime/` contiene la clave y los registros; es privada y está
excluida de Git. Nunca subir su contenido a GitHub. La clave del túnel no debe
compartirse con usuarios de la página pública.

## Conectar Render

El Dockerfile incluye el cliente de wstunnel. En Render → Environment, importar
`runtime/render.env`, guardar y desplegar. Al configurar `MAC_TUNNEL_URL`, el
servidor usa automáticamente su cliente local como `YTDLP_PROXY`.

El túnel Quick Tunnel es gratuito, experimental y no tiene garantía de
continuidad. Su dirección cambia cada vez que se inicia de nuevo; en ese caso
actualizar `MAC_TUNNEL_URL` con el archivo `runtime/render.env` regenerado y
volver a desplegar. Para una dirección estable se necesita un túnel con nombre
asociado a una cuenta/dominio, que no se configura aquí.

## Comprobaciones

`python3 proxy/mac/check_tunnel.py` valida el túnel público con una clave válida
e inválida. No imprime la clave. La prueba positiva consulta robots.txt de
YouTube; para validar descargas hay que probar también un enlace de contenido.

Si se desconecta la Mac, Render permanece público pero las descargas que usan
el túnel fallarán. Eliminar `MAC_TUNNEL_URL`, `WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX`
y `YTDLP_PROXY` de Render permite volver a la conexión directa anterior.
