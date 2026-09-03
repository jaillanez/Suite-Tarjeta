'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { EstadoCiudadano } from '@tarjeta/api-client';
import { Button, type Nivel, TarjetaCredencial } from '@tarjeta/ui';
import { api } from '@/lib/api';

const municipio = process.env.NEXT_PUBLIC_MUNICIPIO_NOMBRE ?? 'Municipio';

export default function TarjetaPage() {
  const router = useRouter();
  const [estado, setEstado] = useState<EstadoCiudadano | null>(null);

  const cargar = useCallback(async () => {
    try {
      setEstado(await api.miEstado());
    } catch {
      router.push('/login');
    }
  }, [router]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function bloquear(): Promise<void> {
    await api.bloquearTarjeta();
    await cargar();
  }

  if (!estado) {
    return <p className="p-4 text-muted-foreground">Cargando…</p>;
  }

  return (
    <main className="mx-auto max-w-md space-y-4 p-4">
      <h1 className="text-lg font-semibold">Mi tarjeta</h1>
      <TarjetaCredencial
        nombre="Titular"
        numero={estado.numero_tarjeta}
        nivel={estado.nivel as Nivel}
        municipio={municipio}
      />
      <p className="text-sm text-muted-foreground">Estado: {estado.estado_tarjeta}</p>
      {estado.estado_tarjeta === 'ACTIVA' ? (
        <Button size="sm" variant="outline" onClick={bloquear}>
          Bloquear por robo o pérdida
        </Button>
      ) : null}
    </main>
  );
}
