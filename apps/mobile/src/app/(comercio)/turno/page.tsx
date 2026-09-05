'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Store } from 'lucide-react';
import { ApiError, type SucursalOut } from '@tarjeta/api-client';
import { Button } from '@tarjeta/ui';
import { CerrarSesion } from '@/components/CerrarSesion';
import { api } from '@/lib/api';

export default function TurnoPage() {
  const router = useRouter();
  const [sucursales, setSucursales] = useState<SucursalOut[] | null>(null); // null = cargando
  const [activa, setActiva] = useState<SucursalOut | null>(null);
  const [turnoAbierto, setTurnoAbierto] = useState(false);
  const [resumen, setResumen] = useState<Record<string, unknown> | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      setSucursales(await api.listarSucursales());
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        router.push('/caja');
        return;
      }
      setSucursales([]);
      setMsg(e instanceof ApiError ? e.message : 'No se pudieron cargar las sucursales.');
    }
  }, [router]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function abrir(sucursal: SucursalOut): Promise<void> {
    setMsg(null);
    try {
      await api.abrirTurno(sucursal.id);
      setActiva(sucursal);
      setTurnoAbierto(true);
      setResumen(null);
    } catch (e) {
      // Ya había un turno abierto para este cajero: pasamos igual al estado "abierto".
      if (e instanceof ApiError && e.status === 409) {
        setActiva(sucursal);
        setTurnoAbierto(true);
        setMsg('Ya tenías un turno abierto.');
        return;
      }
      setMsg(e instanceof ApiError ? e.message : 'No se pudo abrir el turno.');
    }
  }

  async function cerrar(): Promise<void> {
    setMsg(null);
    try {
      const real = await api.resumenTurnoCanje();
      await api.cerrarTurno();
      setResumen({ ...real });
      setTurnoAbierto(false);
      setActiva(null);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo cerrar el turno.');
    }
  }

  if (sucursales === null) {
    return <p className="p-6 text-muted-foreground">Cargando…</p>;
  }

  return (
    <main className="mx-auto max-w-sm space-y-5 p-6">
      <h1 className="text-xl font-semibold">Turno</h1>

      {turnoAbierto ? (
        <div className="space-y-3">
          <div className="rounded-xl border border-primary bg-brand-50 p-4">
            <p className="font-semibold text-brand-900">Turno abierto</p>
            {activa ? (
              <p className="text-sm text-brand-700">{activa.nombre}</p>
            ) : null}
          </div>
          <p className="text-sm text-muted-foreground">
            La caja (escaneo del QR del ciudadano) llega en el paso siguiente.
          </p>
          <Button variant="outline" className="w-full" onClick={cerrar}>
            Cerrar turno
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">Elegí la sucursal para abrir el turno.</p>
          {sucursales.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Este comercio todavía no tiene sucursales cargadas.
            </p>
          ) : (
            <ul className="space-y-3">
              {sucursales.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    onClick={() => void abrir(s)}
                    className="flex w-full items-center gap-4 rounded-xl border border-border bg-card p-4 text-left transition-colors active:bg-accent"
                  >
                    <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-700">
                      <Store className="size-5" aria-hidden="true" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block font-semibold">{s.nombre}</span>
                      {s.direccion ? (
                        <span className="block truncate text-sm text-muted-foreground">
                          {s.direccion}
                        </span>
                      ) : null}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {resumen ? (
        <div className="rounded-md border border-border p-3 text-sm">
          <p className="font-medium">Resumen del turno</p>
          <pre className="mt-1 overflow-x-auto text-xs">{JSON.stringify(resumen, null, 2)}</pre>
        </div>
      ) : null}
      {msg ? <p className="text-sm text-muted-foreground">{msg}</p> : null}

      <div className="border-t border-border pt-4">
        <CerrarSesion />
      </div>
    </main>
  );
}
