# Tarjeta de Beneficios Municipal — Rivadavia
## Especificación funcional detallada · v2.0 — para revisión

**Decisiones tomadas:**
- **Financiamiento:** el comercio absorbe el 100% del descuento. El municipio no aporta caja.
- **Verificación municipal:** endpoint que devuelve si la persona es contribuyente, si está al día, y si el CUIT está inscripto como comercio. Sin montos, cuotas ni vencimientos.
- **Aplicaciones:** una sola app, una sola publicación, tres perfiles (ciudadano, comercio, municipal) + portales web complementarios.
- **Descuentos:** el comercio fija libremente el porcentaje. Sin mínimo ni máximo.

---

# PARTE 0 — Consecuencias de las decisiones

## 0.1 El comercio absorbe: qué implica realmente

Esto cambia el centro de gravedad del proyecto. Si el municipio no pone plata, **el producto no se vende solo: hay que salir a conseguir comercios uno por uno**. El riesgo número uno del proyecto pasa a ser una app hermosa con 12 comercios adheridos y ningún ciudadano usándola.

Consecuencias directas:

| Consecuencia | Qué hay que construir |
|---|---|
| El comercio necesita ver retorno o se va | **M2.7 Reportes con valor real** (clientes nuevos, ticket promedio, benchmark de rubro). No es un "nice to have": es lo que evita la baja. |
| Hay que captar comercios activamente | **M7 — Módulo de Captación** (embudo, promotores, metas). No estaba en el pedido original; lo agrego. |
| El comercio puede inflar precios antes de dar el descuento | **M6.4 Control de precio de referencia** + calificación ciudadana post-canje. |
| Riesgo de arranque en frío (chicken-and-egg) | Resuelto: los grandes comercios ya confirmaron su adhesión. Ver §12.2. |
| El municipio necesita algo que dar a cambio | **Inventario municipal de beneficios** (§0.2) y visibilidad en canales oficiales. |

## 0.2 Las dos monedas: separación obligatoria

Un solo tipo de punto no funciona en este modelo. Propongo dos monedas con financiamiento distinto y libros contables separados:

### Puntos Comercio (PC)
- **Financia:** el comercio.
- **Se generan:** cuando el comercio elige dar parte del beneficio en puntos en vez de descuento inmediato (ej: "10% off" o "5% off + 10% en puntos").
- **Se canjean:** **circuito cerrado por comercio.** Los puntos que emite un comercio se canjean únicamente en ese mismo comercio (en cualquiera de sus sucursales). Decidido.
- **Por qué:** cero riesgo contable, cero compensación entre privados, y sigue cumpliendo la función de fidelizar. Una bolsa común entre comercios exigiría una cámara compensadora, que es un sistema financiero en sí mismo. Queda como posible evolución futura, no en agenda.
- **Vencimiento:** 24 meses rodantes.

### Puntos Municipales (PM)
- **Financia:** el municipio, pero **con inventario propio de costo marginal casi nulo**, no con caja.
- **Se generan por conductas que al municipio le sirven:**
  - Pago anticipado o al día de tasas
  - Adhesión a débito automático / boleta digital
  - Referir vecinos que se registren y usen
  - Participación en campañas municipales, encuestas, censos
  - Denuncia de problemas urbanos vía app (baches, luminarias) verificada
- **Se canjean contra inventario municipal:**
  - Entradas a eventos, teatro, anfiteatro
  - Cupos en colonia de vacaciones, escuelas deportivas, talleres culturales
  - Horas de estacionamiento medido
  - Uso de instalaciones deportivas
  - Prioridad o exención de costo en trámites no arancelados
- **Canje contra tasas municipales:** el motor queda **preparado pero apagado por feature flag**. No está en agenda: requiere una ordenanza del Concejo Deliberante, que es un camino largo. Se deja previsto para no tener que reescribir después.

> Ambas monedas se muestran al ciudadano en billeteras visualmente distintas. Nunca se mezclan ni se convierten entre sí.

## 0.3 Qué gana el comercio (la propuesta de valor a vender)

Hay que poder decirlo en 30 segundos en un mostrador:

1. Acceso a una base de ~X mil vecinos con la app instalada, gratis.
2. Publicación en las redes oficiales del municipio (alcance que no puede comprar).
3. Herramienta de diseño con IA gratis: dicta la idea, sale la placa lista para publicar.
4. Estadísticas de su propio negocio que hoy no tiene.
5. Sello físico para vidriera y presencia en el mapa oficial.
6. Trato prioritario en trámites municipales (a definir con el municipio — es el incentivo más barato y más potente que existe).

**El comercio decide libremente el % que da. El municipio no fija mínimos ni máximos.** Solo ordena la vidriera por atractivo, novedad y cercanía.

---

# PARTE 1 — Modelo de datos detallado

## 1.1 Identidad

```
Persona
  id_persona (UUID)
  dni, cuil (único, indexado)
  apellido, nombre
  fecha_nacimiento, sexo
  email, celular (verificados: bool)
  domicilio {calle, nro, piso, depto, barrio, localidad, cp, lat, lng}
  estado_identidad: PENDIENTE | VERIFICADA | RECHAZADA | SUSPENDIDA
  metodo_verificacion: RENAPER | PRESENCIAL | DOCUMENTAL
  fecha_alta, fecha_ultima_actividad
  consentimientos[] {tipo, version_TyC, fecha, ip}
  
  → PerfilCiudadano (0..1)
  → PerfilComercio (0..N)   // una persona puede ser cajero de 2 comercios
  → PerfilMunicipal (0..1)
```

Una sola credencial de acceso. Al iniciar sesión, si la persona tiene más de un perfil, se le pregunta con cuál entra (selector de contexto tipo "workspace").

## 1.2 Ciudadano y niveles

```
PerfilCiudadano
  id_persona
  nivel_actual: GENERAL | BLACK
  nivel_origen: PROPIO | HEREDADO_GRUPO
  fecha_ultimo_calculo_nivel
  proxima_revision_nivel
  numero_tarjeta (16 dígitos, generado)
  estado_tarjeta: ACTIVA | BLOQUEADA | SUSPENDIDA | BAJA
  tiene_tarjeta_fisica: bool
  → BilleteraPC (individual)
  → BilleteraPM (individual)
  → MembresiaGrupo (0..1)

HistorialNivel        // append-only, auditable
  id_persona, nivel_anterior, nivel_nuevo
  motivo: CALCULO_AUTOMATICO | ALTA_GRUPO | BAJA_GRUPO | SANCION | AJUSTE_MANUAL
  detalle_regla_aplicada (snapshot de la regla vigente)
  usuario_responsable (si fue manual)
  timestamp
```

**Regla dura:** el nivel nunca se edita a mano directamente. Un agente municipal puede crear una *excepción* con vigencia y motivo, y el motor la respeta; pero el cálculo base sigue corriendo. Esto evita el clásico "me lo cambió alguien y no sabemos por qué".

## 1.3 Contribuyente (espejo del padrón)

La tarjeta **no replica el padrón**. Solo cachea el veredicto que devuelve el endpoint municipal.

```
EstadoPadron           // cache del endpoint, uno por persona
  cuil (clave de cruce con Persona)
  es_contribuyente: bool
  al_dia: bool
  es_comerciante: bool
  cuit_comercio (si aplica)
  fecha_corte              // del dato, informada por el municipio
  fecha_ultima_consulta    // cuándo lo consultamos nosotros

HistorialEstadoPadron  // append-only — habilita la métrica de recaudación
  cuil, campo, valor_anterior, valor_nuevo
  fecha_corte, timestamp
  origen_consulta: BATCH | BOTON_USUARIO | ALTA_PRESENCIAL
```

**No se almacenan montos, cuentas, cuotas, vencimientos ni deuda.** Ver §7.5.

## 1.4 Grupo familiar

```
GrupoFamiliar
  id_grupo
  id_titular (debe tener PerfilCiudadano con nivel_origen = PROPIO)
  nombre_grupo (editable, ej: "Familia Gómez")
  modo_billetera: COMUN | INDIVIDUAL
  fecha_creacion, fecha_ultimo_cambio_modo
  estado: ACTIVO | SUSPENDIDO | DISUELTO
  → BilleteraComunPC, BilleteraComunPM (solo si modo = COMUN)

MembresiaGrupo
  id_grupo, id_persona
  rol: TITULAR | MIEMBRO
  vinculo_declarado: CONYUGE | HIJO | PADRE_MADRE | HERMANO | OTRO
  estado: INVITADO | ACTIVO | SUSPENDIDO | RETIRADO
  fecha_invitacion, fecha_aceptacion, fecha_baja
  tope_mensual_puntos (opcional, lo fija el titular)
  puede_canjear: bool
  cooldown_hasta (fecha)     // no puede unirse a otro grupo antes de esto
```

