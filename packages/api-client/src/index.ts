// Cliente TypeScript de la API. Los tipos se generan desde el OpenAPI 3.1 de FastAPI
// (`pnpm generate:api` -> src/schema.generated.ts, commiteado).

import type { components } from './schema.generated';

export type { components, paths } from './schema.generated';

/** Atajo a los esquemas generados desde el OpenAPI del backend (§06.0.A). */
type S = components['schemas'];

export interface ApiClientOptions {
  baseUrl: string;
  /** Devuelve el token de acceso (o null si no hay sesión). */
  getToken?: () => string | null | Promise<string | null>;
  maxRetries?: number;
  retryBaseMs?: number;
}

/** Error normalizado para la UI. */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

interface BackendError {
  error?: { code?: string; message?: string };
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export interface HealthResponse {
  status: string;
}

export interface HealthDbResponse {
  uuid: string;
  server_version: string;
}

export function createApiClient(options: ApiClientOptions) {
  const { baseUrl, getToken, maxRetries = 3, retryBaseMs = 300 } = options;

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const url = `${baseUrl.replace(/\/$/, '')}${path}`;
    const headers = new Headers(init.headers);
    headers.set('accept', 'application/json');

    const token = getToken ? await getToken() : null;
    if (token) headers.set('authorization', `Bearer ${token}`);

    let lastError: unknown;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const res = await fetch(url, { ...init, headers });
        if (res.ok) {
          if (res.status === 204) return undefined as T;
          return (await res.json()) as T;
        }
        // 5xx: reintentable; 4xx: error de negocio, no se reintenta.
        if (res.status >= 500 && attempt < maxRetries) {
          await sleep(retryBaseMs * 2 ** attempt);
          continue;
        }
        let body: BackendError = {};
        try {
          body = (await res.json()) as BackendError;
        } catch {
          // respuesta sin cuerpo JSON
        }
        throw new ApiError(
          body.error?.message ?? res.statusText ?? 'Error de la API',
          body.error?.code ?? `http_${res.status}`,
          res.status,
        );
      } catch (err) {
        if (err instanceof ApiError) throw err;
        lastError = err;
        if (attempt < maxRetries) {
          await sleep(retryBaseMs * 2 ** attempt);
          continue;
        }
      }
    }
    throw new ApiError(
      lastError instanceof Error ? lastError.message : 'Error de red',
      'network_error',
      0,
    );
  }

  const post = <T>(path: string, data?: unknown): Promise<T> => {
    const init: RequestInit = { method: 'POST' };
    if (data !== undefined) {
      init.headers = { 'content-type': 'application/json' };
      init.body = JSON.stringify(data);
    }
    return request<T>(path, init);
  };

  const del = <T>(path: string): Promise<T> => request<T>(path, { method: 'DELETE' });

  return {
    request,
    health: () => request<HealthResponse>('/health'),
    healthDb: () => request<HealthDbResponse>('/health/db'),
    // --- auth ---
    registro: (body: RegistroBody) => post<Mensaje>('/api/v1/auth/registro', body),
    verificarCelular: (celular: string, codigo: string) =>
      post<Mensaje>('/api/v1/auth/verificar-celular', { celular, codigo }),
    reenviarOtp: (celular: string) => post<Mensaje>('/api/v1/auth/reenviar-otp', { celular }),
    login: (dni: string, password: string) =>
      post<LoginResult>('/api/v1/auth/login', { dni, password }),
    mfaVerificar: (mfa_token: string, codigo: string) =>
      post<LoginResult>('/api/v1/auth/mfa/verificar', { mfa_token, codigo }),
    refresh: (refresh_token: string) => post<Tokens>('/api/v1/auth/refresh', { refresh_token }),
    logout: (refresh_token: string) => post<Mensaje>('/api/v1/auth/logout', { refresh_token }),
    perfiles: () => request<Perfil[]>('/api/v1/auth/perfiles'),
    activarPerfil: (clave: string) =>
      post<Tokens>(`/api/v1/auth/perfiles/${encodeURIComponent(clave)}/activar`),
    // --- personas/me ---
    me: () => request<PersonaMe>('/api/v1/personas/me'),
    consentimientos: () => request<Record<string, boolean>>('/api/v1/personas/me/consentimientos'),
    dispositivos: () => request<Dispositivo[]>('/api/v1/personas/me/dispositivos'),
    revocarDispositivo: (id: string) => del<Mensaje>(`/api/v1/personas/me/dispositivos/${id}`),
    activarMfa: () => post<MfaActivacion>('/api/v1/personas/me/mfa/activar'),
    // --- ciudadania / padron (PASO 04) ---
    miEstado: () => request<EstadoCiudadano>('/api/v1/ciudadania/mi-estado'),
    estadoPadron: () => request<EstadoPadron>('/api/v1/padron/mi-estado'),
    actualizarEstado: () => post<Mensaje>('/api/v1/ciudadania/actualizar-estado'),
    bloquearTarjeta: () => post<Mensaje>('/api/v1/ciudadania/tarjeta/bloquear'),
    // --- gobierno / portal municipal (PASO 05) ---
    parametros: () => request<Record<string, number>>('/api/v1/gobierno/parametros'),
    cambiarParametro: (clave: string, valor: number, motivo = '') =>
      request<Mensaje>(`/api/v1/gobierno/parametros/${encodeURIComponent(clave)}`, {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ valor, motivo }),
      }),
    auditoria: (q: AuditoriaQuery = {}) => {
      const p = new URLSearchParams();
      if (q.actor) p.set('actor', q.actor);
      if (q.accion) p.set('accion', q.accion);
      if (q.entidad) p.set('entidad', q.entidad);
      if (q.limite) p.set('limite', String(q.limite));
      const qs = p.toString();
      return request<RegistroAuditoria[]>(`/api/v1/gobierno/auditoria${qs ? `?${qs}` : ''}`);
    },
    recaudacion: () => request<Recaudacion>('/api/v1/gobierno/recaudacion'),
    agentes: () => request<AgenteMunicipal[]>('/api/v1/gobierno/agentes'),
    solicitarAprobacion: (accion: string, payload: Record<string, unknown> = {}) =>
      post<{ id: string }>('/api/v1/gobierno/aprobaciones', { accion, payload }),
    bandejaAprobaciones: () =>
      request<SolicitudAprobacion[]>('/api/v1/gobierno/aprobaciones'),
    aprobarSolicitud: (id: string, motivo = '') =>
      post<Mensaje>(`/api/v1/gobierno/aprobaciones/${encodeURIComponent(id)}/aprobar`, { motivo }),
    rechazarSolicitud: (id: string, motivo = '') =>
      post<Mensaje>(`/api/v1/gobierno/aprobaciones/${encodeURIComponent(id)}/rechazar`, { motivo }),
    // portal (cross-módulo)
    ficha360: (idPersona: string, reauth: string) =>
      request<Ficha360>(`/api/v1/portal/ficha360/${encodeURIComponent(idPersona)}`, {
        headers: { 'x-reauth': reauth },
      }),
    altaPresencial: (dni: string, fecha_nacimiento: string) =>
      post<AltaPresencialResult>('/api/v1/portal/alta-presencial', { dni, fecha_nacimiento }),
    crearReclamo: (dni: string, motivo: string) =>
      post<{ id: string }>('/api/v1/portal/reclamos', { dni, motivo }),
    aprobarReclamo: (id: string, motivo = '') =>
      post<Mensaje>(`/api/v1/portal/reclamos/${encodeURIComponent(id)}/aprobar`, { motivo }),
    asignarAgente: (id_persona: string, rol: string) =>
      post<Mensaje>('/api/v1/portal/agentes', { id_persona, rol }),
    revocarAgente: (id_persona: string, motivo = '') =>
      post<Mensaje>(`/api/v1/portal/agentes/${encodeURIComponent(id_persona)}/revocar`, { motivo }),
    // --- comercios (PASO 06) ---
    adhesion: (body: S['AdhesionIn']) =>
      post<{ id_comercio: string }>('/api/v1/portal-comercio/adhesion', body),
    miComercio: () => request<ComercioOut>('/api/v1/comercios/mi-comercio'),
    crearSucursal: (body: SucursalIn) => post<Mensaje>('/api/v1/comercios/sucursales', body),
    listarSucursales: () => request<SucursalOut[]>('/api/v1/comercios/sucursales'),
    cerrarSucursal: (id: string, motivo: string, reapertura_estimada: string | null = null) =>
      post<Mensaje>(`/api/v1/comercios/sucursales/${encodeURIComponent(id)}/cerrar-temporal`, {
        motivo,
        reapertura_estimada,
      }),
    reabrirSucursal: (id: string) =>
      post<Mensaje>(`/api/v1/comercios/sucursales/${encodeURIComponent(id)}/reabrir`),
    cercanas: (lat: number, lon: number, radio_m = 5000) => {
      const p = new URLSearchParams({
        lat: String(lat),
        lon: String(lon),
        radio_m: String(radio_m),
      });
      return request<SucursalCercanaOut[]>(`/api/v1/comercios/cercanas?${p.toString()}`);
    },
    abiertoAhora: (id: string) =>
      request<S['AbiertoOut']>(
        `/api/v1/comercios/sucursales/${encodeURIComponent(id)}/abierto-ahora`,
      ),
    invitarUsuario: (rol: string, destino: string, sucursales: string[] = []) =>
      post<InvitacionOut>('/api/v1/comercios/usuarios/invitar', { rol, destino, sucursales }),
    listarUsuarios: () => request<UsuarioComercioOut[]>('/api/v1/comercios/usuarios'),
    aceptarInvitacion: (token: string) =>
      post<Mensaje>(`/api/v1/portal-comercio/invitaciones/${encodeURIComponent(token)}/aceptar`),
    establecerPinCajero: (id_usuario: string, pin: string, huella: string) =>
      request<Mensaje>(`/api/v1/comercios/cajeros/${encodeURIComponent(id_usuario)}/pin`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'X-Device-Huella': huella },
        body: JSON.stringify({ pin }),
      }),
    cajeroLogin: (id_usuario: string, pin: string, huella: string) =>
      request<Tokens>('/api/v1/portal-comercio/cajero/login', {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'X-Device-Huella': huella },
        body: JSON.stringify({ id_usuario, pin }),
      }),
    abrirTurno: (id_sucursal: string) =>
      post<{ id: string }>('/api/v1/comercios/turnos/abrir', { id_sucursal }),
    cerrarTurno: () =>
      post<S['CierreTurnoOut']>('/api/v1/comercios/turnos/cerrar'),
    bajaCajero: (id_usuario: string) =>
      post<Mensaje>(`/api/v1/portal-comercio/cajeros/${encodeURIComponent(id_usuario)}/baja`),
    // bandeja municipal de comercios
    bandejaComercios: () => request<ComercioBandejaOut[]>('/api/v1/portal-comercio/bandeja'),
    fichaComercio: (id: string) =>
      request<FichaComercioOut>(
        `/api/v1/portal-comercio/comercios/${encodeURIComponent(id)}/ficha`,
      ),
    comercioAccion: (
      id: string,
      accion: 'tomar' | 'aprobar' | 'rechazar' | 'pedir-documentacion' | 'suspender',
      motivo = '',
    ) => post<Mensaje>(`/api/v1/portal-comercio/comercios/${encodeURIComponent(id)}/${accion}`, {
      motivo,
    }),
    comercioBajaSolicitar: (id: string, motivo = '') =>
      post<{ id: string }>(
        `/api/v1/portal-comercio/comercios/${encodeURIComponent(id)}/baja-solicitar`,
        { motivo },
      ),
    comercioBajaAprobar: (id_solicitud: string, motivo = '') =>
      post<Mensaje>(`/api/v1/portal-comercio/baja/${encodeURIComponent(id_solicitud)}/aprobar`, {
        motivo,
      }),
    cargaMasivaComercios: (contenido: string, confirmar: boolean) =>
      post<CargaMasivaResultado>('/api/v1/portal-comercio/carga-masiva', { contenido, confirmar }),
    // --- canje (PASO 08) ---
    misTokensCanje: () => request<TokenOut[]>('/api/v1/canje/mis-tokens'),
    generarCodigoCanje: () => post<S['CodigoOut']>('/api/v1/canje/codigo'),
    resolverCanje: (body: S['ResolverIn']) => post<ResolverOut>('/api/v1/canje/resolver', body),
    iniciarCanje: (body: S['IniciarIn']) => post<TransaccionOut>('/api/v1/canje/iniciar', body),
    misPendientesCanje: () => request<TransaccionOut[]>('/api/v1/canje/mis-pendientes'),
    confirmarCanje: (id: string, usar_puntos = 0) =>
      post<TransaccionOut>(`/api/v1/canje/${encodeURIComponent(id)}/confirmar`, { usar_puntos }),
    rechazarCanje: (id: string) =>
      post<Mensaje>(`/api/v1/canje/${encodeURIComponent(id)}/rechazar`),
    pendientesComercioCanje: () =>
      request<TransaccionOut[]>('/api/v1/canje/comercio/pendientes'),
    estadoOperacionCanje: (id: string) =>
      request<TransaccionOut>(`/api/v1/canje/comercio/operacion/${encodeURIComponent(id)}`),
    confirmarComercioCanje: (id: string) =>
      post<TransaccionOut>(`/api/v1/canje/comercio/${encodeURIComponent(id)}/confirmar`),
    anularCanje: (id: string, motivo: string) =>
      post<Mensaje>(`/api/v1/canje/${encodeURIComponent(id)}/anular`, { motivo }),
    disputarCanje: (id: string, motivo: string) =>
      post<Mensaje>(`/api/v1/canje/${encodeURIComponent(id)}/disputar`, { motivo }),
    calificarCanje: (id: string, estrellas: number) =>
      post<Mensaje>(`/api/v1/canje/${encodeURIComponent(id)}/calificar`, { estrellas }),
    historialCanje: () => request<TransaccionOut[]>('/api/v1/canje/historial'),
    resumenTurnoCanje: () => request<ResumenTurno>('/api/v1/canje/turno/resumen'),
    // --- promociones (PASO 07) ---
    crearPromocion: (body: S['PromocionIn']) =>
      post<Mensaje>('/api/v1/portal-comercio/promociones', body),
    listarPromociones: () =>
      request<PromocionOut[]>('/api/v1/portal-comercio/promociones'),
    editarCondicionesPromo: (id: string, body: S['CondicionesIn']) =>
      request<Mensaje>(
        `/api/v1/portal-comercio/promociones/${encodeURIComponent(id)}/condiciones`,
        { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) },
      ),
    publicarPromocion: (id: string) =>
      post<Mensaje>(`/api/v1/portal-comercio/promociones/${encodeURIComponent(id)}/publicar`),
    pausarPromocion: (id: string) =>
      post<Mensaje>(`/api/v1/portal-comercio/promociones/${encodeURIComponent(id)}/pausar`),
    reanudarPromocion: (id: string) =>
      post<Mensaje>(`/api/v1/portal-comercio/promociones/${encodeURIComponent(id)}/reanudar`),
    duplicarPromocion: (id: string) =>
      post<Mensaje>(`/api/v1/portal-comercio/promociones/${encodeURIComponent(id)}/duplicar`),
    // moderación municipal
    colaModeracion: () =>
      request<PromocionOut[]>('/api/v1/portal-comercio/moderacion/promociones'),
    moderarAprobar: (id: string, body: S['ModeracionIn'] = { motivo: '' }) =>
      post<Mensaje>(
        `/api/v1/portal-comercio/moderacion/promociones/${encodeURIComponent(id)}/aprobar`,
        body,
      ),
    moderarRechazar: (id: string, motivo: string) =>
      post<Mensaje>(
        `/api/v1/portal-comercio/moderacion/promociones/${encodeURIComponent(id)}/rechazar`,
        { motivo },
      ),
    // descubrimiento (ciudadano)
    buscarPromos: (params: {
      texto?: string | undefined;
      porcentaje_min?: number | undefined;
      solo_black?: boolean | undefined;
      lat?: number | undefined;
      lon?: number | undefined;
    } = {}) => {
      const p = new URLSearchParams();
      if (params.texto) p.set('texto', params.texto);
      if (params.porcentaje_min) p.set('porcentaje_min', String(params.porcentaje_min));
      if (params.solo_black) p.set('solo_black', 'true');
      if (params.lat !== undefined) p.set('lat', String(params.lat));
      if (params.lon !== undefined) p.set('lon', String(params.lon));
      const qs = p.toString();
      return request<PromocionOut[]>(`/api/v1/promociones/buscar${qs ? `?${qs}` : ''}`);
    },
    feedPromos: () => request<FeedOut>('/api/v1/promociones/feed'),
    resolverPromos: (idSucursal: string, monto = 0) =>
      request<PromocionOut[]>(
        `/api/v1/promociones/resolver?id_sucursal=${encodeURIComponent(idSucursal)}&monto=${monto}`,
      ),
    rankingCriterio: () => request<Mensaje>('/api/v1/promociones/ranking-criterio'),
    favoritosPromo: () => request<Record<string, string[]>>('/api/v1/promociones/favoritos'),
    marcarFavoritoPromo: (body: S['FavoritoIn']) =>
      post<Mensaje>('/api/v1/promociones/favoritos', body),
    fichaPublicaPromo: (id: string) =>
      request<FichaPublicaOut>(`/api/v1/promociones/${encodeURIComponent(id)}`),
    // --- puntos (PASO 09) ---
    misBilleteras: () => request<BilleterasOut>('/api/v1/puntos/billeteras'),
    movimientosPuntos: (tipo_moneda = 'PM', id_comercio?: string) => {
      const p = new URLSearchParams({ tipo_moneda });
      if (id_comercio) p.set('id_comercio', id_comercio);
      return request<MovimientoPuntosOut[]>(`/api/v1/puntos/movimientos?${p.toString()}`);
    },
    puntosPorVencer: (dias = 30) =>
      request<LotePorVencerOut[]>(`/api/v1/puntos/por-vencer?dias=${dias}`),
    catalogoPuntos: () => request<ItemCatalogoOut[]>('/api/v1/puntos/catalogo'),
    canjearInventario: (idItem: string) =>
      post<ComprobanteInventarioOut>(
        `/api/v1/puntos/catalogo/${encodeURIComponent(idItem)}/canjear`,
      ),
    misComprobantesPuntos: () =>
      request<ComprobanteInventarioOut[]>('/api/v1/puntos/mis-comprobantes'),
    pasivoComercioPuntos: () => request<PasivoComercioOut>('/api/v1/puntos/comercio/pasivo'),
    // municipal
    publicarItemCatalogo: (body: ItemCatalogoIn) =>
      post<{ id: string }>('/api/v1/puntos/municipal/catalogo', body),
    catalogoMunicipal: () => request<ItemCatalogoOut[]>('/api/v1/puntos/municipal/catalogo'),
    pmCirculante: () => request<PmCirculanteOut>('/api/v1/puntos/municipal/pm-circulante'),
    acreditarPm: (body: AcreditarPmIn) => post<Mensaje>('/api/v1/puntos/municipal/acreditar', body),
    // --- grupo familiar (PASO 10) ---
    crearGrupo: (modo_billetera = 'COMUN') =>
      post<{ id_grupo: string }>('/api/v1/grupo/crear', { modo_billetera }),
    invitarAlGrupo: () => post<GrupoInvitacionOut>('/api/v1/grupo/invitar'),
    verInvitacionGrupo: (token: string) =>
      request<InvitacionDetalleOut>(`/api/v1/grupo/invitacion/${encodeURIComponent(token)}`),
    aceptarInvitacionGrupo: (token: string) =>
      post<{ id_grupo: string }>(`/api/v1/grupo/invitacion/${encodeURIComponent(token)}/aceptar`),
    salirDelGrupo: () => post<Mensaje>('/api/v1/grupo/salir'),
    disolverGrupo: () => post<Mensaje>('/api/v1/grupo/disolver'),
    cambiarModoGrupo: (modo_billetera: string) =>
      post<Mensaje>('/api/v1/grupo/modo', { modo_billetera }),
    miGrupo: () => request<MiGrupoOut>('/api/v1/grupo/mi-grupo'),
    suspenderMiembro: (idPersona: string) =>
      post<Mensaje>(`/api/v1/grupo/miembros/${encodeURIComponent(idPersona)}/suspender`),
    reactivarMiembro: (idPersona: string) =>
      post<Mensaje>(`/api/v1/grupo/miembros/${encodeURIComponent(idPersona)}/reactivar`),
    fijarTopeMiembro: (idPersona: string, tope_mensual: number | null) =>
      post<Mensaje>(`/api/v1/grupo/miembros/${encodeURIComponent(idPersona)}/tope`, {
        tope_mensual,
      }),
    marcarAvisosVistos: () => post<Mensaje>('/api/v1/grupo/avisos/vistos'),
    // --- contenido (PASO 11) ---
    plantillasContenido: () => request<PlantillaContenidoOut[]>('/api/v1/contenido/plantillas'),
    creditosContenido: () => request<CuotaContenidoOut>('/api/v1/contenido/creditos'),
    generarPieza: (body: GenerarPiezaIn) => post<PiezaOut>('/api/v1/contenido/piezas/generar', body),
    piezaDesdeFoto: (body: FotoPiezaIn) => post<PiezaOut>('/api/v1/contenido/piezas/foto', body),
    listarPiezas: () => request<PiezaOut[]>('/api/v1/contenido/piezas'),
    cambiarPlantillaPieza: (id: string, plantilla: string) =>
      post<PiezaOut>(`/api/v1/contenido/piezas/${encodeURIComponent(id)}/plantilla`, { plantilla }),
    elegirVariantePieza: (id: string, indice: number) =>
      post<PiezaOut>(`/api/v1/contenido/piezas/${encodeURIComponent(id)}/variante`, { indice }),
    sincronizarDatosPieza: (id: string) =>
      post<PiezaOut>(`/api/v1/contenido/piezas/${encodeURIComponent(id)}/sincronizar-datos`),
    colaModeracionPiezas: () => request<PiezaOut[]>('/api/v1/contenido/moderacion'),
    aprobarPieza: (id: string) =>
      post<Mensaje>(`/api/v1/contenido/moderacion/${encodeURIComponent(id)}/aprobar`),
    rechazarPieza: (id: string, motivo: string) =>
      post<Mensaje>(`/api/v1/contenido/moderacion/${encodeURIComponent(id)}/rechazar`, { motivo }),
  };
}

