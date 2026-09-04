'use client';

import { useCallback, useEffect, useState } from 'react';
import type {
  BilleterasOut,
  ComprobanteInventarioOut,
  ItemCatalogoOut,
  LotePorVencerOut,
} from '@tarjeta/api-client';
import { Button } from '@tarjeta/ui';
import { api } from '@/lib/api';

export default function PuntosPage() {
  const [billeteras, setBilleteras] = useState<BilleterasOut | null>(null);
  const [porVencer, setPorVencer] = useState<LotePorVencerOut[]>([]);
  const [catalogo, setCatalogo] = useState<ItemCatalogoOut[]>([]);
  const [comprobantes, setComprobantes] = useState<ComprobanteInventarioOut[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    const [b, v, c, comp] = await Promise.all([
      api.misBilleteras(),
      api.puntosPorVencer(30),
      api.catalogoPuntos(),
      api.misComprobantesPuntos(),
    ]);
    setBilleteras(b);
    setPorVencer(v);
    setCatalogo(c);
    setComprobantes(comp);
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function canjear(idItem: string): Promise<void> {
    setError(null);
    setMsg(null);
    try {
      const c = await api.canjearInventario(idItem);
      setMsg(`¡Canje listo! Código ${c.codigo}. Presentalo para retirar.`);
      await cargar();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo canjear.');
    }
  }

  if (!billeteras) return <p className="p-4 text-muted-foreground">Cargando…</p>;

  return (
    <main className="mx-auto max-w-md space-y-5 p-4">
      <h1 className="text-lg font-semibold">Mis puntos</h1>

      {/* Dos billeteras SIEMPRE separadas: PC y PM nunca se mezclan (§09.7). */}
      <section className="rounded-lg border border-border p-4">
        <h2 className="text-sm font-semibold text-muted-foreground">Puntos Municipales (PM)</h2>
        <p className="mt-1 text-3xl font-semibold">{billeteras.pm}</p>
        <p className="text-xs text-muted-foreground">Se canjean por beneficios del municipio.</p>
      </section>

      <section className="rounded-lg border border-border p-4">
        <h2 className="text-sm font-semibold text-muted-foreground">Puntos Comercio (PC)</h2>
        {billeteras.pc.length === 0 ? (
          <p className="mt-1 text-sm text-muted-foreground">Todavía no tenés puntos de comercio.</p>
        ) : (
          <ul className="mt-2 space-y-1">
            {billeteras.pc.map((w) => (
              <li key={w.id_comercio} className="flex justify-between text-sm">
                <span className="truncate text-muted-foreground">Comercio {w.id_comercio.slice(0, 8)}…</span>
                <span className="font-semibold">{w.saldo}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-2 text-xs text-muted-foreground">
          Cada saldo se usa solo en el comercio que lo emitió.
        </p>
      </section>

      {porVencer.length > 0 ? (
        <section className="rounded-lg border border-amber-500/50 bg-amber-50 p-4 dark:bg-amber-950/20">
          <h2 className="text-sm font-semibold">Por vencer</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {porVencer.map((l, i) => (
              <li key={i} className={l.dias_restantes <= 7 ? 'font-semibold text-red-600' : ''}>
                {l.saldo_restante} {l.tipo_moneda} vencen en {l.dias_restantes} día
                {l.dias_restantes === 1 ? '' : 's'} ({l.vence_en})
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section>
        <h2 className="text-sm font-semibold">Canjeá tus PM</h2>
        {catalogo.length === 0 ? (
          <p className="mt-1 text-sm text-muted-foreground">No hay ítems disponibles por ahora.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {catalogo.map((item) => (
              <li key={item.id} className="rounded-lg border border-border p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{item.titulo}</p>
                    <p className="text-xs text-muted-foreground">{item.descripcion}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold">{item.costo_pm} PM</p>
                    <Button
                      size="sm"
                      disabled={billeteras.pm < item.costo_pm}
                      onClick={() => void canjear(item.id)}
                    >
                      Canjear
                    </Button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {comprobantes.length > 0 ? (
        <section>
          <h2 className="text-sm font-semibold">Mis comprobantes</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {comprobantes.map((c) => (
              <li key={c.id} className="flex justify-between">
                <span className="text-muted-foreground">{c.titulo_item}</span>
                <span className="font-mono">{c.codigo}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {msg ? <p className="text-sm text-green-600">{msg}</p> : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </main>
  );
}
