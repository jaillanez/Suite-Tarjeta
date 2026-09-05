'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  ApiError,
  type components,
  type ResolverOut,
  type TransaccionOut,
} from '@tarjeta/api-client';
import { Button, Input, Label } from '@tarjeta/ui';
import { api } from '@/lib/api';

type Fase = 'cobrar' | 'opciones' | 'esperando' | 'resultado';

/**
 * Caja del cajero (§08): con el turno abierto, cobra una compra aplicando el beneficio.
 * El ciudadano genera un código de 6 dígitos en su tarjeta; el cajero carga monto + código,
 * ve el descuento, inicia la operación y el ciudadano la confirma en su teléfono.
 * (El escaneo del QR queda para cuando esté cableado el plugin de cámara.)
 */
export function CajaOperacion({ idSucursal }: { idSucursal: string }) {
  const [fase, setFase] = useState<Fase>('cobrar');
  const [monto, setMonto] = useState('');
  const [codigo, setCodigo] = useState('');
  const [resuelto, setResuelto] = useState<ResolverOut | null>(null);
  const [tx, setTx] = useState<TransaccionOut | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const montoNum = Math.max(0, Math.floor(Number(monto) || 0));

  async function buscar(): Promise<void> {
    if (montoNum <= 0) {
      setMsg('Ingresá el monto de la compra.');
      return;
    }
    if (codigo.length < 6) {
      setMsg('Pedí al ciudadano su código de 6 dígitos.');
      return;
    }
    setMsg(null);
    setOcupado(true);
    try {
      const r = await api.resolverCanje({
        via: 'CODIGO',
        monto: montoNum,
        id_sucursal: idSucursal,
        codigo,
      });
      setResuelto(r);
      setFase('opciones');
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo identificar al ciudadano.');
    } finally {
      setOcupado(false);
    }
  }

  async function iniciar(idPromocion: string | null): Promise<void> {
    setMsg(null);
    setOcupado(true);
    try {
      // exactOptionalPropertyTypes: id_promocion se agrega solo si hay promoción (no como undefined).
      const body: components['schemas']['IniciarIn'] = {
        via: 'CODIGO',
        monto: montoNum,
        id_sucursal: idSucursal,
        clave_idempotencia: crypto.randomUUID(),
        codigo,
      };
      if (idPromocion) body.id_promocion = idPromocion;
      const t = await api.iniciarCanje(body);
      setTx(t);
      setFase(t.estado === 'PENDIENTE_CONFIRMACION' ? 'esperando' : 'resultado');
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo iniciar la operación.');
    } finally {
      setOcupado(false);
    }
  }

  // Mientras espera, consulta si el ciudadano ya confirmó/rechazó en su teléfono.
  useEffect(() => {
    if (fase !== 'esperando' || !tx) return;
    let vivo = true;
    const id = window.setInterval(async () => {
      try {
        const t = await api.estadoOperacionCanje(tx.id);
        if (vivo && t.estado !== 'PENDIENTE_CONFIRMACION') {
          setTx(t);
          setFase('resultado');
        }
      } catch {
        // reintentamos en el próximo tick
      }
    }, 2500);
    return () => {
      vivo = false;
      window.clearInterval(id);
    };
  }, [fase, tx]);

  const reiniciar = useCallback(() => {
    setFase('cobrar');
    setMonto('');
    setCodigo('');
    setResuelto(null);
    setTx(null);
    setMsg(null);
  }, []);

  if (fase === 'cobrar') {
    return (
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void buscar();
        }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="monto">Monto de la compra ($)</Label>
          <Input
            id="monto"
            inputMode="numeric"
            value={monto}
            onChange={(e) => setMonto(e.target.value)}
            placeholder="0"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="codigo">Código del ciudadano (6 dígitos)</Label>
          <Input
            id="codigo"
            inputMode="numeric"
            maxLength={6}
            className="text-center text-2xl tracking-[0.4em]"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ''))}
            placeholder="––––––"
          />
          <p className="text-xs text-muted-foreground">
            El ciudadano lo genera en su tarjeta con “Generar código de 6 dígitos”.
          </p>
        </div>
        {msg ? (
          <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
            {msg}
          </p>
        ) : null}
        <Button type="submit" size="lg" className="w-full" disabled={ocupado}>
          Buscar beneficio
        </Button>
      </form>
    );
  }

  if (fase === 'opciones' && resuelto) {
    return (
      <div className="space-y-4">
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="font-semibold">
            {resuelto.nombre} {resuelto.inicial_apellido}.
          </p>
          <p className="text-sm text-muted-foreground">
            Nivel {resuelto.nivel} · compra ${montoNum}
          </p>
        </div>
        {resuelto.opciones.length > 0 ? (
          <ul className="space-y-2">
            {resuelto.opciones.map((o) => (
              <li key={o.id_promocion}>
                <button
                  type="button"
                  disabled={ocupado}
                  onClick={() => void iniciar(o.id_promocion)}
                  className="w-full rounded-xl border border-border bg-card p-4 text-left transition-colors active:bg-accent disabled:opacity-50"
                >
                  <span className="block font-semibold">{o.titulo}</span>
                  <span className="block text-sm text-muted-foreground">
                    Descuento ${o.descuento} · paga ${o.total}
                    {o.puntos > 0 ? ` · +${o.puntos} pts` : ''}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">No hay una promoción aplicable.</p>
            <Button className="w-full" disabled={ocupado} onClick={() => void iniciar(null)}>
              Cobrar sin descuento
            </Button>
          </div>
        )}
        {msg ? (
          <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
            {msg}
          </p>
        ) : null}
        <Button variant="ghost" className="w-full" onClick={reiniciar}>
          Cancelar
        </Button>
      </div>
    );
  }

  if (fase === 'esperando') {
    return (
      <div className="space-y-3 py-6 text-center">
        <p className="text-lg font-semibold">Esperando confirmación…</p>
        <p className="text-sm text-muted-foreground">
          {resuelto?.nombre ?? 'El ciudadano'} tiene que aceptar la compra en su teléfono.
        </p>
        <Button variant="ghost" onClick={reiniciar}>
          Cancelar
        </Button>
      </div>
    );
  }

  // resultado
  const aplicada = tx?.estado === 'APLICADA';
  return (
    <div className="space-y-4 py-4 text-center">
      {aplicada ? (
        <>
          <p className="text-2xl font-bold text-brand-700">¡Descuento aplicado!</p>
          <div className="rounded-xl border border-border bg-card p-4 text-left">
            <p className="text-sm text-muted-foreground">Comprobante {tx?.numero_comprobante}</p>
            <p className="mt-1">Descuento: ${tx?.descuento}</p>
            <p className="text-lg font-semibold">Total a pagar: ${tx?.total_pagar}</p>
          </div>
        </>
      ) : (
        <p className="text-lg font-semibold text-destructive">
          Operación {tx?.estado === 'RECHAZADA' ? 'rechazada' : 'no aplicada'}.
        </p>
      )}
      <Button size="lg" className="w-full" onClick={reiniciar}>
        Nueva operación
      </Button>
    </div>
  );
}
