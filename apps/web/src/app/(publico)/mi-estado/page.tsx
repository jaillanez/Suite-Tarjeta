'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { EstadoCiudadano, EstadoPadron, PersonaMe } from '@tarjeta/api-client';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  type Nivel,
  NivelBadge,
  TarjetaCredencial,
} from '@tarjeta/ui';
import { api } from '@/lib/api';
import { esSesionVencida, mensajeDeError } from '@/lib/errores';

const municipio = process.env.NEXT_PUBLIC_MUNICIPIO_NOMBRE ?? 'Rivadavia';

export default function MiEstadoPage() {
  const router = useRouter();
  const [me, setMe] = useState<PersonaMe | null>(null);
  const [estado, setEstado] = useState<EstadoCiudadano | null>(null);
  const [padron, setPadron] = useState<EstadoPadron | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      const [m, e, p] = await Promise.all([api.me(), api.miEstado(), api.estadoPadron()]);
      setMe(m);
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
      setMsg('Estado actualizado.');
    } catch (err) {
      // El límite diario (429) tiene su propio mensaje; un 500/red no debe disfrazarse de límite.
      setMsg(mensajeDeError(err));
    }
  }

  async function bloquear(): Promise<void> {
    await api.bloquearTarjeta();
    await cargar();
  }

  if (error) {
    return (
      <div className="mx-auto max-w-md space-y-3" role="alert">
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" onClick={() => void cargar()}>
          Reintentar
        </Button>
      </div>
    );
  }

  if (!me || !estado) {
    return <p className="text-muted-foreground">Cargando…</p>;
  }

  const nivel = estado.nivel as Nivel;
  const esBlack = nivel === 'BLACK';
  const nombre = `${me.nombre} ${me.apellido}`.trim() || 'Titular';

  return (
    <div className="mx-auto max-w-md space-y-6">
      <TarjetaCredencial
        nombre={nombre}
        numero={estado.numero_tarjeta}
        nivel={nivel}
        municipio={municipio}
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Mi estado <NivelBadge nivel={nivel} />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {esBlack ? (
            <p>Estás al día con el municipio. Por eso accedés a los mejores beneficios.</p>
          ) : (
            <>
              <p>Si estás al día con el municipio pasás a Black y accedés a más beneficios.</p>
              <button type="button" className="block text-left text-primary underline">
                Ir al portal de pagos
              </button>
              <button type="button" className="block text-left text-primary underline">
                ¿Un familiar contribuyente? Sumate a su grupo familiar
              </button>
            </>
          )}
          {padron?.consultado ? (
            <p className="text-muted-foreground">
              Actualizado hace {padron.horas_desde_consulta ?? 0} horas.
            </p>
          ) : (
            <p className="text-muted-foreground">Estado sin consultar todavía.</p>
          )}
          {msg ? <p className="text-muted-foreground">{msg}</p> : null}
          <div className="flex gap-2">
            <Button size="sm" onClick={actualizar}>
              Actualizar mi estado
            </Button>
            {estado.estado_tarjeta === 'ACTIVA' ? (
              <Button size="sm" variant="outline" onClick={bloquear}>
                Bloquear tarjeta
              </Button>
            ) : (
              <span className="text-xs text-muted-foreground">
                Tarjeta {estado.estado_tarjeta}
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