## 1.5 Comercio

```
Comercio
  id_comercio, cuit (único)
  razon_social, nombre_fantasia
  rubro_principal, rubros_secundarios[]
  logo, descripcion, sitio_web, redes[]
  inscripto_en_municipio: bool     // verificado contra el endpoint (§7.1)
  fecha_verificacion_inscripcion
  estado_adhesion: SOLICITADA | EN_REVISION | DOCUMENTACION_PENDIENTE |
                   APROBADA | ACTIVA | SUSPENDIDA | BAJA | RECHAZADA
  nivel_confianza: NUEVO | ESTABLECIDO | VERIFICADO   // define moderación
  descuento_base_declarado (%)
  fecha_adhesion, fecha_baja, motivo_baja
  puntaje_ciudadano (promedio, 1..5)
  cuota_ia_mensual, cuota_ia_consumida

Sucursal
  id_sucursal, id_comercio
  nombre (ej: "Sucursal Centro")
  es_casa_central: bool
  direccion completa + lat/lng (pin obligatorio en mapa)
  telefono, whatsapp
  horarios[] {dia_semana, apertura, cierre, apertura2, cierre2}
  feriados_cerrado: bool
  medios_pago[], accesibilidad{rampa, bano_adaptado, estacionamiento}
  fotos[]
  qr_establecimiento (token permanente firmado)
  estado: ACTIVA | SUSPENDIDA | CERRADA_TEMPORAL | CERRADA_DEFINITIVA
  motivo_cierre, fecha_reapertura_estimada

UsuarioComercio
  id_persona, id_comercio
  rol: ADMIN_COMERCIO | ADMIN_SUCURSALES | ENCARGADO | CAJERO
  sucursales_asignadas[]      // vacío = todas, solo válido para ADMIN_COMERCIO
  permisos_extra[]            // ej: ENCARGADO con permiso de crear promos
  pin_caja (hash, solo CAJERO/ENCARGADO)
  dispositivos_autorizados[]
  estado: INVITADO | ACTIVO | SUSPENDIDO | BAJA
  ultimo_acceso
```

## 1.6 Promociones

```
Promocion
  id_promocion, id_comercio
  titulo (máx 60 car.), descripcion (máx 500)
  letra_chica / condiciones
  mecanica: PORCENTAJE | MONTO_FIJO | 2X1 | PRECIO_ESPECIAL |
            PUNTOS_MULTIPLICADOR | CUPON_UNICO | COMBO
  valor_general (%, $ o multiplicador)
  valor_black
  aplica_a: TODO_EL_LOCAL | CATEGORIA | PRODUCTO_ESPECIFICO
  reparto_beneficio {pct_descuento_inmediato, pct_en_puntos}
  sucursales[]                // todas o selección
  segmento: GENERAL | BLACK | AMBOS
  vigencia_desde, vigencia_hasta
  dias_semana[], franja_horaria{desde, hasta}
  tope_usos_total, tope_usos_por_usuario, tope_usos_por_dia
  usos_actuales
  monto_minimo_compra, monto_maximo_descuento
  acumulable_con_otras: bool
  creatividades[] {url, formato, origen: SUBIDA|IA, prompt_usado, moderada}
  estado: BORRADOR | EN_REVISION | APROBADA | ACTIVA |
          PAUSADA | AGOTADA | VENCIDA | RECHAZADA
  motivo_rechazo
  destacada_por_municipio: bool
  id_campania (opcional)
```

## 1.7 Transacción y billetera

```
Transaccion
  id_transaccion (UUID), nro_comprobante (legible: RIV-000123456)
  id_persona, id_sucursal, id_usuario_cajero, id_promocion
  nivel_ciudadano_al_momento
  monto_bruto, descuento_aplicado, monto_neto
  pc_generados, pc_consumidos, pm_generados, pm_consumidos
  origen_puntos: INDIVIDUAL | GRUPO_COMUN
  metodo_validacion: QR_DINAMICO | QR_COMERCIO | CODIGO_6D | TARJETA_FISICA
  geo_validacion {lat, lng, distancia_a_sucursal_m}
  estado: CONFIRMADA | ANULADA | EN_DISPUTA | PENDIENTE_SYNC
  timestamp_cliente, timestamp_servidor
  hash_idempotencia
  calificacion_ciudadano (1..5, opcional)

MovimientoBilletera        // append-only, nunca se edita ni borra
  id_movimiento, id_billetera, moneda: PC | PM
  tipo: ACREDITACION | CONSUMO | VENCIMIENTO | AJUSTE_MANUAL |
        REVERSO | TRANSFERENCIA_INTERNA
  monto (signo), saldo_resultante
  id_transaccion_origen
  fecha_vencimiento_lote     // FIFO por lote
  usuario_responsable, motivo (obligatorio si AJUSTE_MANUAL)
  timestamp
```

**Regla contable:** los puntos se acreditan por lotes con vencimiento propio y se consumen **FIFO** (vence primero el lote más viejo). Esto evita el reclamo de "me vencieron puntos que había ganado ayer".

---

# PARTE 2 — Roles y matriz de permisos

## 2.1 Matriz de comercio

| Acción | Admin Comercio | Admin Sucursales | Encargado | Cajero |
|---|:---:|:---:|:---:|:---:|
| Editar datos del comercio | ✅ | ❌ | ❌ | ❌ |
| Crear/editar sucursal | ✅ | ✅ (asignadas) | ❌ | ❌ |
| Suspender sucursal | ✅ | ✅ (asignadas) | ❌ | ❌ |
| Invitar Admin de Sucursales | ✅ | ❌ | ❌ | ❌ |
| Invitar Encargado | ✅ | ✅ | ❌ | ❌ |
| Invitar/dar de baja Cajero | ✅ | ✅ | ✅ | ❌ |
| Crear promoción | ✅ | ✅ | ⚙️ con permiso | ❌ |
| Pausar promoción | ✅ | ✅ | ✅ (su sucursal) | ❌ |
| Generar imagen con IA | ✅ | ✅ | ⚙️ con permiso | ❌ |
| Publicar en redes propias | ✅ | ⚙️ | ❌ | ❌ |
| Validar canje en caja | ✅ | ✅ | ✅ | ✅ |
| Anular canje (ventana 15 min) | ✅ | ✅ | ✅ | ✅ propia |
| Anular fuera de ventana | ✅ | ❌ | ❌ | ❌ |
| Ver reportes globales | ✅ | ❌ | ❌ | ❌ |
| Ver reportes de sucursal | ✅ | ✅ (asignadas) | ✅ (propia) | ❌ |
| Ver datos de contacto del ciudadano | ❌ | ❌ | ❌ | ❌ |
| Cierre de caja | ✅ | ✅ | ✅ | ✅ propia |
| Solicitar baja del programa | ✅ | ❌ | ❌ | ❌ |

**Ningún rol de comercio, en ningún nivel, accede a datos de contacto, domicilio o estado fiscal del ciudadano.** El cajero ve: nombre de pila, inicial del apellido, nivel, foto (opcional) y promociones aplicables. Nada más.

## 2.2 Matriz municipal

| Acción | Super Admin | Administrador | Encargado | Personal | Auditor |
|---|:---:|:---:|:---:|:---:|:---:|
| Parametría del sistema | ✅ | ❌ | ❌ | ❌ | 👁️ |
| Reglas de nivel Black | ✅ | 🔒 doble conf. | ❌ | ❌ | 👁️ |
| Gestión de roles municipales | ✅ | ✅ (inferiores) | ❌ | ❌ | 👁️ |
| Aprobar adhesión de comercio | ✅ | ✅ | ✅ | ❌ | 👁️ |
| Rechazar adhesión | ✅ | ✅ | ✅ | ❌ | 👁️ |
| Suspender comercio | ✅ | ✅ | ✅ | ❌ | 👁️ |
| Baja definitiva de comercio | ✅ | 🔒 doble conf. | ❌ | ❌ | 👁️ |
| Alta manual de ciudadano | ✅ | ✅ | ✅ | ✅ | 👁️ |
| Suspender ciudadano | ✅ | ✅ | ✅ | ❌ | 👁️ |
| Ajuste manual de puntos | ✅ | ✅ hasta tope | ✅ tope bajo | ❌ | 👁️ |
| Moderar promociones/imágenes | ✅ | ✅ | ✅ | ✅ | 👁️ |
| Crear campaña municipal | ✅ | ✅ | ❌ | ❌ | 👁️ |
| Publicar en redes oficiales | ✅ | ✅ | ✅ | ⚙️ | 👁️ |
| Ver tablero de gobierno | ✅ | ✅ | ✅ parcial | ❌ | ✅ |
| Ver ficha 360 de ciudadano | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ver logs de auditoría | ✅ | ✅ | ❌ | ❌ | ✅ |
| Exportar datos personales masivo | 🔒 doble conf. | ❌ | ❌ | ❌ | ❌ |

