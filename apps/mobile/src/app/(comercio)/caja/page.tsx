'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ApiError } from '@tarjeta/api-client';
import { api } from '@/lib/api';
import { getHuellaDispositivo, guardarPerfilActivo, guardarSesion } from '@/lib/session';

export default function CajaPage() {
  const router = useRouter();
  const [idUsuario, setIdUsuario] = useState('');
  const [pin, setPin] = useState('');
  const [msg, setMsg] = useState<string | null>(null);

  async function ingresar(): Promise<void> {
    setMsg(null);
    try {
      const huella = await getHuellaDispositivo();
      const tokens = await api.cajeroLogin(idUsuario.trim(), pin, huella);
      await guardarSesion(tokens.access_token, tokens.refresh_token);
      await guardarPerfilActivo('COMERCIO');
      router.push('/turno');
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo ingresar.');
    }
  }

  return (
    <section className="mx-auto max-w-sm space-y-4 p-4">
      <h1 className="text-xl font-semibold">Ingreso de cajero</h1>
      <p className="text-sm text-muted-foreground">
        Ingresá con tu PIN. Solo funciona en este dispositivo, que ya fue registrado por el
        encargado.
      </p>
      <div className="space-y-2">
        <label className="block text-sm" htmlFor="idu">
          Usuario (ID)
        </label>
        <input
          id="idu"
          aria-label="Usuario (ID)"
          className="w-full rounded-md border border-border px-3 py-2"
          value={idUsuario}
          onChange={(e) => setIdUsuario(e.target.value)}
        />
        <label className="block text-sm" htmlFor="pin">
          PIN
        </label>
        <input
          id="pin"
          type="password"
          inputMode="numeric"
          maxLength={6}
          aria-label="PIN"
          className="w-full rounded-md border border-border px-3 py-2 text-2xl tracking-widest"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
        />
      </div>
      {msg ? <p className="text-sm text-destructive">{msg}</p> : null}
      <button
        type="button"
        disabled={!idUsuario.trim() || pin.length < 4}
        onClick={ingresar}
        className="w-full rounded-md bg-primary px-4 py-3 font-medium text-primary-foreground disabled:opacity-50"
      >
        Ingresar
      </button>
    </section>
  );
}
