'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Building2, ChevronRight, Store, UserRound } from 'lucide-react';
import type { Perfil } from '@tarjeta/api-client';
import { Marca } from '@tarjeta/ui';
import { api } from '@/lib/api';
import { esSesionVencida, mensajeDeError } from '@/lib/errores';
import { guardarPerfilActivo, guardarSesion } from '@/lib/session';

// Selector de contexto (§11.2): cambio de un toque, sin volver a iniciar sesión.
const DESTINO: Record<string, string> = {
  CIUDADANO: '/inicio',
  COMERCIO: '/caja',
  MUNICIPAL: '/operacion',
};

const ICONO: Record<string, typeof UserRound> = {
  CIUDADANO: UserRound,
  COMERCIO: Store,
  MUNICIPAL: Building2,
};

const ETIQUETA: Record<string, string> = {
  CIUDADANO: 'Ciudadano',
  COMERCIO: 'Comercio',
  MUNICIPAL: 'Municipal',
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
      await guardarSesion(tokens.access_token, tokens.refresh_token);
      await guardarPerfilActivo(clave);
      router.push(DESTINO[tipo] ?? '/inicio');
    } catch (err) {
      if (esSesionVencida(err)) router.push('/login');
      else setError(mensajeDeError(err));
    }
  }

  return (
    <main className="mx-auto max-w-md space-y-6 p-6">
      <header className="flex flex-col items-center gap-3 pt-6 text-center">
        <Marca variante="wordmark" alto={38} />
        <h1 className="text-lg font-semibold">Elegí con qué perfil entrás</h1>
      </header>
      {error ? (
        <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
      <ul className="grid gap-3">
        {perfiles.map((p) => {
          const Icono = ICONO[p.tipo] ?? UserRound;
          return (
            <li key={p.clave}>
              <button
                type="button"
                className="flex w-full items-center gap-4 rounded-xl border border-border bg-card p-4 text-left transition-colors active:bg-accent"
                onClick={() => activar(p.clave, p.tipo)}
              >
                <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-700">
                  <Icono className="size-5" aria-hidden="true" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold">{ETIQUETA[p.tipo] ?? p.tipo}</span>
                  {p.rol ? (
                    <span className="block text-sm text-muted-foreground">{p.rol}</span>
                  ) : null}
                </span>
                <ChevronRight className="size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
              </button>
            </li>
          );
        })}
      </ul>
    </main>
  );
}