🔒 = requiere aprobación de un segundo usuario con rol igual o superior. 👁️ = solo lectura. ⚙️ = configurable por permiso adicional.

**Doble conformidad:** la acción queda en estado PENDIENTE_APROBACION, se notifica a los habilitados, y expira a las 72 h sin aprobar. El solicitante no puede aprobar su propia solicitud.

---

# PARTE 3 — M1 · Módulo Ciudadano

## 3.1 Registro y verificación de identidad

**Flujo:**
1. Ingreso de DNI + CUIL + fecha de nacimiento + sexo.
2. Consulta a padrón: ¿existe como contribuyente titular?
3. Verificación de identidad — tres caminos:
   - **RENAPER** (ideal): validación de datos + prueba de vida por selfie.
   - **Documental**: foto frente y dorso del DNI + selfie, con revisión humana si el score es bajo.
   - **Presencial**: el vecino va al municipio, el personal valida y activa la cuenta.
4. Verificación de celular por OTP (obligatoria) y email (opcional).
5. Creación de contraseña + biometría en el dispositivo.
6. Aceptación de TyC y consentimientos **granulares y separados**:
   - Tratamiento de datos para operar el programa (obligatorio)
   - Comunicaciones comerciales (opcional)
   - Geolocalización para beneficios cercanos (opcional)
   - Uso de datos agregados y anonimizados para estadística municipal (opcional)
7. Cálculo inicial de nivel.
8. Emisión de tarjeta digital.

**Criterios de aceptación:**
- [ ] Un DNI ya registrado no puede registrarse de nuevo; ofrece recuperar cuenta.
- [ ] Una cuenta sin verificar puede navegar beneficios pero **no canjear**.
- [ ] El rechazo de identidad indica motivo y ofrece la vía presencial.
- [ ] Los consentimientos se guardan con versión de TyC, fecha e IP.
- [ ] Rechazar los consentimientos opcionales no impide usar el programa.

## 3.2 Motor de nivel: General vs Black

**Regla base:**

```
Es BLACK si:  el endpoint devuelve contribuyente = true  Y  al_dia = true
              (o hereda el nivel por pertenecer a un grupo familiar)

La tarjeta consume el booleano. No conoce cuotas, montos, cuentas ni vencimientos.
No se investiga ni se replica el criterio de Hacienda.

Recálculo: batch nocturno + botón "Actualizar mi estado" (máx. 3/día).
```

**Casos borde:**

| Caso | Tratamiento |
|---|---|
| No figura en el padrón (inquilino, joven) | GENERAL. Puede subir a Black solo por grupo familiar. |
| Figura y no está al día | GENERAL. |
| Titular fallecido / sucesión | Congelar nivel 180 días, marcar para revisión manual. |
| Baja de nivel a mitad de una compra | El nivel se congela al emitir el token de canje. No se le cambia el precio al vecino en la caja. |

**Pantalla "Mi estado":**

| Escenario | Qué muestra |
|---|---|
| Contribuyente al día | Nivel Black destacado. "Estás al día con el municipio. Por eso accedés a los mejores beneficios." |
| Contribuyente no al día | Nivel General. "Regularizando tu situación con el municipio pasás a Black y accedés a X beneficios más." Botón → portal de pagos municipal. |
| No figura como contribuyente | Nivel General. "No figurás como contribuyente municipal. Si un familiar contribuyente te suma a su grupo, accedés a los beneficios Black." → link a Grupo Familiar. |

- La app **nunca muestra montos, cuentas ni detalle de deuda.** No los tiene y no los pide.
- Fecha de corte del dato siempre visible.
- Botón "Actualizar mi estado", máx. 3 usos por día.
- Contador de beneficios bloqueados: el número concreto de promociones que se está perdiendo. Es el gancho de conversión.

> El tercer escenario es el que obliga a que el endpoint distinga "no figura en el padrón" de "figura y no está al día". Si devuelve un solo booleano, la app le va a decir "tenés deuda" a un inquilino que no debe nada. No es una pregunta sobre cuotas: es evitar un mensaje falso.

## 3.3 Grupo familiar

**Creación:**
- Solo puede crear grupo quien tenga `nivel_origen = PROPIO` (es decir, es contribuyente titular). Un usuario que ya es Black heredado no puede crear otro grupo.
- Se define nombre del grupo y **modo de billetera**.

**Invitación:**
- Por DNI o por link con vencimiento a 7 días.
- El invitado recibe notificación y **debe aceptar explícitamente**, viendo qué implica (hereda nivel, comparte fondo si es común, el titular ve su consumo).
- Un invitado que ya pertenece a otro grupo debe salir primero, y le aplica cooldown.

**Reglas antifraude (críticas):**

| Regla | Valor definido |
|---|---|
| Máximo de miembros | 6 (titular incluido) |
| Una persona, un grupo | Sí, excluyente |
| Permanencia mínima antes de poder salir | **Sin mínimo.** Se puede salir cuando se quiera. |
| Cooldown para unirse a otro grupo tras salir | 90 días |
| Cambios de composición por año | Máx. 4 altas y 4 bajas |
| Cambio de modo de billetera | Máx. 1 cada 180 días |
| Alerta automática | Grupo con 3+ miembros de apellidos todos distintos y domicilios en 3+ barrios → revisión |
| Validación de vínculo | **Sin verificación documental.** El titular declara el vínculo y es el responsable de la veracidad. |

**Sobre la combinación "sin permanencia mínima + cooldown de 90 días":** funciona bien y es mejor que exigir permanencia. Nadie queda atrapado en un grupo del que quiere salir —importante en separaciones o conflictos familiares— pero tampoco puede saltar de grupo en grupo, porque después de salir tiene que esperar 90 días para entrar a otro. El límite al abuso se mantiene sin encerrar a nadie.

**Sobre la responsabilidad del titular:** al no haber verificación documental, el peso recae sobre la declaración del titular. Eso exige tres cosas:
- Texto explícito en el momento de invitar: *"Declarás que esta persona integra tu grupo familiar. Sos responsable de lo que declarás."* Con aceptación registrada, fecha e IP.
- Cláusula en los TyC que habilite la suspensión del titular y de todo su grupo ante una declaración falsa comprobada.
- Las alertas antifraude (§8.2) pasan a ser la única red de contención real, así que no pueden quedar sin monitorear.

El techo del abuso igual está acotado: 6 miembros como máximo, 4 altas por año y cooldown de 90 días. Un titular no puede repartir el nivel Black a mucha gente aunque quiera.

**Modo COMÚN vs INDIVIDUAL:**

- **COMÚN:** todos los canjes suman al pozo del grupo; cualquiera puede gastar del pozo (salvo que el titular restrinja). El titular puede fijar tope mensual por miembro.
- **INDIVIDUAL:** cada uno acumula y gasta lo suyo. El grupo sirve solo para heredar el nivel.
- **Al cambiar de COMÚN a INDIVIDUAL:** el saldo del pozo **queda en el titular**. Decidido. Debe estar explícito en los TyC y avisarse antes de confirmar el cambio.
- **Al salir del grupo:** los puntos individuales viajan con la persona; los del pozo quedan en el grupo. Se avisa antes de confirmar la baja.

**Panel del titular:**
- Miembros, estado, consumo por miembro del mes, tope asignado.
- Suspender temporalmente a un miembro (ej: adolescente que gastó todo).
- Disolver el grupo (con confirmación fuerte y aviso a todos).

## 3.4 Tarjeta digital y validación

**QR dinámico:**
- Token firmado (JWT corto) que rota cada **45 segundos**.
- Contiene: id_ciudadano, nivel congelado, timestamp, nonce, firma.
- Validez del token: 90 segundos (tolerancia de reloj).
- Un token consumido no puede reutilizarse (registro de nonces).
- Funciona sin conexión del lado del ciudadano: la app puede pregenerar tokens para las próximas 2 horas.

**Cuatro vías de validación, en orden de preferencia:**

| Vía | Cuándo se usa | Seguridad |
|---|---|---|
| 1. Cajero escanea QR del ciudadano | Caso normal | Alta |
| 2. Ciudadano escanea QR de la sucursal | Comercio sin lector | Alta (geo + token de sucursal) |
| 3. Código de 6 dígitos | Sin internet en el comercio | Media — límite de monto |
| 4. Tarjeta física + DNI | Adulto mayor, sin smartphone | Media — el cajero valida identidad |

