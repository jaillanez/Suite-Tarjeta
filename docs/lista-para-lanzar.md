# Tarjeta de Beneficios — Qué falta para lanzar

Estado al cierre del PASO 12 (y trabajo posterior). El desarrollo dejó de ser el cuello de botella:
casi todo lo que queda son decisiones, contrataciones y trámites.

> **Cómo se mantiene este documento (leer antes de tocar código).**
> Este archivo y `docs/estado-funcional.md` se desactualizaron una vez en un solo paso (la matriz
> decía que el QR estaba pendiente cuando ya estaba hecho, y daba a entender que el almacén seguro
> estaba resuelto cuando no). Para que no vuelva a pasar:
> 1. **Ninguna línea sin dueño y sin fecha.** Una línea sin responsable no se cierra sola: queda de
>    adorno hasta que alguien la descubre tarde. Lo que todavía no se decidió se marca **⛔ definir**
>    (a propósito visible), no en blanco.
> 2. **Actualizar los dos documentos es criterio de aceptación, no buena costumbre.** Igual que el
>    lint o la cobertura: antes de mergear. El CI lo exige (job `docs_al_dia`: si cambia código
>    funcional y no cambia `docs/estado-funcional.md`, el PR falla salvo opt-out justificado) y el
>    template de PR lo tiene como casilla. La matriz refleja **cada** cambio funcional; esta lista se
>    revisa cuando cambia el estado de lanzamiento.

---

## 1. Bloqueantes

Sin esto no se puede abrir al público.

| # | Qué falta | Responsable | Fecha objetivo | Estado |
|---|---|---|---|---|
| 1.1 | **Endpoint del padrón municipal.** Sin esto nadie es Black y el programa queda como una app de cupones. El pedido ya está redactado. | Sistemas del municipio | ⛔ definir | Abierto |
| 1.2 | **Infraestructura de producción**: servidor, dominio, certificados, base de datos, backups automáticos. Lo más grande de la lista y nunca se conversó. | ⛔ definir | ⛔ definir | Abierto |
| 1.3 | **Resguardo de la clave de cifrado de campos.** Si se pierde, el DNI y el CUIL de todos los vecinos son irrecuperables aunque el backup esté perfecto. | Municipio (no el equipo de desarrollo) | ⛔ definir | Abierto |
| 1.4 | **Términos y condiciones + política de privacidad.** Hay **borradores v1 cargados** (§13.2, `docs/legal/`) con la nota "no utilizar sin revisión legal"; falta la revisión de Asesoría Letrada. | Asesoría Letrada | ⛔ definir | **Abierto** (borrador listo; falta revisión legal) |
| 1.5 | **Convenio de adhesión del comercio.** Hay **borrador v1 cargado** (§13.2); falta la revisión de Asesoría Letrada. Es el único instrumento que obliga al comercio. | Asesoría Letrada | ⛔ definir | **Abierto** (borrador listo; falta revisión legal) |
| 1.6 | **Cuentas de desarrollador y publicación en tiendas.** La revisión de Apple es externa, tarda y puede rechazar. **Empezar por acá: es la única tarea con un plazo que no controlamos.** | ⛔ definir | ⛔ definir (empezar ya) | Abierto |
| 1.7 | **Archivo de tiles del mapa.** En dev/local ya se ve con el **OSM público** (§13.0). Para **producción** falta pasar a tiles propios (política de OSM): `scripts/generar-tiles.sh` (Java 21+) + hostear + `NEXT_PUBLIC_TILES_URL`. | ⛔ definir (necesita alguien con Java 21) | ⛔ definir | **Abierto** (dev OK con OSM; falta tiles propios para prod) |
| 1.8 | **Recuperación de cuenta.** El flujo está completo (token de un solo uso por email, cierra sesiones); en dev el token va por consola. Falta el **proveedor de email real** (`EMAIL_PROVEEDOR=real`); la guarda de arranque bloquea prod hasta configurarlo. | Equipo del programa (elegir proveedor) | ⛔ definir | **Abierto** (código listo; falta proveedor) |
| 1.9 | **Comercios cargados con promociones activas.** Hay **precarga sintética** (§13.3: 36 comercios, comando idempotente `cargar_comercios`) para probar el sistema; falta el **relevamiento real** (mismo comando, reemplazando el YAML) antes de abrir el registro. | Equipo del programa | ⛔ definir | **Abierto** (precarga de prueba lista; falta relevamiento real) |

---

## 2. Casi bloqueantes

Se puede lanzar sin esto, pero con costo.

| # | Qué falta | Responsable | Fecha objetivo | Estado |
|---|---|---|---|---|
| 2.1 | **Plugin nativo de Keychain/Keystore.** El plugin (`capacitor-secure-storage-plugin`) ya está cableado detrás del seam. Falta **verificarlo en un teléfono real** (`cap:sync` + build nativo): CI no compila el proyecto nativo. | ⛔ definir (QA en dispositivo) | ⛔ definir | **Abierto** (código listo; falta probar en dispositivo) |
| 2.2 | **Quién modera las promociones y con qué tiempo de respuesta.** Sin alguien mirando la cola, el primer comercio que carga una promo espera indefinidamente. | ⛔ definir | ⛔ definir | Abierto |
| 2.3 | **Quién atiende el soporte.** Van a llegar consultas desde el día uno. | ⛔ definir | ⛔ definir | Abierto |
| 2.4 | **Capacitación de comercios.** Un cajero que no sabe usar la caja no aplica el descuento. Diez minutos por comercio. | Equipo del programa | ⛔ definir | Abierto |
| 2.5 | **Tarjetas físicas impresas** (para el vecino sin teléfono). Nadie las mandó a imprimir. | ⛔ definir | ⛔ definir | Abierto |
| 2.6 | **Prueba de la caja en un equipo viejo real.** Pendiente desde el PASO 02. | ⛔ definir | ⛔ definir | Abierto |
| 2.7 | **Prueba de restauración de backup contra la infraestructura real.** La prueba se hizo en la máquina de desarrollo (`docs/restauracion-backup.md`); en producción hay que repetirla. | ⛔ definir | ⛔ definir | Abierto |