export interface CargaMasivaFila {
  fila: number;
  cuit: string;
  ok: boolean;
  error: string | null;
}

export interface CargaMasivaResultado {
  filas: CargaMasivaFila[];
  validas: number;
  creados: number;
}

export interface EstadoCiudadano {
  nivel: string;
  numero_tarjeta: string;
  estado_tarjeta: string;
  tiene_tarjeta_fisica: boolean;
}

export interface EstadoPadron {
  consultado: boolean;
  al_dia?: boolean | null;
  fecha_ultima_consulta?: string | null;
  horas_desde_consulta?: number | null;
}

export interface Mensaje {
  mensaje: string;
}

export interface ConsentimientoBody {
  tipo: string;
  otorgado: boolean;
}

export interface RegistroBody {
  dni: string;
  cuil: string;
  apellido: string;
  nombre: string;
  celular: string;
  password: string;
  email?: string;
  consentimientos: ConsentimientoBody[];
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Perfil {
  clave: string;
  tipo: string;
  id_comercio?: string | null;
  rol?: string | null;
}

export interface LoginResult {
  mfa_requerido: boolean;
  perfiles: Perfil[];
  perfil_activo?: string | null;
  tokens?: Tokens | null;
  mfa_token?: string | null;
}

export interface PersonaMe {
  id: string;
  dni: string;
  cuil: string;
  apellido: string;
  nombre: string;
  celular: string;
  email: string | null;
  estado_identidad: string;
  celular_verificado: boolean;
  perfiles: Perfil[];
}

export interface Dispositivo {
  id: string;
  nombre_declarado: string;
  plataforma: string;
  estado: string;
  autorizado_para_perfil_municipal: boolean;
}

export interface MfaActivacion {
  secreto: string;
  uri: string;
  codigos_recuperacion: string[];
}

// --- gobierno / portal municipal (PASO 05) ---

export interface AuditoriaQuery {
  actor?: string | undefined;
  accion?: string | undefined;
  entidad?: string | undefined;
  limite?: number | undefined;
}

// Tipos de gobierno/portal/comercios: alias a los esquemas generados desde el OpenAPI.
// Así el cliente no puede divergir del backend (el CI regenera y falla si cambia).
export type RegistroAuditoria = S['RegistroAuditoriaOut'];
export type Recaudacion = S['RecaudacionOut'];
export type AgenteMunicipal = S['AgenteOut'];
export type SolicitudAprobacion = S['SolicitudPendienteOut'];
export type Ficha360 = S['Ficha360Out'];
export interface AltaPresencialResult {
  id_persona: string;
  password_temporal: string;
}

// comercios (PASO 06)
export type ComercioOut = S['ComercioOut'];
export type SucursalOut = S['SucursalOut'];
export type SucursalCercanaOut = S['SucursalCercanaOut'];
export type UsuarioComercioOut = S['UsuarioComercioOut'];
export type ComercioBandejaOut = S['ComercioBandejaOut'];
export type FichaComercioOut = S['FichaComercioOut'];
export type SucursalIn = S['SucursalIn'];
export type InvitacionOut = S['InvitacionOut'];

// promociones (PASO 07)
export type PromocionOut = S['PromocionOut'];
export type PromocionFeedOut = S['PromocionFeedOut'];
export type FichaPublicaOut = S['FichaPublicaOut'];
export type FeedOut = S['FeedOut'];
export type PromocionIn = S['PromocionIn'];

// canje (PASO 08)
export type TokenOut = S['TokenOut'];
export type TransaccionOut = S['TransaccionOut'];
export type ResolverOut = S['ResolverOut'];
export type OpcionOut = S['OpcionOut'];

// puntos (PASO 09)
export type BilleterasOut = S['BilleterasOut'];
export type BilleteraPCOut = S['BilleteraPCOut'];
export type MovimientoPuntosOut = S['MovimientoOut'];
export type LotePorVencerOut = S['LotePorVencerOut'];
export type ItemCatalogoOut = S['ItemOut'];
export type ItemCatalogoIn = S['ItemIn'];
export type ComprobanteInventarioOut = S['ComprobanteOut'];
export type PasivoComercioOut = S['PasivoComercioOut'];
export type PmCirculanteOut = S['PmCirculanteOut'];
export type AcreditarPmIn = S['AcreditarPmIn'];

// grupo familiar (PASO 10)
export type MiGrupoOut = S['MiGrupoOut'];
export type GrupoMiembroOut = S['MiembroOut'];
export type GrupoInvitacionOut = S['GrupoInvitacionOut'];
export type InvitacionDetalleOut = S['InvitacionDetalleOut'];

// contenido (PASO 11)
export type PiezaOut = S['PiezaOut'];
export type PlantillaContenidoOut = S['PlantillaOut'];
export type CuotaContenidoOut = S['CuotaOut'];
export type GenerarPiezaIn = S['GenerarIn'];
export type FotoPiezaIn = S['FotoIn'];

export interface ResumenTurno {
  operaciones: number;
  monto_bruto: number;
  descuento: number;
  por_promocion: Record<string, number>;
}

export type ApiClient = ReturnType<typeof createApiClient>;