**Tarjeta física:** no es un extra opcional. En un municipio, dejar afuera a quien no tiene smartphone es un problema político antes que de producto. Emisión gratuita a demanda en el municipio, con QR impreso + número. El vecino la usa mostrándola con DNI.

## 3.5 Descubrimiento de beneficios

**Home / Feed:**
Secciones ordenadas por relevancia calculada:
1. "Cerca tuyo ahora" (si dio permiso de ubicación y está en horario)
2. "Nuevos esta semana"
3. "Exclusivos Black" (si es General, se muestran **bloqueados con el % visible** — es el gancho de conversión fiscal)
4. "De tus favoritos"
5. "Vencen pronto"
6. Campaña municipal vigente (si hay)

**Buscador y filtros:** rubro, texto libre, % mínimo, distancia, abierto ahora, acepta puntos, solo Black.

**Mapa:**
- Pines agrupados por zona, con color por rubro.
- Filtros persistentes.
- Ficha rápida al tocar el pin: nombre, distancia, mejor promo, horario, calificación.
- "Cómo llegar" → deep link a Google/Apple Maps.
- Modo lista alternativo ordenado por distancia.

**Ordenamiento — regla de transparencia:** en un programa público el ranking no puede ser una caja negra ni venderse. El criterio se publica: relevancia = f(distancia, nivel de descuento, novedad, calificación ciudadana, destaque municipal explícito). Los destaques municipales se marcan visualmente como tales.

**Ficha de promoción:**
- Imagen, título, % para tu nivel (y el % Black si sos General, tachado y bloqueado)
- Condiciones y letra chica completa
- Vigencia, días y horarios
- Sucursales adheridas con distancia
- Usos restantes (si hay tope)
- Botón guardar / compartir / cómo llegar

## 3.6 Canje

**Flujo normal:**
1. Ciudadano abre "Mi tarjeta" → QR dinámico.
2. Cajero escanea → la app del comercio muestra nombre, nivel y promos aplicables.
3. Cajero ingresa monto de la compra y selecciona promoción.
4. **El ciudadano recibe una notificación de confirmación en su celular** con el detalle: comercio, monto, descuento, puntos. Debe aceptar.
5. Confirmado → comprobante digital para ambos.

El paso 4 es lo que evita el fraude más común: el cajero que "quema" beneficios de clientes sin que se enteren.

**Resolución de promociones concurrentes:** si aplican varias, el motor propone la de **mayor beneficio para el ciudadano** por defecto, pero el cajero puede elegir otra si el cliente lo pide. Nunca se aplican dos, salvo que ambas estén marcadas `acumulable_con_otras`.

**Anulación:** ventana de 15 minutos, con motivo, reversa puntos y descuento. Fuera de la ventana, solo el Admin de Comercio, y genera notificación al ciudadano y al municipio.

**Disputa:** botón "Esto no está bien" en cada comprobante, abre un caso con el municipio como árbitro.

## 3.7 Billetera

- Dos tarjetas visuales separadas: **Puntos Comercio** y **Puntos Municipales**.
- Si pertenece a grupo COMÚN: tercera vista del pozo familiar, con quién aportó y quién gastó.
- Movimientos con filtro y buscador.
- Detalle de lotes por vencer, con aviso a 30 y 7 días.
- Catálogo de canje PM (inventario municipal) con stock y reserva de cupo.
- Canje PC dentro de cada comercio emisor.

## 3.8 Perfil, privacidad y accesibilidad

- Datos personales, domicilio, contacto.
- Preferencias de notificación por canal y por tipo, con horario de silencio.
- **Panel de privacidad**: qué datos tenemos, quién los ve, descargar mis datos (JSON/PDF), solicitar supresión. Exigido por Ley 25.326.
- Gestión de dispositivos con sesión activa, cierre remoto.
- Bloqueo de tarjeta por robo/pérdida.
- **Accesibilidad:** contraste alto, tamaño de fuente escalable, lectores de pantalla, textos en lenguaje claro, modo simplificado (3 botones grandes: Mi tarjeta / Beneficios cerca / Mis puntos) pensado para adultos mayores.

---

# PARTE 4 — M2 · Módulo Comercio

## 4.1 Adhesión

**Autogestión (portal web público):**
1. CUIT + verificación de inscripción municipal contra el endpoint (§7.1).
2. Datos del comercio, rubro, logo.
3. Alta de al menos una sucursal con pin en mapa.
4. Datos del responsable (será Admin de Comercio) con verificación de identidad.
5. Declaración de descuento base ofrecido.
6. Documentación: constancia de inscripción AFIP, DNI del responsable.
7. Aceptación del convenio de adhesión (firma digital / aceptación con OTP).
8. Envío → estado SOLICITADA.

**Regla decidida:** solo pueden adherir comercios **inscriptos en el municipio**, verificado contra el campo `es_comerciante` del endpoint (§7.1). No se exige estado de cuenta ni situación fiscal del comercio.

**Estados y transiciones:**
```
SOLICITADA ─→ EN_REVISION ─→ APROBADA ─→ ACTIVA
     │             │  └─→ DOCUMENTACION_PENDIENTE ─→ EN_REVISION
     │             └─→ RECHAZADA (con motivo)
   ACTIVA ─→ SUSPENDIDA (por municipio o autosuspensión) ─→ ACTIVA
   ACTIVA ─→ BAJA (solicitada por el comercio o por el municipio)
```

**Baja y suspensión:** no hay régimen sancionatorio por ordenanza. El instrumento es el **convenio de adhesión** que el comercio firma al inscribirse, donde acepta que el municipio puede suspenderlo o darlo de baja si no cumple lo publicado. La decisión la toma el administrador municipal, siempre con motivo registrado y notificación al comercio (§5.1).

## 4.2 Gestión de sucursales

- ABM completo con los campos de §1.5.
- **Pin obligatorio en mapa.** Las direcciones textuales en el interior son poco confiables; el pin es lo que hace funcionar el mapa y el geofencing.
- Horarios por día con doble turno (mañana/tarde), que es lo habitual en San Juan.
- Estado "cerrada temporalmente" con motivo y fecha estimada de reapertura — evita que el vecino vaya al pedo y califique mal.
- Fotos de fachada e interior (mín. 1, máx. 8).
- QR de establecimiento imprimible en PDF listo para plastificar.
- Cada sucursal con métricas propias.
- Casa central con atributos heredables a sucursales nuevas.

## 4.3 Usuarios del comercio

- Invitación por celular/email, link con vencimiento 72 h.
- El invitado se registra o vincula su Persona existente.
- **Login de cajero:** el dispositivo se registra una vez (con credencial de Encargado); después el cajero entra con PIN de 4-6 dígitos. Nadie tipea contraseñas largas con cola en la caja.
- Cierre de sesión automático por inactividad (configurable, default 30 min) en dispositivos compartidos.
- Turnos: apertura y cierre de turno por cajero, con resumen.
- Bitácora: cada canje queda asociado al cajero que lo validó.
- Baja inmediata de un cajero revoca todas sus sesiones.

## 4.4 Promociones

**Asistente de creación (5 pasos):**
1. **Qué ofrecés** — mecánica y valores. Aquí se define el reparto: cuánto va a descuento inmediato y cuánto a Puntos Comercio.
2. **A quién** — General, Black o ambos, con valores diferenciados. La UI sugiere activamente dar más a Black y explica por qué (atrae al contribuyente al día, y el municipio destaca esas promos).
3. **Dónde y cuándo** — sucursales, fechas, días, franjas horarias.
4. **Límites** — topes de uso total/por usuario/por día, monto mínimo, tope de descuento.
5. **Imagen y texto** — subir foto, generar con IA, o ambas. Vista previa exacta en app y en redes.

**Estados:**
```
BORRADOR ─→ EN_REVISION ─→ APROBADA ─→ ACTIVA ─→ VENCIDA
                  └─→ RECHAZADA (motivo)      ├─→ AGOTADA
   ACTIVA ⇄ PAUSADA                            
```

**Moderación por nivel de confianza:**
| Nivel | Cómo se publica |
|---|---|
| NUEVO (primeras 3 promos) | Revisión humana previa obligatoria |
| ESTABLECIDO | Prefiltro automático; humano solo si hay señal |
| VERIFICADO | Publicación inmediata, auditoría posterior por muestreo |

Sin esto, la cola de moderación se convierte en el cuello de botella del programa a los dos meses.

**Extras:** duplicar promo anterior, plantillas por rubro, programación anticipada, "promo relámpago" (activación inmediata por pocas horas, con notificación push a usuarios cercanos).

## 4.5 Generación de creatividades con IA

**Flujo:**
1. El comerciante **escribe o dicta** (botón de micrófono → transcripción).
   > *"Promo de empanadas para el fin de semana, dos por uno, que se vea la parrilla, colores cálidos, que llame la atención"*
