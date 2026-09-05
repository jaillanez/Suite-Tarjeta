# Configuración de producción (§15.1)

Toda la configuración con secretos vive en **un solo archivo fuera del repositorio**:
`config/produccion.env`. Guardando ese archivo (con resguardo) se resuelve la custodia de la clave
de cifrado: no hace falta un gestor de secretos aparte.

## Cómo se completa

```bash
cp config/produccion.env.ejemplo config/produccion.env   # el real está en .gitignore
$EDITOR config/produccion.env                            # completar los valores CAMBIAR/...
```

Generar los secretos de cifrado:

```bash
# clave de cifrado de campos (32 bytes base64 urlsafe)
python3 -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
# pepper
python3 -c "import secrets;print(secrets.token_urlsafe(32))"
# secreto JWT
python3 -c "import secrets;print(secrets.token_urlsafe(48))"
```

## Verificar que no falte nada

```bash
uv run --project apps/api python -m tarjeta.scripts.verificar_config
```

Revisa que estén **todas** las claves requeridas y avisa cuáles faltan o quedaron con el valor de
ejemplo. **No imprime valores** (son secretos). Sale con código ≠ 0 si falta algo.

## Cargar antes de arrancar

```bash
set -a; source config/produccion.env; set +a
uv run --project apps/api uvicorn tarjeta.main:app --host 0.0.0.0 --port 8000
```

Las variables del archivo tienen prefijo `TARJETA_` (backend) y `NEXT_PUBLIC_` (frontend). El
frontend toma `NEXT_PUBLIC_TILES_URL` en tiempo de build.

## Qué contiene

Clave de cifrado de campos y pepper, secreto JWT, cadena de conexión a la base (dos roles) y Redis,
URL y clave del padrón, datos SMTP del correo (§15.2), URL de tiles (§14.1), y la contraseña del
keystore de Android (§15.4). Ver `config/produccion.env.ejemplo` para la lista completa.

## Correo (§15.2)

Con `TARJETA_EMAIL_PROVEEDOR=real` y los cinco datos SMTP (host, puerto, usuario, contraseña,
remitente), el sistema envía por SMTP real. En desarrollo queda el adaptador de consola (escribe el
correo al log). Probar el envío:

```bash
set -a; source config/produccion.env; set +a
uv run --project apps/api python -m tarjeta.scripts.probar_email vos@ejemplo.com
```

> La guarda de arranque en producción (§12.2-D) no cambia: con proveedores en simulación
> (`padron_modo=simulacion`, `email_proveedor=consola`, etc.), la app **no arranca** en `prod`.