---

## 3. No bloqueantes

Se lanza sin esto y se agrega después (post-lanzamiento).

| Qué | Por qué puede esperar | Responsable |
|---|---|---|
| Generación de imágenes con IA | Las plantillas con foto propia dan mejor resultado y no cuestan nada | Municipio (cuando llegue el momento) |
| Publicación en redes sociales | El community manager puede publicar a mano al principio | Equipo del programa |
| Puntos Municipales | La generación está detrás de una bandera apagada, y no hay inventario cargado | Equipo del programa |
| Canje de puntos contra tasas | Requiere ordenanza. No está en agenda | Municipio |
| Módulo de antifraude | Las señales se registran; nada bloquea a nadie | Equipo del programa |
| Módulo de captación | El trabajo se puede llevar en una planilla al principio | Equipo del programa |
| Notificaciones push | La confirmación de canje ya funciona por consulta | Equipo del programa |

---

## 4. Lo que hay que decidir, no construir

| Decisión | Quién | Fecha objetivo |
|---|---|---|
| Proveedor de email para recuperación de cuenta | Equipo del programa | ⛔ definir |
| Dónde se aloja el sistema | Municipio | ⛔ definir |
| Quién custodia la clave de cifrado | Municipio | ⛔ definir |
| Quién genera y mantiene el archivo de tiles | Equipo del programa | ⛔ definir |
| Proveedor de imágenes con IA y su presupuesto mensual | Municipio (cuando llegue el momento) | ⛔ definir |
| Confirmar la marca de la app (hoy "Rivadavia Cumple", logo/colores tomados del sitio oficial del municipio) y proveer el **logo en vector** de alta resolución | Prensa / Comunicación del municipio | ⛔ definir |
| Fecha real de apertura al público | Municipio | ⛔ definir |

---

## 5. Orden sugerido

1. **Cuentas de tiendas y primer envío a revisión.** Es lo único con un plazo que no controlamos.
2. **Pedido del endpoint a Sistemas.** El documento está listo.
3. **Textos legales a Asesoría Letrada.** Tampoco los controlamos nosotros.
4. **Infraestructura de producción.** Es lo más grande y necesita definirse ya.
5. **Tiles, clave de cifrado, recuperación por email.** Las tres tienen la parte de código lista;
   falta correr/hostear (tiles), elegir proveedor (email) y decidir custodia (clave).
6. **Carga de comercios y promociones, y capacitación.** Al final, pero antes de abrir el registro.

---

## 6. Lo que no puede hacer el agente (§14.3)

No depende del equipo de desarrollo en este entorno; queda listado para que se sepa qué falta y de
quién depende.

| Qué | Por qué no lo puede hacer el agente | Quién |
|---|---|---|
| Compilar el APK y el AAB firmado | No hay Android SDK ni gradle en el entorno | Responsable del proyecto, en su máquina |
| Probar el recorrido completo en un teléfono real | No hay dispositivo | Responsable del proyecto |
| Confirmar que los tokens van a Keychain o Keystore | Solo se verifica en dispositivo | Responsable del proyecto |
| Compilar iOS | Requiere Mac con Xcode 27 | Responsable del proyecto (ver decisión abajo) |
| Revisión legal de los tres borradores | No es trabajo de desarrollo | Asesoría Letrada |
| Cuentas de App Store y Google Play | Trámite externo | Responsable del proyecto |

**Herramientas listas para correr en la máquina del responsable (§15.4/§15.5/§15.6):**
`scripts/compilar-android.sh` (APK debug, un comando, con verificación de requisitos),
`scripts/compilar-android-aab.sh` (AAB firmado + keystore), `scripts/verificar-ios.sh` (veredicto
iOS), y los instructivos `docs/compilar-apk.md` y `docs/verificar-keychain.md`. En la Mac del
proyecto ya está el Android SDK; falta **JDK 21** (`brew install --cask temurin@21`) para el APK.

**Decisión sobre iOS (registrada):** **iOS entra en el lanzamiento inicial, junto con Android.** El
responsable cuenta (o contará) con una Mac con Xcode 27; la compilación de iOS queda **pendiente de
ejecutarse en esa máquina** siguiendo `docs/apps-build.md`. No es "Android primero, iOS después":
ambas plataformas van al lanzamiento.

**Almacén seguro (recordatorio):** es el único ítem del PASO 12 que sigue sin cerrar y solo se
verifica en un teléfono. Mientras no se confirme en dispositivo, en la matriz va como **parcial**,
nunca como resuelto.

---

## Observación

Los puntos 1.2, 1.6 y 1.4 nunca se conversaron en todo el proyecto. No son técnicos y no dependen
del equipo de desarrollo, pero cada uno puede frenar el lanzamiento por sí solo. El de las tiendas
es el más peligroso porque tiene un tiempo de espera externo e impredecible.

Y sobre lo que sí es de desarrollo: **los tres ítems de código (1.7 tiles, 1.8 recuperación, 2.1
almacén seguro) están hechos pero ninguno está terminado de verdad.** La recuperación necesita
proveedor de email, el almacén seguro necesita probarse en un teléfono, y los tiles necesitan que
alguien con Java 21 corra el script. Figuran arriba como **Abierto** a propósito: el código deja de
ser la excusa, pero la línea no se cierra hasta que se completa la parte que no es código.