2. El sistema arma el prompt final combinando:
   - La idea del comerciante
   - Datos estructurados de la promo (%, vigencia, nombre de fantasía)
   - Plantilla de marca del programa (paleta, ubicación del isologo municipal)
   - Restricciones fijas de seguridad
3. Genera **4 variantes** en 3 formatos: 1:1 (feed), 9:16 (story), 16:9 (banner de app).
4. Editor liviano posterior: recortar, mover/editar texto sobreimpreso, cambiar plantilla, subir logo propio, ajustar colores.
5. Guardar como creatividad de la promoción.

**Modo recomendado — "foto real + fondo IA":** el comerciante sube la foto de su producto y la IA solo genera el fondo y la composición. Da resultados sensiblemente mejores que generar el producto entero, y evita la promoción engañosa (mostrar una hamburguesa que no es la que vende).

**Guardarraíles obligatorios:**
- Prohibido generar personas identificables o rostros realistas.
- Prohibidas marcas, logos o personajes de terceros.
- Prohibido texto que prometa condiciones distintas a las de la promoción cargada. El texto sobreimpreso del % se **inyecta desde los datos**, no lo escribe la IA.
- Filtro de contenido inapropiado antes de mostrar el resultado.
- Metadato + marca de agua discreta indicando generación por IA.
- Toda imagen generada pasa por la cola de moderación según nivel de confianza.

**Control de costos:** **10 generaciones por mes por comercio, igual para todos**, sin distinción por nivel de confianza. Contador visible en el portal. El municipio puede otorgar cuota extra puntual en campañas.

**Qué consume un crédito:** un pedido de generación, que devuelve el set completo de 4 variantes en 3 formatos. Volver a generar porque no gustó el resultado consume otro crédito.

**Consecuencia de diseño:** con una cuota ajustada, el **editor posterior** (§4.5) pasa a ser más importante que la generación misma. El comerciante tiene que poder recortar, mover el texto, cambiar la plantilla y ajustar colores sin gastar crédito. Y la vista previa antes de generar debe ser clara, para que no se queme un crédito en un intento a ciegas.

**También con IA:** generación del copy para redes y del texto de la promoción, siempre editable y siempre con el dato duro (%, vigencia) inyectado desde el sistema.

## 4.6 Caja: app con perfil de comercio + web como alternativa

**Decisión tomada: una sola app, una sola publicación en las tiendas, con perfiles distintos adentro.** El comercio opera desde la misma app que descarga el vecino; al iniciar sesión, la app lo lleva al perfil que corresponde. Ver §11.2 para el detalle de perfiles y cambio de contexto.

**Además**, todo el módulo de caja funciona también desde el navegador, sin instalar nada. No es un reemplazo de la app: es la salida para el comercio que prefiere usar la PC del mostrador que ya tiene, o el que no quiere instalar nada en el celular del empleado. URL corta y dictable por teléfono, tipo `caja.rivadavia.gob.ar`.

**Dos métodos de validación, sin jerarquía impuesta:**

| Método | Requiere | Para quién |
|---|---|---|
| **Escaneo de QR desde la app** | La app instalada + cámara | Vía principal. Rápida y con modo offline sólido. |
| **Código de 6 dígitos** | Solo un navegador. Ninguna cámara, ningún permiso. | Comercio sin app, PC del mostrador, celular viejo, o cuando falla la cámara. Nunca bloquea una venta. |
| **Escaneo de QR desde el navegador** | Cámara + navegador compatible | Comercio que no quiere instalar la app pero sí quiere velocidad |

**Límites conocidos del escaneo por navegador** (no aplican a la app):
- En iPhone solo funciona en Safari. Desde Chrome de iOS o el navegador interno de Instagram, la cámara no responde.
- El reconocimiento del QR corre en JavaScript, más lento que en la app en Android de gama baja.
- El código de 6 dígitos existe justamente para que ninguno de estos límites frene una operación.

**Pantalla principal de caja:** botón grande "Escanear" + campo para el código. Nada más.

**Modo caja bloqueado (nuevo, y necesario):**
El celular del mostrador tiene adentro el perfil ciudadano del dueño. Si un empleado agarra ese teléfono, no puede poder saltar al perfil personal del jefe.
- Al abrir turno, la app queda **fijada** en la pantalla de caja.
- Salir del modo caja o cambiar de perfil exige el PIN del encargado.
- El cierre de turno libera el bloqueo.
- Si el dispositivo es personal del dueño y no compartido, el bloqueo se puede desactivar en la configuración del comercio.

**Flujo:**
1. Escanear QR (o ingresar código de 6 dígitos).
2. Muestra: nombre + inicial de apellido, nivel (con color), promociones aplicables.
3. Ingresar monto de compra (teclado numérico grande).
4. Seleccionar promoción (viene preseleccionada la de mayor beneficio).
5. Pantalla de confirmación: monto, descuento, total a cobrar, puntos.
6. Esperar aceptación del ciudadano.
7. Confirmado. Botón "Nueva operación".

**Modo sin conexión:**
- Service worker + IndexedDB guardan localmente las promociones vigentes y los hashes de códigos válidos, actualizados en cada sincronización.
- Sin internet: valida contra el caché local, encola la transacción, muestra "pendiente de sincronización".
- Límites reforzados en modo offline: monto máximo por operación y cantidad máxima de operaciones encoladas.
- Al recuperar conexión: sincroniza y resuelve conflictos (ej: tope de promo ya agotado → se honra al ciudadano y se avisa al comercio).
- **Esto no es opcional en Argentina.** Un comercio que no puede cobrar porque se cayó internet se da de baja del programa esa misma semana.
- **Es el único punto donde una app nativa sería claramente superior.** Hay que probar el PWA con cuidado en el piloto; si falla, ahí sí se justifica la app.

**Cierre de caja:** resumen del turno — cantidad de operaciones, monto bruto, descuento otorgado, puntos emitidos, por promoción.

## 4.7 Reportes del comercio

Este módulo es lo que retiene al comercio. Si solo ve "diste 40 descuentos", se va.

| Reporte | Contenido |
|---|---|
| **Resumen** | Canjes, monto bruto generado, descuento otorgado, ticket promedio |
| **Clientes** | Nuevos vs. recurrentes, frecuencia de repetición, distribución por nivel |
| **Impacto real** | Ticket promedio con tarjeta vs. sin tarjeta (dato que el comercio declara o se estima) |
| **Por promoción** | Ranking de rendimiento, costo del descuento vs. facturación generada |
| **Por sucursal / por cajero** | Comparativo |
| **Horarios y días** | Mapa de calor para decidir cuándo hacer promos |
| **Benchmark de rubro** | Su rendimiento vs. el promedio anónimo de su rubro en Rivadavia |
| **Calificación** | Promedio y comentarios de ciudadanos |

El benchmark de rubro es el dato que el comercio no puede conseguir por su cuenta y por el que vuelve al portal.

Exportación a CSV/Excel. Resumen mensual automático por email y WhatsApp.

---

# PARTE 5 — M3 · Módulo Administrador Municipal

## 5.1 Bandeja de comercios

- Cola de solicitudes con SLA visible y semáforo por antigüedad.
- Ficha de revisión: datos, documentación, verificación automática de inscripción municipal (✅/❌), historial si ya estuvo adherido.
- Acciones: aprobar / rechazar con motivo / pedir documentación.
- **Ficha 360 del comercio:** sucursales, usuarios, promociones activas e históricas, volumen de canjes, calificación, reclamos, estado de inscripción, historial de moderación.
- Carga masiva por CSV para migración inicial o incorporación de una cámara de comercio completa.
- Baja/suspensión con motivo obligatorio y notificación automática.

## 5.2 Gestión de ciudadanos

- Búsqueda por DNI, CUIL, nombre, número de tarjeta, cuenta tributaria.
- **Ficha 360:** nivel y su historial con motivo, cuentas tributarias y estado, grupo familiar, billeteras, transacciones, dispositivos, reclamos, casos.
- **Alta presencial:** pantalla optimizada para mesa de entrada. El vecino llega sin smartphone, el personal lo registra, valida DNI, emite tarjeta física en el momento.
- Suspensión por fraude con expediente asociado.
- Resolución de conflictos de grupo familiar (ej: divorcio, disputa por el pozo de puntos).
- Ajuste manual de puntos: motivo obligatorio, tope por rol, doble conformidad por encima de cierto monto, siempre auditado.
- Excepciones de nivel: otorgar Black a un caso puntual (ej: exención por discapacidad, jubilado con eximición) con vigencia y motivo.

## 5.3 Moderación

