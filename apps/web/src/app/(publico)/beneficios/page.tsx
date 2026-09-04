'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ApiError, type FeedOut, type PromocionOut } from '@tarjeta/api-client';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
} from '@tarjeta/ui';
import { api } from '@/lib/api';

function beneficio(p: { mecanica: string; valor_black: number }): string {
  if (p.mecanica === 'PORCENTAJE') return `${p.valor_black}%`;
  if (p.mecanica === 'DOS_POR_UNO') return '2x1';
  if (p.mecanica === 'MONTO_FIJO') return `$${p.valor_black}`;
  return 'Beneficio';
}

function PromoCard({ p }: { p: PromocionOut }) {
  return (
    <Link href={`/promo/${p.id}`} className="block">
      <div className="flex items-center justify-between rounded-md border border-border px-3 py-2 hover:bg-muted">
        <div>
          <p className="font-medium">{p.titulo}</p>
          <p className="text-xs text-muted-foreground">{p.descripcion}</p>
        </div>
        <div className="flex items-center gap-2">
          {p.destacada_municipal ? <Badge>Destacado</Badge> : null}
          <span className="font-semibold text-primary">{beneficio(p)}</span>
        </div>
      </div>
    </Link>
  );
}

export default function BeneficiosPage() {
  const [texto, setTexto] = useState('');
  const [soloBlack, setSoloBlack] = useState(false);
  const [resultados, setResultados] = useState<PromocionOut[] | null>(null);
  const [feed, setFeed] = useState<FeedOut | null>(null);
  const [criterio, setCriterio] = useState('');

  useEffect(() => {
    api.rankingCriterio().then((m) => setCriterio(m.mensaje)).catch(() => {});
    // El feed personalizado necesita sesión; si no hay, se muestra solo el buscador.
    api.feedPromos().then(setFeed).catch(() => setFeed(null));
  }, []);

  const buscar = useCallback(async () => {
    try {
      setResultados(
        await api.buscarPromos({ texto: texto || undefined, solo_black: soloBlack || undefined }),
      );
    } catch (e) {
      if (e instanceof ApiError) setResultados([]);
    }
  }, [texto, soloBlack]);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Buscar beneficios</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Input
              placeholder="Buscar (sin importar tildes)"
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              className="grow"
            />
            <label className="flex items-center gap-1 text-sm">
              <input
                type="checkbox"
                aria-label="Solo Black"
                checked={soloBlack}
                onChange={(e) => setSoloBlack(e.target.checked)}
              />
              Solo Black
            </label>
            <Button size="sm" onClick={buscar}>
              Buscar
            </Button>
          </div>
          {resultados !== null ? (
            <div className="space-y-2">
              {resultados.length === 0 ? (
                <p className="text-sm text-muted-foreground">Sin resultados.</p>
              ) : (
                resultados.map((p) => <PromoCard key={p.id} p={p} />)
              )}
            </div>
          ) : null}
          {criterio ? <p className="text-xs text-muted-foreground">Orden: {criterio}</p> : null}
        </CardContent>
      </Card>

      {feed ? (
        <>
          {feed.nuevos_esta_semana.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Nuevos esta semana</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {feed.nuevos_esta_semana.map((p) => <PromoCard key={p.id} p={p} />)}
              </CardContent>
            </Card>
          ) : null}

          {feed.exclusivos_black.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Exclusivos Black</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {feed.exclusivos_black.map((p) =>
                  p.bloqueada ? (
                    <div
                      key={p.id}
                      className="flex items-center justify-between rounded-md border border-dashed border-border px-3 py-2 opacity-80"
                    >
                      <div>
                        <p className="font-medium">🔒 {p.titulo}</p>
                        <p className="text-xs text-muted-foreground">
                          Ponete al día y pasá a Black para desbloquearla.
                        </p>
                      </div>
                      <span className="font-semibold text-primary">{beneficio(p)}</span>
                    </div>
                  ) : (
                    <PromoCard key={p.id} p={p} />
                  ),
                )}
              </CardContent>
            </Card>
          ) : null}

          {feed.vencen_pronto.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Vencen pronto</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {feed.vencen_pronto.map((p) => <PromoCard key={p.id} p={p} />)}
              </CardContent>
            </Card>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
