// Cliente TypeScript de la API. Los tipos se generan desde el OpenAPI 3.1 de FastAPI
// (`pnpm generate:api` -> src/schema.generated.ts, commiteado).

export type { components, paths } from './schema.generated';

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
  };
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

export interface RegistroAuditoria {
  id: string;
  timestamp: string;
  accion: string;
  entidad: string;
  id_entidad: string;
  actor: string | null;
  motivo: string;
}

export interface Recaudacion {
  transiciones_a_black_post_registro: number;
  distribucion_por_nivel: Record<string, number>;
}

export interface AgenteMunicipal {
  id_persona: string;
  rol: string;
}

export interface SolicitudAprobacion {
  id: string;
  accion: string;
  solicitante: string;
  fecha_expiracion: string;
}

export interface Ficha360 {
  id: string;
  dni: string;
  apellido: string;
  nombre: string;
  estado_identidad: string;
  nivel: string | null;
  tarjeta: string | null;
  estado_tarjeta: string | null;
  padron_al_dia: boolean | null;
  padron_actualizado: string | null;
  dispositivos: { id: string; nombre: string; estado: string }[];
}

export interface AltaPresencialResult {
  id_persona: string;
  password_temporal: string;
}

export type ApiClient = ReturnType<typeof createApiClient>;
