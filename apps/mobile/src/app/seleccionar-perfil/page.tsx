'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Perfil } from '@tarjeta/api-client';
import { api } from '@/lib/api';
import { guardarPerfilActivo, guardarSesion } from '@/lib/session';

// Selector de contexto (§11.2): cambio de un toque, sin volver a iniciar sesión.
const DESTINO: Record<string, string> = {
  CIUDADANO: '/inicio',
  COMERCIO: '/caja',
  MUNICIPAL: '/operacion',
};

export default function SeleccionarPerfilPage() {
  const router = useRouter();
  const [perfiles, setPerfiles] = useState<Perfil[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .perfiles()
      .then(setPerfiles)
      .catch(() => router.push('/login'));
  }, [router]);

  async function activar(clave: string, tipo: string): Promise<void> {
    setError(null);
    try {
      const tokens = await api.activarPerfil(clave);
      await guardarSesion(tokens.access_token, tokens.refresh_token);
      await guardarPerfilActivo(clave);
      router.push(DESTINO[tipo] ?? '/inicio');
    } catch {
      setError('No pudimos activar ese perfil.');
    }
  }

  return (
    <main className="mx-auto max-w-md space-y-4 p-4">
      <h1 className="text-lg font-semibold">Elegí con qué perfil entrás</h1>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <ul className="grid gap-3">
        {perfiles.map((p) => (
          <li key={p.clave}>
            <button
              type="button"
              className="w-full rounded-lg border border-border p-4 text-left"
              onClick={() => activar(p.clave, p.tipo)}
            >
              <span className="font-medium">{p.tipo}</span>
              {p.rol ? <span className="block text-sm text-muted-foreground">{p.rol}</span> : null}
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}
