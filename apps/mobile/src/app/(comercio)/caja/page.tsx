'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { UserRound } from 'lucide-react';
import { ApiError, type CajeroCortoOut } from '@tarjeta/api-client';
import { Button, Input, Label, Marca } from '@tarjeta/ui';
import { api } from '@/lib/api';
import { getHuellaDispositivo, guardarPerfilActivo, guardarSesion } from '@/lib/session';

export default function CajaPage() {
  const router = useRouter();
  const [huella, setHuella] = useState<string | null>(null);
  const [cajeros, setCajeros] = useState<CajeroCortoOut[] | null>(null); // null = cargando
  const [seleccion, setSeleccion] = useState<CajeroCortoOut | null>(null);
  const [pin, setPin] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [espera, setEspera] = useState(0); // segundos restantes del bloqueo por dispositivo
  const [cargaError, setCargaError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setCargaError(null);
    try {
      const h = await getHuellaDispositivo();
      setHuella(h);
      const lista = await api.cajeroLista(h);
      setCajeros(lista);
      // Un solo cajero registrado: salteamos el selector y vamos directo al PIN.
      if (lista.length === 1) setSeleccion(lista[0] ?? null);
    } catch (e) {
      setCajeros([]);
      setCargaError(e instanceof ApiError ? e.message : 'No se pudo cargar la caja.');
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  // Cuenta regresiva del bloqueo (3 intentos fallidos -> 30 s).
  useEffect(() => {
    if (espera <= 0) return;
    const id = window.setInterval(() => setEspera((s) => Math.max(0, s - 1)), 1000);
    return () => window.clearInterval(id);
  }, [espera]);

  async function ingresar(): Promise<void> {
    if (!seleccion || !huella || espera > 0) return;
    setMsg(null);
    try {
      const tokens = await api.cajeroLogin(seleccion.id_usuario, pin, huella);
      await guardarSesion(tokens.access_token, tokens.refresh_token);
      await guardarPerfilActivo('COMERCIO');
      router.push('/turno');
    } catch (e) {
      setPin('');
      if (e instanceof ApiError && e.status === 429) {
        setEspera(e.retryAfter ?? 30); // el backend manda los segundos en Retry-After
      } else {
        setMsg(e instanceof ApiError ? e.message : 'No se pudo ingresar.');
      }
    }
  }

  if (cajeros === null) {
    return <p className="p-6 text-muted-foreground">Cargando…</p>;
  }

  // Dispositivo sin cajeros registrados: mensaje claro (lo registra el encargado).
  if (cajeros.length === 0) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center gap-6 p-6 text-center">
        <Marca variante="wordmark" alto={40} className="mx-auto" />
        <div className="space-y-2">
          <h1 className="text-lg font-semibold">Caja no disponible</h1>
          <p className="text-sm text-muted-foreground">
            Este dispositivo todavía no está registrado para ningún cajero. El encargado tiene que
            registrarlo desde su cuenta.
          </p>
          {cargaError ? <p className="text-sm text-destructive">{cargaError}</p> : null}
        </div>
      </main>
    );
  }

  // Selector: varios cajeros en el dispositivo y ninguno elegido todavía.
  if (!seleccion) {
    return (
      <main className="mx-auto max-w-sm space-y-6 p-6">
        <div className="flex flex-col items-center gap-3 text-center">
          <Marca variante="wordmark" alto={40} />
          <h1 className="text-lg font-semibold">¿Quién abre la caja?</h1>
        </div>
        <ul className="space-y-3">
          {cajeros.map((c) => (
            <li key={c.id_usuario}>
              <button
                type="button"
                onClick={() => {
                  setSeleccion(c);
                  setMsg(null);
                }}
                className="flex w-full items-center gap-4 rounded-xl border border-border bg-card p-4 text-left transition-colors active:bg-accent"
              >
                <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-700">
                  <UserRound className="size-5" aria-hidden="true" />
                </span>
                <span className="font-semibold">{c.nombre}</span>
              </button>
            </li>
          ))}
        </ul>
      </main>
    );
  }

  const bloqueado = espera > 0;
  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center gap-6 p-6">
      <div className="flex flex-col items-center gap-2 text-center">
        <Marca variante="wordmark" alto={36} />
        <h1 className="text-lg font-semibold">{seleccion.nombre}</h1>
        <p className="text-sm text-muted-foreground">Ingresá tu PIN.</p>
      </div>
      <form
        className="space-y-4 rounded-2xl border border-border bg-card p-5 shadow-sm"
        onSubmit={(e) => {
          e.preventDefault();
          void ingresar();
        }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="pin">PIN</Label>
          <Input
            id="pin"
            type="password"
            inputMode="numeric"
            autoComplete="off"
            maxLength={6}
            aria-label="PIN"
            className="text-center text-2xl tracking-[0.5em]"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            disabled={bloqueado}
            required
          />
        </div>
        {bloqueado ? (
          <p
            className="rounded-lg bg-destructive/10 px-3 py-2 text-center text-sm text-destructive"
            role="alert"
            aria-live="polite"
          >
            Demasiados intentos. Probá de nuevo en {espera} s.
          </p>
        ) : msg ? (
          <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
            {msg}
          </p>
        ) : null}
        <Button type="submit" size="lg" className="w-full" disabled={bloqueado || pin.length < 4}>
          Ingresar
        </Button>
        {cajeros.length > 1 ? (
          <Button
            type="button"
            variant="ghost"
            className="w-full"
            onClick={() => {
              setSeleccion(null);
              setPin('');
              setMsg(null);
            }}
          >
            Elegir otro cajero
          </Button>
        ) : null}
      </form>
    </main>
  );
}
