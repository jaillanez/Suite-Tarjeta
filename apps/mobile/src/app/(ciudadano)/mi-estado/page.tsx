'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { EstadoCiudadano, EstadoPadron } from '@tarjeta/api-client';
import { Button, type Nivel, NivelBadge } from '@tarjeta/ui';
import { CerrarSesion } from '@/components/CerrarSesion';
import { api } from '@/lib/api';
import { esSesionVencida, mensajeDeError } from '@/lib/errores';

export default function MiEstadoPage() {
  const router = useRouter();
  const [estado, setEstado] = useState<EstadoCiudadano | null>(null);
  const [padron, setPadron] = useState<EstadoPadron | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      const [e, p] = await Promise.all([api.miEstado(), api.estadoPadron()]);
      setEstado(e);
      setPadron(p);
    } catch (err) {
      if (esSesionVencida(err)) router.push('/login');
      else setError(mensajeDeError(err));
    }
  }, [router]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function actualizar(): Promise<void> {
    setMsg(null);
    try {
      await api.actualizarEstado();
      await cargar();
    } catch (err) {
      setMsg(mensajeDeError(err));
    }
  }

  if (error && !estado) {
    return (
      <main className="mx-auto max-w-md space-y-3 p-4" role="alert">
        <p className="text-sm text-destructive">{error}</p>
        <Button size="sm" variant="outline" onClick={() => void cargar()}>
          Reintentar
        </Button>
      </main>
    );
  }

  if (!estado) {
    return <p className="p-4 text-muted-foreground">Cargando…</p>;
  }

  const nivel = estado.nivel as Nivel;
  const esBlack = nivel === 'BLACK';

  return (
    <main className="mx-auto max-w-md space-y-4 p-4">
      <h1 className="flex items-center gap-2 text-lg font-semibold">
        Mi estado <NivelBadge nivel={nivel} />
      </h1>
      {esBlack ? (
        <p className="text-sm">Estás al día con el municipio. Accedés a los mejores beneficios.</p>
      ) : (
        <p className="text-sm">Si estás al día con el municipio pasás a Black y accedés a más beneficios.</p>
      )}
      {padron?.consultado ? (
        <p className="text-xs text-muted-foreground">
          Actualizado hace {padron.horas_desde_consulta ?? 0} horas.
        </p>
      ) : null}
      {msg ? <p className="text-xs text-muted-foreground">{msg}</p> : null}
      <Button size="sm" onClick={actualizar}>
        Actualizar mi estado
      </Button>
      <div className="border-t border-border pt-4">
        <CerrarSesion />
      </div>
    </main>
  );
}
