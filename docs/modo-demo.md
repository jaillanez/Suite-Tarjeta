# Modo demostración (§13.5)

Un recorrido listo para mostrar el sistema andando a un comerciante o a un funcionario, sin armar
datos cada vez.

```bash
uv run python -m tarjeta.scripts.demo
```

Deja, con un solo comando:

- Un vecino **Black** (DNI `20111222`, contraseña `Back@12345`) y uno **Platino**
  (DNI `27333444`, contraseña `Platino@12`). El resto de los usuarios usa
  `demo-contrasena-123` (o `TARJETA_DEMO_PASSWORD` si se define).
- Un **grupo familiar** (Black titular, Platino miembro, billetera común).
- Un **comercio** ("Comercio Demostración") con **cajero** (DNI `23555666`, PIN `1234`) y **turno
  abierto**.
- **Promociones activas** de distintas mecánicas (porcentaje, 2x1, multiplicador de puntos).
- **Saldo de puntos** con movimientos (una acreditación y un consumo).

**Reiniciable / idempotente:** los ids se derivan por `uuid5`, así que **volver a correrlo
restablece el mismo estado conocido** sin duplicar. Nota: `movimiento_billetera` es append-only e
inmutable para el rol de runtime (§09), por eso "reiniciable" acá significa re-ejecutar hasta el
mismo estado, no borrar el libro. El comercio de la demo queda marcado como precarga, así que
`baja_precarga` también lo retira.