- Cola unificada de promociones e imágenes pendientes.
- Prefiltrado automático con score y motivo de la señal.
- Vista lado a lado: creatividad + datos de la promo, para detectar incoherencias (la imagen dice 50%, la promo dice 20%).
- Acciones: aprobar / rechazar con motivo / aprobar con edición.
- Gestión de niveles de confianza por comercio, con promoción automática por buen historial.
- Auditoría posterior por muestreo aleatorio de comercios VERIFICADO.

## 5.4 Campañas municipales

- Creación de campaña: nombre, período, pieza gráfica común, condiciones mínimas para participar.
- Invitación masiva a comercios; ellos se suman con un clic aceptando las condiciones.
- Landing de campaña destacada en la app y en el mapa.
- Publicación coordinada en redes oficiales.
- Reporte de impacto de la campaña: comercios participantes, canjes, monto movilizado, alcance en redes.

Ejemplos: "Semana del Comercio Rivadaviense", "Vuelta al Cole", "Fin de semana largo en Rivadavia", "Mes del Jubilado".

## 5.5 Parametría

Todo esto se cambia sin desarrollo:
- Tasas de acumulación y conversión de puntos.
- Vencimiento de puntos (definido: 24 meses).
- Cuota mensual de generación de imágenes con IA (definida: 10 por comercio).
- Límites de grupo familiar (todos los de §3.3).
- Rubros y categorías.
- (Sin mínimo ni máximo de descuento: el comercio fija libremente el porcentaje.)
- Ventana de anulación.
- Cuotas de generación de IA.
- Textos legales y TyC, versionados, con reaceptación forzada si cambian sustancialmente.
- *Feature flags* (ej: canje contra tasas = OFF).

## 5.6 Tablero de gobierno

**Bloque ciudadanía:** registrados, activos (30 días), distribución por nivel, por barrio, por edad, tasa de activación, retención.

**Bloque recaudación — el bloque que justifica el programa:**
- Contribuyentes que pasaron de GENERAL a BLACK después de registrarse
- Comparativo de morosidad: registrados vs. no registrados

El monto en pesos no se calcula acá — la tarjeta no maneja montos. Hacienda lo cruza por fuera con la lista de CUILs.

> Este es el número que se lleva al Concejo Deliberante y al intendente. No es "descargas de la app".

**Bloque comercios:** adheridos por rubro y zona, activos vs. inactivos, mapa de cobertura con **desiertos comerciales** (zonas con vecinos y sin comercios adheridos → ahí va el promotor), ranking, altas y bajas.

**Bloque transaccional:** volumen de canjes, monto bruto movilizado, descuento agregado otorgado por los comercios (dato de valor político: "el programa movilizó $X millones en la economía local"), mapa de calor de consumo.

**Bloque operativo:** SLA de moderación, tickets abiertos, alertas antifraude, salud de las integraciones.

Todo exportable, con reportes preformateados para prensa y rendición de cuentas.

## 5.7 Perfil municipal en la app

No es una app aparte: es el tercer perfil de la app única (§11.2). Cubre solo operación en calle; todo lo que sea gobierno del sistema queda en el portal web. El reparto completo y los recaudos de seguridad están en §11.3.

**Funciones en la app:**
- Verificar un comercio en el lugar (¿está adherido? ¿respeta el descuento? ¿tiene el sello en la vidriera?)
- Alta rápida de comercio con foto de fachada y pin GPS automático.
- Alta rápida de ciudadano en operativos barriales.
- Consulta de ficha por DNI, con re-autenticación biométrica.
- Registro de visita de promotor.
- Cola de moderación simplificada (aprobar / rechazar).
- Levantar un caso o incidencia desde el lugar.

**Lo que nunca está en la app:** parametría, roles, bajas definitivas, ajustes de puntos, logs, exportaciones masivas, tablero completo, y cualquier acción con doble conformidad.

---

# PARTE 6 — M4 · Redes sociales

## 6.1 Conexión y canales

- **Oficiales del municipio:** Instagram, Facebook, TikTok, X, canal de difusión de WhatsApp.
- **Propios del comercio:** conexión opcional para publicar en su feed desde el mismo lugar.
- Gestión de tokens con renovación automática y alerta al vencer.

## 6.2 Flujo de publicación

1. Desde una promoción aprobada: botón "Publicar en redes".
2. El sistema toma las creatividades ya generadas y adapta formato por red.
3. Genera copy con IA (editable) con hashtags sugeridos y ubicación geográfica.
4. Vista previa por red.
5. Publicar ahora / programar / enviar a la cola editorial del municipio.

## 6.3 Cola editorial

El municipio no puede publicar 40 promos por día en su Instagram oficial. Se necesita curaduría:
- Cola con priorización manual.
- Calendario editorial mensual con vista de qué se publica cada día.
- Cupo diario configurable por red.
- Criterios sugeridos de selección: comercios nuevos, campañas vigentes, rubros con poca exposición, rotación equitativa.
- **Regla de equidad:** el sistema lleva registro de cuántas veces se publicó cada comercio y alerta si hay concentración. En un organismo público, la equidad en el uso de canales oficiales no es un detalle estético.

## 6.4 Métricas y fallback

- Alcance, interacciones, clics, guardados por publicación.
- Link corto rastreado que lleva a la promo en la app → atribución de canjes al posteo.
- **Fallback obligatorio:** si la API de una red no permite publicación automática (TikTok e Instagram tienen restricciones variables), el sistema genera un paquete descargable (imágenes en todos los formatos + copy listo para copiar) y notifica al community manager. El flujo nunca queda trabado por una API de terceros.

---

# PARTE 7 — M5 · Endpoint de verificación municipal

El municipio expone un endpoint mínimo. La tarjeta **no accede a cuotas, montos, cuentas ni vencimientos, y no replica el criterio de Hacienda**. Recibe un veredicto ya calculado y lo consume.

## 7.1 Contrato

```
GET /padron/estado?cuil={cuil}
Authorization: servidor a servidor (mTLS o API key rotativa)

200 OK
{
  "cuil": "20123456789",
  "es_contribuyente": true,
  "al_dia": true,
  "es_comerciante": true,
  "cuit_comercio": "30712345678",
  "fecha_corte": "2026-09-02T03:00:00-03:00"
}
```

| Campo | Para qué |
|---|---|
| `es_contribuyente` | Distingue al que no figura en el padrón del que figura. Sin esto, la app le dice "tenés deuda" a un inquilino. |
| `al_dia` | Determina GENERAL vs BLACK. Booleano puro. El criterio lo define Hacienda y no se cuestiona. |
| `es_comerciante` | Valida la adhesión de comercios: debe estar inscripto en el municipio (§4.1). |
| `fecha_corte` | Nunca mostrar el estado sin decir de cuándo es el dato. |

**Fuera de alcance en esta etapa:** montos, cuentas tributarias, cantidad de cuotas, fechas de vencimiento, planes de pago, webhooks de pago. Nada de eso se pide ni se almacena.

## 7.2 Sincronización

- Batch nocturno (03:00) sobre los usuarios registrados.
- Botón "Actualizar mi estado" en la app, máx. 3 usos por día.
- Caché con TTL de 6 h, invalidado por el botón.
- `fecha_corte` visible en pantalla.

## 7.3 Degradación

Si el endpoint no responde, el programa no se cae:
- Se usa el último estado conocido, con la fecha de corte a la vista.
- **Nadie baja de nivel por falta de datos.** Solo se baja con dato fresco.
- Los canjes siguen funcionando con normalidad.

## 7.4 Seguridad del endpoint

Devuelve situación fiscal por CUIL. Si queda expuesto, cualquiera averigua si su vecino debe impuestos.

- Autenticación servidor a servidor. **Nunca** consumido desde la app.
- Rate limiting por origen y detección de consultas masivas.
- Log de cada consulta: qué CUIL, cuándo y qué la disparó.
- Solo se consulta el CUIL de una persona con sesión verificada activa, o por un agente municipal en un alta presencial identificada. Nunca un CUIL arbitrario.

## 7.5 Qué se almacena

Solo: `es_contribuyente`, `al_dia`, `es_comerciante`, `cuit_comercio`, `fecha_corte`, y el histórico de cambios de esos valores.

Sin montos, sin cuentas, sin conceptos. La base es mínima.

# PARTE 8 — M6 · Antifraude, seguridad y cumplimiento

## 8.1 Vectores de fraude y contramedidas

| Vector | Contramedida |
|---|---|
| QR compartido por captura de pantalla | QR dinámico rotativo cada 45 s |
| Cajero quema beneficios de clientes | Confirmación obligatoria del ciudadano en su celular |
| Comercio infla precios y "da" el descuento | Precio de referencia declarado + calificación ciudadana + comprador incógnito |
| Titular "alquila" nivel Black a terceros | Límites, cooldowns y alertas de grupo familiar (§3.3) |
| Canjes falsos para inflar métricas | Análisis de patrones: frecuencia, geo, horario, monto redondo |
| Cuentas duplicadas | Unicidad por DNI/CUIL + verificación de identidad |
| Abuso del modo offline | Tope de monto y de operaciones encoladas |
| Bots en el registro | Rate limiting, verificación de celular, captcha invisible |

