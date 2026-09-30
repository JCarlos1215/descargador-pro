# Proxy privado en Railway

Estado: preparado para desplegar; verificar una descarga antes de conectar Render.

Crear un servicio desde este repositorio, con contexto de compilación en la raíz
y `RAILWAY_DOCKERFILE_PATH=proxy/cloud/Dockerfile`. Configurar una clave aleatoria
de 64 caracteres hexadecimales en `WSTUNNEL_RESTRICT_HTTP_UPGRADE_PATH_PREFIX`.
No guardarla en Git. Exponer el puerto 8080 mediante un dominio HTTPS de Railway.

El contenedor corre como usuario `proxy`. Squid solo escucha en loopback;
wstunnel exige la clave y solo puede conectar al puerto local de Squid.
Squid limita los destinos a HTTPS de plataformas públicas compatibles y algunos
CDN explícitos; rechaza redes privadas, puertos no HTTPS y cualquier dominio fuera
de la lista. No es un proxy abierto ni evita verificaciones o restricciones de las
plataformas.
Railway termina TLS; el cliente debe validar el certificado del dominio público.

Después de probar el túnel, configurar Render con:

```
MAC_TUNNEL_URL=wss://DOMINIO.up.railway.app
WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX=LA_MISMA_CLAVE_PRIVADA
YTDLP_PROXY=http://127.0.0.1:13128
```

`MAC_TUNNEL_URL` conserva el nombre por compatibilidad con el cliente existente;
con esta dirección las conexiones salen desde Railway y no desde la Mac.

El plan Free incluye un crédito mensual limitado: no garantiza actividad continua.
No contratar Hobby para este despliegue. El proxy permite HTTPS a YouTube,
SoundCloud, Vimeo, TikTok, Twitch, Dailymotion, Reddit, Facebook, Instagram, X,
Streamable, Rumble, Bandcamp, Mixcloud, Archive.org, Kick y Odysee, incluidos
dominios CDN conocidos. Las plataformas pueden seguir rechazando solicitudes;
el proxy no elude verificaciones ni restricciones.
