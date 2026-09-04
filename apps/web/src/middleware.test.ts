// §12.3-C: toda ruta privada, sin sesión, redirige a login. La API igual valida siempre.

import { NextRequest } from 'next/server';
import { describe, expect, it } from 'vitest';
import { middleware } from '../middleware';

const PRIVADAS = [
  '/agentes',
  '/aprobaciones',
  '/auditoria',
  '/puntos',
  '/piezas',
  '/mi-comercio',
  '/contenido',
  '/promociones',
  '/tablero',
  '/perfil',
];

function pedir(path: string, conSesion: boolean): NextRequest {
  const headers = new Headers();
  if (conSesion) headers.set('cookie', 'tarjeta_sesion=1');
  return new NextRequest(`http://localhost${path}`, { headers });
}

describe('middleware de rutas privadas', () => {
  it.each(PRIVADAS)('%s sin sesión redirige a /login', (path) => {
    const res = middleware(pedir(path, false));
    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toContain('/login');
  });

  it.each(PRIVADAS)('%s con sesión deja pasar', (path) => {
    const res = middleware(pedir(path, true));
    // NextResponse.next() no redirige.
    expect(res.headers.get('location')).toBeNull();
  });
});