## 8.2 Motor de alertas

Reglas configurables que generan casos para revisión, no bloqueos automáticos (un bloqueo automático mal calibrado en un servicio público genera un problema mayor que el fraude que evita):

- Cajero con volumen > 3σ del promedio de su rubro y horario
- Ciudadano con > N canjes en < X minutos
- Canje con geolocalización a > 500 m de la sucursal
- Canje fuera del horario declarado de la sucursal
- Grupo familiar con dispersión geográfica y de apellidos anómala
- Comercio con calificación en caída abrupta
- Pico de anulaciones en un comercio

## 8.3 Seguridad técnica

- TLS 1.3 en tránsito; cifrado en reposo; **cifrado a nivel de campo** para DNI, CUIL y domicilio.
- MFA obligatorio para todos los roles municipales y para Admin de Comercio.
- Rate limiting por IP, por usuario y por endpoint.
- Segregación de ambientes (dev / staging / prod) con datos anonimizados fuera de producción.
- Rotación de secretos, gestión centralizada de credenciales.
- **Log de auditoría inmutable**, append-only, no borrable ni por el superadministrador.
- Backups diarios con retención 30 días + mensual con retención 12 meses. **Prueba de restauración trimestral** — un backup no probado no es un backup.
- Penetration test antes del lanzamiento público y anual.
- Plan de respuesta a incidentes con notificación a la AAIP en caso de brecha.

## 8.4 Cumplimiento normativo (Argentina)

- **Ley 25.326:** en esta etapa se implementan en producto la minimización de datos, la política de privacidad accesible y los derechos de acceso, rectificación y supresión. La inscripción formal de la base ante la AAIP queda para más adelante.
- **Ley 24.240** de Defensa del Consumidor: las condiciones de las promociones deben ser claras, accesibles y respetadas. El municipio es responsable de que lo publicado se cumpla.
- **Sin ordenanza en esta etapa.** El instrumento que obliga al comercio es el convenio de adhesión que firma al inscribirse. La facultad de suspender o dar de baja queda en el administrador municipal, con motivo registrado.
- Accesibilidad: pauta WCAG 2.1 nivel AA como objetivo.

---

# PARTE 9 — M7 · Captación de comercios (módulo agregado)

No estaba en el pedido original, pero con el modelo "el comercio absorbe" es el módulo que decide si el proyecto vive o muere.

**Funcionalidades:**
- **CRM de captación**: universo de comercios de Rivadavia (importado del padrón de inscripciones municipales), estado en el embudo (no contactado → contactado → interesado → en alta → adherido → activo → en riesgo → baja).
- **Asignación a promotores** por zona o rubro, con metas.
- **App del promotor** (parte de la app del administrador): visitas, resultado, foto, alta en el momento con el comercio presente.
- **Alertas de riesgo de baja**: comercio sin promociones activas hace 30 días, sin canjes hace 45 días, calificación en caída.
- **Playbook de objeciones** integrado (qué responder al "no me conviene dar descuento").
- **Reporte de embudo** para el tablero de gobierno.

---

# PARTE 10 — M8 · Notificaciones

| Tipo | Canal | Destinatario | Ejemplo |
|---|---|---|---|
| Transaccional | Push + in-app | Ciudadano | Confirmación de canje |
| Estado fiscal | Push + email | Ciudadano | "Tu cuota vence en 10 días" |
| Cambio de nivel | Push + email | Ciudadano | "Ya sos Black" |
| Puntos por vencer | Push | Ciudadano | A 30 y 7 días |
| Beneficio cercano | Push (geofence) | Ciudadano | Máx. 1 por día, opt-in |
| Nueva promo de favorito | Push | Ciudadano | Opt-in |
| Invitación a grupo | Push + SMS | Ciudadano | — |
| Promoción moderada | Email + in-app | Comercio | Aprobada / rechazada |
| Resumen semanal | Email + WhatsApp | Comercio | Métricas |
| Solicitud de adhesión | In-app | Municipio | Nueva en la cola |
| Alerta antifraude | In-app + email | Municipio | Caso generado |

**Reglas de higiene:** horario de silencio 22:00–08:00 salvo transaccionales; máximo 3 push promocionales por semana por usuario; opt-out granular; frecuencia adaptativa (si no abre, baja la frecuencia).

---

# PARTE 11 — Arquitectura técnica sugerida

## 11.1 Stack

| Capa | Recomendación | Por qué |
|---|---|---|
| Backend | **Node.js (NestJS)** o **.NET 8** | Ecosistema local con talento disponible en San Juan/Mendoza |
| Base de datos | **PostgreSQL** + PostGIS | PostGIS resuelve todo lo geoespacial nativamente |
| Caché / colas | **Redis** | Sesiones, tokens de canje, rate limiting, colas |
| Almacenamiento | S3 compatible (MinIO on-premise o cloud) | Imágenes |
| App única | **Flutter** o **React Native** | Una base de código, una publicación, perfiles adentro. Ver §11.2 |
| Portales web | React / Next.js | Gestión y reportes en pantalla grande, complementarios a la app |
| Portales web | React / Next.js | — |
| IA de imágenes | API externa vía capa de abstracción | Poder cambiar de proveedor sin tocar el producto |
| Notificaciones | Firebase Cloud Messaging + proveedor SMS/WhatsApp local | — |
| Observabilidad | Logs centralizados + APM + alertas | — |

## 11.2 App única con perfiles

**Decisión tomada: una sola aplicación, una sola publicación en App Store y Google Play, con perfiles distintos adentro.** No hay app de ciudadano por un lado y app de comercio por otro.

Encaja con el modelo de datos de §1.1: una `Persona` con credencial única, que puede tener `PerfilCiudadano`, `PerfilComercio` (en uno o varios comercios) y `PerfilMunicipal` simultáneamente.

**Ruteo al iniciar sesión:**

| Perfiles que tiene la persona | Qué pasa |
|---|---|
| Solo ciudadano | Entra directo al home de beneficios |
| Solo comercio (ej: un cajero que no es contribuyente) | Entra directo a la pantalla de caja |
| Solo municipal | Entra directo al panel de agente |
| Dos o tres perfiles | Entra al último usado, con selector visible arriba |
| Comercio en dos comercios distintos | Selector de comercio dentro del perfil comercio |

**El caso de tres perfiles es real:** un empleado municipal que además es contribuyente de Rivadavia y ayuda en el negocio familiar los sábados. La app tiene que soportarlo sin fricción.

**El cambio de perfil es de un toque, sin volver a iniciar sesión.** El caso no es raro, es el más común: el dueño de la panadería es también vecino de Rivadavia y va a querer usar su tarjeta en la ferretería el sábado y atender su caja el lunes.

**Implicancias a tener en cuenta:**

| Tema | Cómo se resuelve |
|---|---|
| Ficha en las tiendas | Título y descripción tienen que hablarle a los dos públicos. Capturas de ambos perfiles. |
| Peso de la app | Carga diferida de módulos: un ciudadano no descarga el código de caja hasta que lo necesita. |
| Permiso de cámara | Se pide en el momento de usarla, no al instalar. |
| Notificaciones | Segmentadas por perfil activo. Un cajero en turno no recibe "beneficios cerca tuyo"; un ciudadano no recibe "promoción aprobada". |
| Dispositivo compartido en el mostrador | **Modo caja bloqueado.** Ver §4.6. |
| Actualizaciones | Un solo release para todos. Ventaja real: no hay que coordinar versiones entre dos apps. |

**Los portales web siguen existiendo** como complemento, no como reemplazo. La regla de reparto es simple: **la app cubre lo que se hace parado; el portal cubre lo que se hace sentado.**

| | App | Portal web |
|---|---|---|
| Ciudadano | Tarjeta, mapa, canje, puntos, mi estado | Consulta de beneficios, perfil, descarga de datos |
| Comercio | Caja, pausar promo, ver el día | Promociones, sucursales, usuarios, reportes |
| Municipal | Operación en calle (ver abajo) | Toda la gestión y el gobierno del sistema |

## 11.3 Perfil municipal dentro de una app pública

Que el perfil municipal viva en una app que cualquiera puede descargar es viable, pero exige tres cosas que no son opcionales.

**1. No existe pantalla de acceso administrativo.** No hay menú oculto, gesto secreto ni "modo admin". La app muestra únicamente los perfiles que el servidor dice que esa Persona tiene. Si alguien descarga la app y no tiene `PerfilMunicipal` asignado, para él ese perfil no existe: no hay nada que buscar ni que forzar. Toda la autorización es del lado del servidor.

