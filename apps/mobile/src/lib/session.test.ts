// §12 P1-B: la sesión guarda access/refresh en el almacén seguro (no en Preferences), migra los
// tokens legacy que hubieran quedado en Preferences, y deja perfil/huella (no sensibles) en Preferences.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// Almacén de Preferences en memoria para poder verificar qué queda dónde.
const prefs = vi.hoisted(() => new Map<string, string>());

vi.mock('@capacitor/preferences', () => ({
  Preferences: {
    get: vi.fn(async ({ key }: { key: string }) => ({ value: prefs.get(key) ?? null })),
    set: vi.fn(async ({ key, value }: { key: string; value: string }) => {
      prefs.set(key, value);
    }),
    remove: vi.fn(async ({ key }: { key: string }) => {
      prefs.delete(key);
    }),
  },
}));

import { configurarAlmacenSeguro } from './almacen-seguro';
import {
  getAccessToken,
  getPerfilActivo,
  guardarPerfilActivo,
  guardarSesion,
  limpiarSesion,
} from './session';

// Backend seguro falso (representa Keychain/Keystore) para las aserciones.
const seguro = new Map<string, string>();
configurarAlmacenSeguro({
  get: async (k) => seguro.get(k) ?? null,
  set: async (k, v) => void seguro.set(k, v),
  remove: async (k) => void seguro.delete(k),
});

beforeEach(() => {
  prefs.clear();
  seguro.clear();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('session (móvil) — almacén seguro para credenciales', () => {
  it('guarda access/refresh en el almacén seguro, no en Preferences', async () => {
    await guardarSesion('acc-123', 'ref-456');

    expect(seguro.get('tarjeta_access')).toBe('acc-123');
    expect(seguro.get('tarjeta_refresh')).toBe('ref-456');
    expect(prefs.has('tarjeta_access')).toBe(false);
    expect(prefs.has('tarjeta_refresh')).toBe(false);

    expect(await getAccessToken()).toBe('acc-123');
  });

  it('migra un token legacy de Preferences al almacén seguro y lo borra del inseguro', async () => {
    prefs.set('tarjeta_access', 'legacy-token'); // como lo guardaba una versión anterior

    const leido = await getAccessToken();

    expect(leido).toBe('legacy-token');
    expect(seguro.get('tarjeta_access')).toBe('legacy-token'); // migrado
    expect(prefs.has('tarjeta_access')).toBe(false); // limpiado del inseguro
  });

  it('el perfil activo (no sensible) queda en Preferences', async () => {
    await guardarPerfilActivo('COMERCIO');
    expect(prefs.get('tarjeta_perfil_activo')).toBe('COMERCIO');
    expect(seguro.has('tarjeta_perfil_activo')).toBe(false);
    expect(await getPerfilActivo()).toBe('COMERCIO');
  });

  it('limpiarSesion borra las credenciales del almacén seguro y del inseguro', async () => {
    await guardarSesion('acc', 'ref');
    prefs.set('tarjeta_access', 'resto-legacy'); // un resto que hubiera quedado
    await guardarPerfilActivo('CIUDADANO');

    await limpiarSesion();

    expect(seguro.has('tarjeta_access')).toBe(false);
    expect(seguro.has('tarjeta_refresh')).toBe(false);
    expect(prefs.has('tarjeta_access')).toBe(false);
    expect(prefs.has('tarjeta_refresh')).toBe(false);
    expect(prefs.has('tarjeta_perfil_activo')).toBe(false);
  });
});
