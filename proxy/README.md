# Proxy privado para Descargador Pro

Archivos preparados para un servidor Linux externo con Docker Compose.
**No está desplegado ni probado en un servidor.** No crea una IP, contrata
alojamiento ni garantiza que YouTube acepte la conexión de ese alojamiento.
La página y la conversión de archivos siguen en Render.

Este proxy usa Squid con contraseña, TLS y una lista de IP de clientes
permitidos. Solo permite túneles HTTPS al puerto 443 para YouTube/SoundCloud
y sus dominios de medios. No inspecciona ni descifra el contenido del túnel.

## Requisitos para activarlo

- Un servidor fuera de Render con IP pública y acceso administrativo.
- Un dominio apuntando a ese servidor y un certificado TLS válido para él.
- Los rangos de IP de salida del servicio Render (panel Connect → Outbound).
- Confirmar el coste de tráfico del servidor antes de utilizarlo para videos.

## Preparación en ese servidor

Desde esta carpeta:

```sh
docker compose build
mkdir -p secrets
chmod 700 secrets
# Solicita la contraseña de forma interactiva y guarda solo su hash.
docker run --rm -it --mount "type=bind,src=$PWD/secrets,dst=/secrets" --entrypoint htpasswd descargador-private-proxy:local -cB /secrets/passwords descargador
chmod 644 secrets/passwords
```

Colocar también en `secrets/`:

- `fullchain.pem`: certificado público y cadena completa del dominio.
- `privkey.pem`: su clave privada.
- `allowed-clients.txt`: un rango CIDR de salida de Render por línea.
  No usar `0.0.0.0/0` ni `::/0`.

El directorio del host debe conservar permisos 700; el archivo `passwords`
debe ser legible por el usuario `proxy` del contenedor. Se puede usar modo 644
para ese archivo de hashes, dentro del directorio privado. Mantener la clave
privada con modo 600. Renovar los certificados antes de caducar y reiniciar el
contenedor después de cada renovación.

Permitir en el firewall el puerto TCP 3129 solamente desde los rangos de salida
de Render. Después:

```sh
docker compose up -d
docker compose logs --tail=30
```

Configurar en Render → Environment → `YTDLP_PROXY`:

```text
https://descargador:CONTRASENA_CODIFICADA@DOMINIO_DEL_PROXY:3129
```

Usar el dominio del certificado y codificar los caracteres especiales de la
contraseña para URL. Guardar y desplegar en Render. No subir secretos a GitHub.

## Verificación pendiente en el servidor

Comprobar desde una IP permitida que una conexión sin contraseña da 407 y que
una con contraseña puede abrir un túnel HTTPS. Confirmar que un dominio fuera
de la lista se rechaza. Después probar un MP3 corto desde la página de Render.
Si persisten 429/403, esa conexión también está siendo rechazada por el proveedor.
Para parar el proxy: `docker compose down`.

Referencia: https://wiki.squid-cache.org/ConfigExamples/Authenticate/Ncsa
TLS: https://www.squid-cache.org/Doc/config/https_port/
