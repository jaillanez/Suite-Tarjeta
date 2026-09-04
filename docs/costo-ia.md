# Costo mensual de la generación de imágenes (§11.2)

Es un gasto **recurrente** sobre un presupuesto municipal acotado. Este documento deja la cuenta
hecha y explícita para que alguien la dimensione con el proveedor que se elija. **No elegimos el
proveedor** (ver `GeneradorImagen` y el flag `TARJETA_CONTENIDO_PROVEEDOR`): el precio unitario de
abajo es ilustrativo.

## La cuenta

```
imágenes/mes = comercios adheridos × créditos por mes × variantes por crédito
costo/mes    = imágenes/mes × precio unitario del proveedor
```

- **Comercios adheridos:** se estiman 200 para el arranque.
- **Créditos por mes:** 10 por comercio (parametría, `cuota_ia_mensual_por_comercio`).
- **Variantes por crédito:** `TARJETA_CONTENIDO_VARIANTES_POR_CREDITO`, por defecto **4**.

Con 200 comercios y 4 variantes: `200 × 10 × 4 = 8.000 imágenes/mes`.

## La palanca de costo son las variantes por crédito

Bajar de 4 a 2 variantes **parte el costo al medio** sin sacarle valor real al comercio (igual
elige una). Es el primer dial a mover si el número asusta.

| Variantes/crédito | Imágenes/mes | Costo a US$0,04/img | Costo a US$0,08/img |
|---|---|---|---|
| 4 (por defecto) | 8.000 | US$320 | US$640 |
| 2 | 4.000 | US$160 | US$320 |
| 1 | 2.000 | US$80 | US$160 |

> El precio unitario depende del proveedor y del tamaño de imagen. Al elegir proveedor, reemplazar
> `US$0,04` por el precio real y anotar el resultado acá.

## Lo que baja el costo sin tocar la palanca

- **Foto propia primero (§11.7):** cada pieza hecha con la foto del comercio + plantilla es una
  generación que no se gasta. Es, además, la de mejor calidad promedio.
- **Editor sin crédito (§11.8):** recortar, mover texto, cambiar plantilla, reencuadrar y exportar
  los tres formatos no consumen crédito. Regenerar el fondo sí.
- **Superposición de texto (§11.5):** cambiar el % de la promoción recompone la pieza sin generar.
- **Devolución ante error (§11.9):** una generación fallida del proveedor devuelve el crédito.

## Recordatorio operativo

Cuando se elija proveedor: fijar `TARJETA_CONTENIDO_PROVEEDOR=real`, cargar `..._IA_API_KEY` y
`..._IA_BASE_URL`, definir `..._IA_MODELO`/`..._IA_TAMANO`, y completar `..._IA_PRECIO_UNITARIO_CENTAVOS`
para que el número quede monitoreado. El adaptador real no arranca sin API key.
