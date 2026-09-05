# Padrón simulado por YAML (§13.1)

Mientras el municipio no entregue el endpoint del padrón, el sistema responde `al_dia` (nivel del
ciudadano) y `es_comerciante` (validación fiscal del comercio) desde un archivo **YAML** que vos
controlás. No hay ninguna regla por paridad de DNI ni heurística: lo que no está en el archivo
devuelve `false`.

## Dónde está y cómo se edita

- Archivo por defecto: `apps/api/datos/padron.yaml` (configurable con `TARJETA_PADRON_SIM_ARCHIVO`).
- Formato:

```yaml
contribuyentes:
  - dni: "20123456"
    al_dia: true      # true => nivel Black; false u omitido => Platino
  - dni: "27987654"
    al_dia: false

comercios:
  - cuit: "30712345678"
    es_comerciante: true

caidos: ["11111111"]  # opcional: DNIs/CUITs que simulan el endpoint caído (para probar degradación)
```

- **Recarga en caliente:** editás el archivo y la **próxima consulta** usa los datos nuevos, sin
  reiniciar la API. Sirve para probar un cambio de nivel en vivo: cambiá `al_dia` y volvé a
  "Actualizar mi estado" en la app.
- Un DNI o CUIT que no figura devuelve `false` (no es error).
- El CUIT se compara por dígitos (los guiones no importan). El DNI, tal cual (sin espacios).

## Cómo se pasa a modo real

El adaptador real (`cliente_real.py`) está intacto y programado contra el contrato del endpoint.
Cuando llegue la URL y la clave, es **sólo configuración** (sin tocar código):

```bash
TARJETA_PADRON_MODO=real
TARJETA_PADRON_BASE_URL=https://padron.rivadavia.gob.ar
TARJETA_PADRON_API_KEY=<clave real>
```

## Guarda de producción (no cambia)

En `environment = prod` con `TARJETA_PADRON_MODO=simulacion`, la aplicación **se niega a arrancar**
(`validar_arranque`, §12.2-D). Es a propósito: nadie llega a producción leyendo el padrón de un
archivo. Para desplegar hay que pasar a modo real.

## Tests

Los tests no usan paridad: cada uno **siembra** en un YAML de prueba los DNIs/CUITs que necesita
(fixture `padron` en `tests/conftest.py`) y la recarga en caliente los toma. Ver ese conftest para
el helper.
