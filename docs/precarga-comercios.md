# Precarga de comercios (§13.3)

Para probar el sistema completo con el mapa poblado, se cargan comercios de precarga con su
sucursal y promociones, todos en estado **ACTIVA**.

> **Los datos son sintéticos** (`datos/comercios_rivadavia.yaml`): nombres y teléfonos inventados,
> **no** son negocios reales. La geografía (zonas y coordenadas) sí es de Rivadavia (San Juan) para
> que el mapa se vea realista. Reemplazá el archivo por un relevamiento real cuando lo tengas; el
> comando es idempotente. Cada comercio guarda su **origen** (de dónde salió el dato y cuándo),
> como agenda para el promotor que después los visite.

## Comandos

```bash
# Cargar / actualizar (idempotente: correrlo dos veces no duplica).
uv run python -m tarjeta.scripts.cargar_comercios [ruta_yaml]

# Dar de baja en bloque TODOS los precargados (estado BAJA; dejan de aparecer).
uv run python -m tarjeta.scripts.baja_precarga
```

- Los comercios de precarga llevan la bandera `precarga=true` y quedan `ACTIVA` con promociones
  `ACTIVA`, para poder operar canjes de punta a punta.
- Sus CUIT figuran en `datos/padron.yaml` como `es_comerciante=true`, de modo que la validación
  fiscal pase si alguna vez se los procesa por adhesión.
- **Antes de abrir al público**, dar de baja en bloque los precargados para distinguirlos de los
  comercios que se adhirieron de verdad.

## Formato del YAML

```yaml
comercios:
  - cuit: "30123456781"
    razon_social: "..."
    nombre_fantasia: "..."
    rubro: "kiosco"
    origen: "de dónde salió el dato y cuándo"
    sucursal:
      nombre: "Casa Central"
      direccion: "..., Rivadavia"
      telefono: "..."
      lat: -31.5355
      lon: -68.5990
      horarios: [{ dia: 0, franjas: [{ desde: "09:00", hasta: "13:00" }] }]
    promociones:
      - titulo: "10% en ..."
        mecanica: "PORCENTAJE"   # PORCENTAJE | MONTO_FIJO | DOS_POR_UNO | PRECIO_ESPECIAL | COMBO | MULTIPLICADOR_PUNTOS
        segmento: "AMBOS"        # AMBOS | SOLO_BLACK
        valor_platino: 10        # omitir si SOLO_BLACK
        valor_black: 15
```
