'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { FeedOut } from '@tarjeta/api-client';
import { Button } from '@tarjeta/ui';
import { api } from '@/lib/api';
import { esSesionVencida, mensajeDeError } from '@/lib/errores';

// Los tres grupos del feed comparten estos campos (cada uno agrega alguno propio);
// la tarjeta solo usa este subconjunto, así sirve para los tres.
type PromoVista = {
  id: string;
  titulo: string;
  descripcion: string;
  mecanica: string;
  segmento: string;
  valor_platino: number | null;
  valor_black: number;
  destacada_municipal: boolean;
};

const SECCIONES: { clave: keyof FeedOut; titulo: string }[] = [
  { clave: 'nuevos_esta_semana', titulo: 'Nuevos esta semana' },
  { clave: 'exclusivos_black', titulo: 'Exclusivos Black' },
  { clave: 'vencen_pronto', titulo: 'Vencen pronto' },
];

function beneficio(p: PromoVista): string {
  if (p.mecanica === 'PORCENTAJE') {
    const platino = p.valor_platino ?? p.valor_black;
    return platino === p.valor_black ? `${p.valor_black}%` : `${platino}%–${p.valor_black}%`;
  }
  return 'Beneficio';
}

function PromoCard({ p }: { p: PromoVista }) {
  const soloBlack = p.segmento === 'SOLO_BLACK';
  return (
    <div className="flex items-center gap-4 rounded-xl border border-border bg-card p-4">
      <span className="flex size-14 shrink-0 flex-col items-center justify-center rounded-lg bg-brand-50 text-brand-700">
        <span className="text-base font-bold leading-none">{beneficio(p)}</span>
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold">{p.titulo || 'Promoción'}</p>
        {p.descripcion ? (
          <p className="truncate text-sm text-muted-foreground">{p.descripcion}</p>
        ) : null}
        <div className="mt-1 flex flex-wrap gap-1.5">
          {soloBlack ? (
            <span className="rounded-full bg-nivel-black px-2 py-0.5 text-[11px] font-semibold text-nivel-black-foreground">
              Black
            </span>
          ) : null}
          {p.destacada_municipal ? (
            <span className="rounded-full bg-brand-100 px-2 py-0.5 text-[11px] font-semibold text-brand-900">
              Destacada
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default function BeneficiosPage() {
  const router = useRouter();
  const [feed, setFeed] = useState<FeedOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      setFeed(await api.feedPromos());
    } catch (err) {
      if (esSesionVencida(err)) router.push('/login');
      else setError(mensajeDeError(err));
    }
  }, [router]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const hayAlgo = feed !== null && SECCIONES.some((s) => feed[s.clave].length > 0);

  return (
    <main className="mx-auto max-w-md space-y-6 p-5 pt-[calc(env(safe-area-inset-top)+1rem)]">
      <h1 className="text-xl font-bold">Beneficios</h1>

      {error && !feed ? (
        <div className="space-y-3" role="alert">
          <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
          <Button variant="outline" onClick={() => void cargar()}>
            Reintentar
          </Button>
        </div>
      ) : null}

      {!feed && !error ? <p className="text-muted-foreground">Cargando…</p> : null}

      {feed && !hayAlgo ? (
        <p className="text-muted-foreground">Todavía no hay beneficios publicados para mostrar.</p>
      ) : null}

      {feed
        ? SECCIONES.map(({ clave, titulo }) =>
            feed[clave].length > 0 ? (
              <section key={clave} className="space-y-3">
                <h2 className="text-sm font-semibold text-muted-foreground">{titulo}</h2>
                <ul className="space-y-3">
                  {feed[clave].map((p) => (
                    <li key={p.id}>
                      <PromoCard p={p} />
                    </li>
                  ))}
                </ul>
              </section>
            ) : null,
          )
        : null}
    </main>
  );
}