**2. Reparto estricto de funciones entre app y portal.**

| En la app (operación en calle) | Solo en el portal web (gobierno del sistema) |
|---|---|
| Verificar un comercio en el lugar | Parametría y reglas de nivel |
| Alta rápida de comercio con foto y GPS | Gestión de roles municipales |
| Alta rápida de ciudadano en operativos | Baja definitiva de comercios |
| Consulta de ficha por DNI | Ajustes manuales de puntos |
| Registro de visita de promotor | Logs de auditoría |
| Cola de moderación simplificada | Exportaciones masivas de datos |
| | Tablero de gobierno completo |
| | Toda acción con doble conformidad |

Nada que requiera 🔒 doble conformidad (§2.2) se ejecuta desde la app.

**3. Protección del dato personal en un celular que anda por la calle.**
- MFA obligatorio y **registro previo del dispositivo** para perfiles municipales. Un agente no puede abrir su perfil en un teléfono desconocido.
- Sin caché local de datos de ciudadanos. Lo que se consulta se muestra y se descarta.
- Timeout de sesión más corto que en los otros perfiles (sugerido: 10 minutos).
- Re-autenticación biométrica para abrir una ficha 360.
- Marca de agua en pantalla con el nombre del agente y la fecha, para desalentar capturas.
- Cada consulta desde la app queda logueada con dispositivo y geolocalización.

**Nota sobre las tiendas:** la descripción pública de la app no debe mencionar funciones administrativas. Habla de la tarjeta de beneficios para vecinos y comercios; el perfil municipal es una capacidad interna que se activa por asignación, no un argumento de venta.

## 11.4 Multi-tenant desde el día uno

Si el programa funciona, los municipios vecinos lo van a querer (Santa Lucía, Chimbas, San Martín, Caucete). Incluir `id_municipio` en el modelo de datos desde el inicio cuesta poco. Agregarlo después es una reescritura. **Fuerte recomendación de hacerlo ahora**, aunque el primer y único tenant sea Rivadavia.

## 11.5 Infraestructura

- Hosting: definir si es on-premise municipal o cloud. Si hay dato personal sensible, verificar la política provincial de residencia de datos.
- Ambientes separados, CI/CD, infraestructura como código.
- Escalado: el pico es predecible (mediodía, tarde, fin de semana). No necesita arquitectura exótica.

---

# PARTE 12 — Roadmap y estrategia de lanzamiento

## 12.1 Fases

**Fase 1 — Piloto (3-4 meses)**
Núcleo, identidad, motor de nivel con integración a recaudación, app ciudadano (tarjeta + descubrimiento + canje), **app única con perfil de comercio (caja con QR y código de 6 dígitos) + caja web como alternativa**, portal de comercio básico (sucursales, usuarios, promociones simples), portal municipal básico (adhesión, moderación, ficha 360). Solo descuento directo. Sin puntos, sin grupo familiar, sin IA, sin redes.
**Meta:** los grandes comercios activos con promociones cargadas, más los comercios chicos que se sumen en el período.

**Fase 2 — Programa completo (3-4 meses)**
Puntos Comercio y Municipales, grupo familiar con fondo común, promociones avanzadas, generación con IA, publicación en redes, reportes de comercio con benchmark, tarjeta física, modo offline, tablero de gobierno.

**Fase 3 — Escala e integración fiscal (3 meses)**
Canje contra tasas (si Hacienda lo aprueba), campañas municipales, inventario municipal de beneficios, **perfil municipal en la app** y módulo de captación, geofencing, referidos, multi-tenant activo.

## 12.2 Estrategia de lanzamiento

**Los grandes comercios ya confirmaron su adhesión.** Eso resuelve el arranque en frío: el vecino que abre la app el día uno encuentra marcas que reconoce y beneficios que le sirven, sin depender de que se sumen primero decenas de comercios chicos.

La secuencia es a la inversa de lo habitual: los grandes llevan la delantera y el resto se suma después, empujado por la visibilidad del programa y por no quedar afuera de donde están sus clientes.

**Implicancias para el módulo de captación (M7):**
- El argumento de venta al comercio chico deja de ser "sumate a construir algo" y pasa a ser "tus clientes ya están usando esto en otro lado".
- El mapa de la app va a mostrar desde el principio dónde faltan comercios. Esos huecos son la agenda del promotor.
- Conviene que los grandes tengan promociones cargadas y activas **antes** de abrir el registro al público. Una app con comercios adheridos pero sin promociones vigentes se percibe como vacía.

## 12.3 Métricas de éxito

**Adelantadas (semanas):**
- Comercios adheridos y activos (con ≥1 canje/semana)
- Ciudadanos registrados / % de la población objetivo
- Tasa de activación (registrados que canjean al menos una vez en 30 días)
- Canjes por usuario activo por mes

**Rezagadas (meses):**
- **Contribuyentes que regularizaron tras registrarse** ← la métrica del programa
- Diferencial de morosidad entre registrados y no registrados
- Retención de comercios a 6 meses
- Monto movilizado en la economía local
- NPS de ciudadanos y de comercios

---

# PARTE 13 — Pendientes de definición

Queda un solo punto abierto. Todo lo demás está decidido y aplicado en el documento.

## 13.1 A confirmar con Sistemas del municipio

| Pendiente | Por qué importa |
|---|---|
| Que el endpoint devuelva **dos booleanos separados**: `es_contribuyente` y `al_dia` | Si viene uno solo, la app no puede distinguir al inquilino que no figura en el padrón del contribuyente que no está al día, y le termina diciendo "tenés deuda" a alguien que no debe nada. No es una consulta sobre cuotas ni sobre criterios de Hacienda: es una línea en el contrato del endpoint para evitar un mensaje falso en pantalla. |

---

## Decisiones cerradas

### Modelo del programa

| Tema | Definición |
|---|---|
| Financiamiento del descuento | El comercio absorbe el 100%. El municipio no pone caja. |
| Porcentaje de descuento | Lo fija libremente el comercio. Sin mínimo ni máximo. |
| Estrategia de lanzamiento | Los grandes comercios ya adheridos lideran; el resto se suma después. |
| Requisito para adherir un comercio | Estar inscripto en el municipio. |
| Marco normativo | Sin ordenanza. El instrumento es el convenio de adhesión; la baja la decide el administrador municipal. |

### Verificación municipal

| Tema | Definición |
|---|---|
| Contrato del endpoint | Contribuyente sí/no, al día sí/no, comercio inscripto sí/no, fecha de corte. |
| Fuera de alcance | Montos, cuentas, cuotas, vencimientos, planes de pago, webhooks. |
| Criterio de "al día" | Lo define Hacienda. No se investiga ni se replica. |

### Puntos

| Tema | Definición |
|---|---|
| Puntos Comercio | Circuito cerrado: se canjean solo en el comercio que los emitió, en cualquiera de sus sucursales. |
| Puntos Municipales | Se canjean contra inventario propio del municipio (entradas, talleres, colonias, estacionamiento). |
| Vencimiento | 24 meses rodantes, consumo FIFO por lote. |
| Canje contra tasas | Previsto en la arquitectura, apagado por feature flag. Requiere ordenanza del Concejo Deliberante, no está en agenda. |

### Grupo familiar

| Tema | Definición |
|---|---|
| Máximo de miembros | 6, titular incluido |
| Permanencia mínima | Sin mínimo. Se puede salir cuando se quiera. |
| Cooldown para unirse a otro grupo | 90 días |
| Cambios de composición por año | 4 altas y 4 bajas |
| Cambio de modo de billetera | 1 cada 180 días |
| Verificación del vínculo | Sin verificación documental. El titular declara y es responsable. |
| Pozo al pasar a modo individual | Queda en el titular. |

### Aplicaciones y contenido

| Tema | Definición |
|---|---|
| Arquitectura | Una sola app, una sola publicación, tres perfiles (ciudadano, comercio, municipal) + portales web complementarios. |
| Caja | QR desde la app, código de 6 dígitos, o escaneo desde el navegador. Modo caja bloqueado en dispositivos compartidos. |
| Cuota de generación con IA | 10 por mes por comercio, igual para todos. |
| Ventana de anulación de canje | 15 minutos |
| Timeout de sesión municipal | 10 minutos |

### Cumplimiento

| Tema | Definición |
|---|---|
| Ley 25.326 | Prioridad de esta etapa: que el sistema no sea vulnerable. Se implementan minimización, política de privacidad y derechos de acceso y supresión. La inscripción formal ante la AAIP queda para más adelante. |

---

*v2.0 — Versión final para revisión.*
