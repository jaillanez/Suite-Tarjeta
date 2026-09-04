'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { EstadoCiudadano, TokenOut, TransaccionOut } from '@tarjeta/api-client';
import { Button, type Nivel, TarjetaCredencial } from '@tarjeta/ui';
import { api } from '@/lib/api';

const municipio = process.env.NEXT_PUBLIC_MUNICIPIO_NOMBRE ?? 'Municipio';

function tokenVigente(lote: TokenOut[]): string | null {
  const ahora = Math.floor(Date.now() / 1000);
  const t = lote.find((x) => x.valido_desde <= ahora && ahora < x.valido_hasta);
  return t ? t.token : null;
}

export default function TarjetaPage() {
  const router = useRouter();
  const [estado, setEstado] = useState<EstadoCiudadano | null>(null);
  const [lote, setLote] = useState<TokenOut[]>([]);
  const [tokenActual, setTokenActual] = useState<string | null>(null);
  const [codigo, setCodigo] = useState<string | null>(null);
  const [pendiente, setPendiente] = useState<TransaccionOut | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      const [e, tokens] = await Promise.all([api.miEstado(), api.misTokensCanje()]);
      setEstado(e);
      setLote(tokens); // pregenerados para 2 h: sirven aunque después no haya señal
    } catch {
      router.push('/login');
    }
  }, [router]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  // El QR rota cada 45 s: se elige el token de la ventana actual del lote pregenerado.
  useEffect(() => {
    const tick = () => setTokenActual(tokenVigente(lote));
    tick();
    const id = window.setInterval(tick, 5000);
    return () => window.clearInterval(id);
  }, [lote]);

  // Sin canal de notificaciones: la app consulta si hay una operación esperando confirmación.
  useEffect(() => {
    const poll = async () => {
      try {
        const pend = await api.misPendientesCanje();
        setPendiente(pend[0] ?? null);
      } catch {
        // ignore
      }
    };
    void poll();
    const id = window.setInterval(poll, 4000);
    return () => window.clearInterval(id);
  }, []);

  async function confirmar(): Promise<void> {
    if (!pendiente) return;
    await api.confirmarCanje(pendiente.id);
    setPendiente(null);
    setMsg('¡Descuento aplicado!');
  }

  async function rechazar(): Promise<void> {
    if (!pendiente) return;
    await api.rechazarCanje(pendiente.id);
    setPendiente(null);
  }

  async function generarCodigo(): Promise<void> {
    const r = await api.generarCodigoCanje();
    setCodigo(r.codigo);
  }

  if (!estado) return <p className="p-4 text-muted-foreground">Cargando…</p>;

  return (
    <main className="mx-auto max-w-md space-y-4 p-4">
      <h1 className="text-lg font-semibold">Mi tarjeta</h1>
      <TarjetaCredencial
        nombre="Titular"
        numero={estado.numero_tarjeta}
        nivel={estado.nivel as Nivel}
        municipio={municipio}
      />

      {/* Operación esperando confirmación (§08.3) */}
      {pendiente ? (
        <div className="rounded-lg border-2 border-primary p-4">
          <p className="font-semibold">Confirmá tu compra</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Monto ${pendiente.monto_bruto} · Descuento ${pendiente.descuento}
          </p>
          <p className="text-2xl font-semibold">Pagás ${pendiente.total_pagar}</p>
          <div className="mt-3 flex gap-2">
            <Button onClick={confirmar}>Aceptar</Button>
            <Button variant="outline" onClick={rechazar}>
              Rechazar
            </Button>
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-border p-4 text-center">
          <p className="text-sm text-muted-foreground">Mostrá este código en la caja</p>
          {/* En la app real esto se renderiza como QR; el token rota cada 45 s. */}
          <p className="mt-2 break-all font-mono text-xs">{tokenActual ?? '…'}</p>
          <div className="mt-3">
            <Button size="sm" variant="outline" onClick={generarCodigo}>
              Generar código de 6 dígitos
            </Button>
            {codigo ? (
              <p className="mt-2 text-3xl font-semibold tracking-widest">{codigo}</p>
            ) : null}
          </div>
        </div>
      )}

      {msg ? <p className="text-sm text-green-600">{msg}</p> : null}
      <p className="text-sm text-muted-foreground">Estado: {estado.estado_tarjeta}</p>
    </main>
  );
}
