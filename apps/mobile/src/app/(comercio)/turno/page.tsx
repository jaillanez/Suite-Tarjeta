'use client';

import { useState } from 'react';
import { ApiError } from '@tarjeta/api-client';
import { api } from '@/lib/api';

export default function TurnoPage() {
  const [idSucursal, setIdSucursal] = useState('');
  const [turnoAbierto, setTurnoAbierto] = useState<string | null>(null);
  const [resumen, setResumen] = useState<Record<string, unknown> | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function abrir(): Promise<void> {
    setMsg(null);
    try {
      const r = await api.abrirTurno(idSucursal.trim());
      setTurnoAbierto(r.id);
      setResumen(null);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo abrir el turno.');
    }
  }

  async function cerrar(): Promise<void> {
    setMsg(null);
    try {
      const r = await api.cerrarTurno();
      setResumen(r.resumen);
      setTurnoAbierto(null);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo cerrar el turno.');
    }
  }

  return (
    <section className="mx-auto max-w-sm space-y-4 p-4">
      <h1 className="text-xl font-semibold">Turno</h1>
      {turnoAbierto ? (
        <>
          <p className="text-sm text-green-600">Turno abierto.</p>
          <p className="text-sm text-muted-foreground">
            La caja llega en el paso siguiente; por ahora el resumen queda vacío.
          </p>
          <button
            type="button"
            onClick={cerrar}
            className="w-full rounded-md border border-border px-4 py-3 font-medium"
          >
            Cerrar turno
          </button>
        </>
      ) : (
        <>
          <label className="block text-sm" htmlFor="suc">
            Sucursal (ID)
          </label>
          <input
            id="suc"
            aria-label="Sucursal (ID)"
            className="w-full rounded-md border border-border px-3 py-2"
            value={idSucursal}
            onChange={(e) => setIdSucursal(e.target.value)}
          />
          <button
            type="button"
            disabled={!idSucursal.trim()}
            onClick={abrir}
            className="w-full rounded-md bg-primary px-4 py-3 font-medium text-primary-foreground disabled:opacity-50"
          >
            Abrir turno
          </button>
        </>
      )}
      {resumen ? (
        <div className="rounded-md border border-border p-3 text-sm">
          <p className="font-medium">Resumen del turno</p>
          <pre className="mt-1 text-xs">{JSON.stringify(resumen, null, 2)}</pre>
        </div>
      ) : null}
      {msg ? <p className="text-sm text-destructive">{msg}</p> : null}
    </section>
  );
}
