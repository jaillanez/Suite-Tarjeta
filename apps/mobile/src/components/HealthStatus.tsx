'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

type Estado = 'cargando' | 'ok' | 'error';

const COLOR: Record<Estado, string> = {
  cargando: 'bg-muted text-muted-foreground',
  ok: 'bg-nivel-general text-nivel-general-foreground',
  error: 'bg-destructive text-white',
};

const ETIQUETA: Record<Estado, string> = {
  cargando: 'API…',
  ok: 'API OK',
  error: 'API caída',
};

/** Consumo real de /health del backend (fetch del lado del cliente: la app es export estático). */
export function HealthStatus() {
  const [estado, setEstado] = useState<Estado>('cargando');

  useEffect(() => {
    let activo = true;
    api
      .health()
      .then((r) => activo && setEstado(r.status === 'ok' ? 'ok' : 'error'))
      .catch(() => activo && setEstado('error'));
    return () => {
      activo = false;
    };
  }, []);

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${COLOR[estado]}`}
      role="status"
      aria-live="polite"
    >
      <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />
      {ETIQUETA[estado]}
    </span>
  );
}
