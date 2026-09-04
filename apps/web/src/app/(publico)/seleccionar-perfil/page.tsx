'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Perfil } from '@tarjeta/api-client';
import { Button } from '@tarjeta/ui';
import { api } from '@/lib/api';
import { esSesionVencida, mensajeDeError } from '@/lib/errores';
import { guardarSesion } from '@/lib/session';

const DESTINO: Record<string, string> = {
  CIUDADANO: '/beneficios',
  COMERCIO: '/promociones',
  MUNICIPAL: '/tablero',
};

export default function SeleccionarPerfilPage() {
  const router = useRouter();
  const [perfiles, setPerfiles] = useState<Perfil[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .perfiles()
      .then(setPerfiles)
      .catch((err: unknown) => {
        if (esSesionVencida(err)) router.push('/login');
        else setError(mensajeDeError(err));
      });
  }, [router]);

  async function activar(clave: string, tipo: string): Promise<void> {
    setError(null);
    try {
      const tokens = await api.activarPerfil(clave);
      guardarSesion(tokens.access_token, tokens.refresh_token);
      router.push(DESTINO[tipo] ?? '/');
    } catch (err) {
      if (esSesionVencida(err)) router.push('/login');
      else setError(mensajeDeError(err));
    }
  }

  return (
    <section className="mx-auto max-w-md space-y-4">
      <h1 className="text-2xl font-semibold">Elegí con qué perfil entrás</h1>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <ul className="grid gap-3">
        {perfiles.map((p) => (
          <li key={p.clave}>
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={() => activar(p.clave, p.tipo)}
            >
              {p.tipo}
              {p.rol ? ` · ${p.rol}` : ''}
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}
