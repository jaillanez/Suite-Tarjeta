'use client';

import { useEffect, useState } from 'react';
import { ApiError, type ComercioOut } from '@tarjeta/api-client';
import { Badge, Card, CardContent, CardHeader, CardTitle } from '@tarjeta/ui';
import { api } from '@/lib/api';

export default function PerfilComercioPage() {
  const [c, setC] = useState<ComercioOut | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .miComercio()
      .then(setC)
      .catch((e) => setErr(e instanceof ApiError ? e.message : 'No se pudo cargar el comercio.'));
  }, []);

  if (err) return <p className="text-sm text-destructive">{err}</p>;
  if (!c) return <p className="text-muted-foreground">Cargando…</p>;

  return (
    <Card className="mx-auto max-w-lg">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {c.nombre_fantasia || c.razon_social} <Badge>{c.estado}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1 text-sm">
        <p>
          <span className="text-muted-foreground">Razón social:</span> {c.razon_social}
        </p>
        <p>
          <span className="text-muted-foreground">CUIT:</span> {c.cuit}
        </p>
        <p>
          <span className="text-muted-foreground">Rubro:</span> {c.rubro || '—'}
        </p>
      </CardContent>
    </Card>
  );
}
