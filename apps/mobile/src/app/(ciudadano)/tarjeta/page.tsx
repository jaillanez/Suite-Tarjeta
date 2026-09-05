'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { EstadoCiudadano, PersonaMe, TokenOut, TransaccionOut } from '@tarjeta/api-client';
import { Button, type Nivel, TarjetaCredencial } from '@tarjeta/ui';
import { QrToken } from '@/components/QrToken';
import { api } from '@/lib/api';
import { esSesionVencida, mensajeDeError } from '@/lib/errores';

const municipio = process.env.NEXT_PUBLIC_MUNICIPIO_NOMBRE ?? 'Rivadavia';

function tokenVigente(lote: TokenOut[]): string | null {
  const ahora = Math.floor(Date.now() / 1000);
  const t = lote.find((x) => x.valido_desde <= ahora && ahora < x.valido_hasta);
  return t ? t.token : null;
}

export default function TarjetaPage() {
  const router = useRouter();
  const [me, setMe] = useState<PersonaMe | null>(null);
  const [estado, setEstado] = useState<EstadoCiudadano | null>(null);
  const [lote, setLote] = useState<TokenOut[]>([]);
  const [tokenActual, setTokenActual] = useState<string | null>(null);
  const [codigo, setCodigo] = useState<string | null>(null);
  const [pendiente, setPendiente] = useState<TransaccionOut | null>(null);
  const [usarPuntos, setUsarPuntos] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      const [m, e, tokens] = await Promise.all([
        api.me(),
        api.miEstado(),
        api.misTokensCanje(),
      ]);
      setMe(m);
      setEstado(e);
      setLote(tokens); // pregenerados para 2 h: sirven aunque después no haya señal
    } catch (err) {
      if (esSesionVencida(err)) router.push('/login');
      else setError(mensajeDeError(err));
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
    setError(null);
    setMsg(null);
    const puntos = Math.max(0, Number(usarPuntos) || 0);
    try {
      const aplicada = await api.confirmarCanje(pendiente.id, puntos);
      setPendiente(null);
      setUsarPuntos('');
      const usados = aplicada.puntos_consumidos;
      setMsg(usados > 0 ? `¡Aplicado! Usaste ${usados} puntos.` : '¡Descuento aplicado!');
    } catch (err) {
      // §12.5: el error al confirmar NO se ignora. Se mantiene la operación pendiente para reintentar.
      if (esSesionVencida(err)) router.push('/login');
      else setError(mensajeDeError(err));
    }
  }

  async function rechazar(): Promise<void> {
    if (!pendiente) return;
    setError(null);
    try {
      await api.rechazarCanje(pendiente.id);
      setPendiente(null);
    } catch (err) {
      if (esSesionVencida(err)) router.push('/login');
      else setError(mensajeDeError(err));
    }
  }

  async function generarCodigo(): Promise<void> {
    setError(null);
    try {
      const r = await api.generarCodigoCanje();
      setCodigo(r.codigo);
    } catch (err) {
      if (esSesionVencida(err)) router.push('/login');
      else setError(mensajeDeError(err));
    }
  }

  if (error && !estado) {
    return (
      <main className="mx-auto max-w-md space-y-3 p-4" role="alert">
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" onClick={() => void cargar()}>
          Reintentar
        </Button>
      </main>
    );
  }

  if (!estado) return <p className="p-4 text-muted-foreground">Cargando…</p>;

  const nombreTitular = me ? `${me.nombre} ${me.apellido}`.trim() : '';

  return (
    <main className="mx-auto max-w-md space-y-4 p-4">
      <h1 className="text-lg font-semibold">Mi tarjeta</h1>
      <TarjetaCredencial
        nombre={nombreTitular || '—'}
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
          {/* §09.4: el ciudadano decide si usa puntos y ve el total resultante antes de aceptar. */}
          <label className="mt-2 block text-sm">
            Usar puntos de este comercio
            <input
              type="number"
              min={0}
              inputMode="numeric"
              aria-label="Puntos a usar en esta compra"
              value={usarPuntos}
              onChange={(e) => setUsarPuntos(e.target.value)}
              className="mt-1 w-full rounded-md border border-border bg-background p-2"
              placeholder="0"
            />
          </label>
          <p className="mt-2 text-2xl font-semibold">
            Pagás ${Math.max(0, pendiente.total_pagar - (Number(usarPuntos) || 0))}
          </p>
          <div className="mt-3 flex gap-2">
            <Button onClick={confirmar}>Aceptar</Button>
            <Button variant="outline" onClick={rechazar}>
              Rechazar
            </Button>
          </div>
          {error ? (
            <p className="mt-2 text-sm text-destructive" role="alert">
              {error}
            </p>
          ) : null}
        </div>
      ) : (
        <div className="rounded-lg border border-border p-4 text-center">
          <p className="text-sm text-muted-foreground">Mostrá este código en la caja</p>
          {/* §12.2-B: QR escaneable (no texto plano). El token rota cada 45 s. */}
          <QrToken token={tokenActual} />
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
      {error && !pendiente ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
      <p className="text-sm text-muted-foreground">Estado: {estado.estado_tarjeta}</p>
    </main>
  );
}
