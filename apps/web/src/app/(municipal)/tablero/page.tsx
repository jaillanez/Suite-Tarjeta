'use client';

import { useEffect, useState } from 'react';
import { ApiError, type Recaudacion } from '@tarjeta/api-client';
import { Card, CardContent, CardHeader, CardTitle } from '@tarjeta/ui';
import { api } from '@/lib/api';

export default function TableroPage() {
  const [rec, setRec] = useState<Recaudacion | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .recaudacion()
      .then(setRec)
      .catch((e) => setErr(e instanceof ApiError ? e.message : 'No se pudo cargar el tablero.'));
  }, []);

  if (err) return <p className="text-sm text-destructive">{err}</p>;
  if (!rec) return <p className="text-muted-foreground">Cargando…</p>;

  const total = Object.values(rec.distribucion_por_nivel).reduce((a, b) => a + b, 0);

  return (
    <div className="grid gap-6 sm:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Impacto en recaudación</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-4xl font-semibold">{rec.transiciones_a_black_post_registro}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            ciudadanos que se pusieron al día (pasaron a Black) después de registrarse.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Distribución por nivel</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {total === 0 ? (
            <p className="text-muted-foreground">Sin ciudadanos todavía.</p>
          ) : (
            Object.entries(rec.distribucion_por_nivel).map(([nivel, n]) => (
              <div key={nivel} className="flex items-center justify-between gap-3">
                <span>{nivel}</span>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-32 overflow-hidden rounded bg-muted">
                    <div
                      className="h-full bg-primary"
                      style={{ width: `${Math.round((100 * n) / total)}%` }}
                    />
                  </div>
                  <span className="w-10 text-right tabular-nums">{n}</span>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
