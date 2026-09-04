'use client';

import { useEffect, useState } from 'react';
import type { PasivoComercioOut } from '@tarjeta/api-client';
import { Card, CardContent, CardHeader, CardTitle } from '@tarjeta/ui';
import { api } from '@/lib/api';

export default function ReportesPage() {
  const [pasivo, setPasivo] = useState<PasivoComercioOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .pasivoComercioPuntos()
      .then(setPasivo)
      .catch((e) => setError(e instanceof Error ? e.message : 'No se pudo cargar.'));
  }, []);

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Reportes</h1>

      {/* §09.7: el comercio tiene derecho a ver su pasivo de puntos. */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">Puntos emitidos</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{pasivo?.emitidos ?? '—'}</p>
            <p className="text-xs text-muted-foreground">Lo que otorgaste a tus clientes.</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">Puntos canjeados</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{pasivo?.canjeados ?? '—'}</p>
            <p className="text-xs text-muted-foreground">Lo que tus clientes ya usaron.</p>
          </CardContent>
        </Card>
      </div>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </section>
  );
}
