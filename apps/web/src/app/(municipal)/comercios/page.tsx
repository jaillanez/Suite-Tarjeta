'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  ApiError,
  type CargaMasivaResultado,
  type ComercioBandejaOut,
  type FichaComercioOut,
} from '@tarjeta/api-client';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
} from '@tarjeta/ui';
import { api } from '@/lib/api';

export default function ComerciosMunicipalPage() {
  const [bandeja, setBandeja] = useState<ComercioBandejaOut[]>([]);
  const [ficha, setFicha] = useState<FichaComercioOut | null>(null);
  const [csv, setCsv] = useState('');
  const [reporte, setReporte] = useState<CargaMasivaResultado | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      setBandeja(await api.bandejaComercios());
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo cargar la bandeja.');
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function abrir(id: string): Promise<void> {
    setMsg(null);
    try {
      setFicha(await api.fichaComercio(id));
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo abrir la ficha.');
    }
  }

  async function accion(
    id: string,
    a: 'tomar' | 'aprobar' | 'rechazar' | 'pedir-documentacion' | 'suspender',
  ): Promise<void> {
    setMsg(null);
    try {
      const motivo = a === 'rechazar' || a === 'pedir-documentacion' ? prompt('Motivo:') ?? '' : '';
      await api.comercioAccion(id, a, motivo);
      await cargar();
      await abrir(id);
      setMsg('Acción aplicada.');
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo aplicar la acción.');
    }
  }

  async function subirCsv(): Promise<void> {
    setMsg(null);
    try {
      setReporte(await api.cargaMasivaComercios(csv, true));
      await cargar();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo procesar el CSV.');
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Solicitudes de comercios</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {msg ? <p className="text-sm">{msg}</p> : null}
          {bandeja.length === 0 ? (
            <p className="text-sm text-muted-foreground">No hay solicitudes pendientes.</p>
          ) : (
            bandeja.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => abrir(c.id)}
                className="flex w-full items-center justify-between rounded-md border border-border px-3 py-2 text-left text-sm hover:bg-muted"
              >
                <span>
                  {c.razon_social}
                  <span className="ml-2 text-xs text-muted-foreground">{c.cuit}</span>
                </span>
                <Badge>{c.estado}</Badge>
              </button>
            ))
          )}
        </CardContent>
      </Card>

      <div className="space-y-6">
        {ficha ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {ficha.razon_social} <Badge>{ficha.estado}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p className="text-muted-foreground">
                CUIT {ficha.cuit} · {ficha.sucursales.length} sucursal(es) ·{' '}
                {ficha.usuarios.length} usuario(s)
              </p>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" onClick={() => accion(ficha.id, 'tomar')}>
                  Tomar
                </Button>
                <Button size="sm" onClick={() => accion(ficha.id, 'aprobar')}>
                  Aprobar
                </Button>
                <Button size="sm" variant="outline" onClick={() => accion(ficha.id, 'pedir-documentacion')}>
                  Pedir documentación
                </Button>
                <Button size="sm" variant="outline" onClick={() => accion(ficha.id, 'suspender')}>
                  Suspender
                </Button>
                <Button size="sm" variant="outline" onClick={() => accion(ficha.id, 'rechazar')}>
                  Rechazar
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                La baja definitiva requiere doble conformidad (Aprobaciones).
              </p>
            </CardContent>
          </Card>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle>Carga masiva (CSV)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-xs text-muted-foreground">
              Encabezado: <code>cuit,razon_social,rubro</code>. Se valida cada fila antes de crear.
            </p>
            <Input
              placeholder="cuit,razon_social,rubro"
              value={csv}
              onChange={(e) => setCsv(e.target.value)}
            />
            <Button size="sm" disabled={!csv.trim()} onClick={subirCsv}>
              Procesar y crear
            </Button>
            {reporte ? (
              <div className="text-sm">
                <p>
                  Válidas: {reporte.validas} · Creadas: {reporte.creados}
                </p>
                <ul className="mt-1 space-y-0.5">
                  {reporte.filas.map((f) => (
                    <li key={f.fila} className={f.ok ? 'text-green-600' : 'text-destructive'}>
                      Fila {f.fila}: {f.ok ? 'OK' : f.error}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
