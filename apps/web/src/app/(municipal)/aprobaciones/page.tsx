'use client';

import { useCallback, useEffect, useState } from 'react';
import { ApiError, type SolicitudAprobacion } from '@tarjeta/api-client';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
} from '@tarjeta/ui';
import { api } from '@/lib/api';

export default function AprobacionesPage() {
  const [pendientes, setPendientes] = useState<SolicitudAprobacion[]>([]);
  const [motivos, setMotivos] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      setPendientes(await api.bandejaAprobaciones());
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo cargar la bandeja.');
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function decidir(id: string, accion: 'aprobar' | 'rechazar'): Promise<void> {
    setMsg(null);
    const motivo = motivos[id] ?? '';
    try {
      if (accion === 'aprobar') await api.aprobarSolicitud(id, motivo);
      else await api.rechazarSolicitud(id, motivo);
      await cargar();
      setMsg(accion === 'aprobar' ? 'Solicitud aprobada.' : 'Solicitud rechazada.');
    } catch (e) {
      // 409 autoaprobación / 403 rango insuficiente se muestran tal cual.
      setMsg(e instanceof ApiError ? e.message : 'No se pudo decidir.');
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Aprobaciones pendientes (doble conformidad)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          No podés aprobar tu propia solicitud, y necesitás un rango igual o superior al de quien
          la pidió.
        </p>
        {msg ? <p className="text-sm">{msg}</p> : null}
        {pendientes.length === 0 ? (
          <p className="text-sm text-muted-foreground">No hay solicitudes pendientes.</p>
        ) : (
          <ul className="space-y-3">
            {pendientes.map((s) => (
              <li key={s.id} className="rounded-md border border-border p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">{s.accion}</span>
                  <span className="text-xs text-muted-foreground">
                    vence {new Date(s.fecha_expiracion).toLocaleString('es-AR')}
                  </span>
                </div>
                <p className="mt-1 font-mono text-xs text-muted-foreground">
                  solicitante: {s.solicitante}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <Input
                    placeholder="Motivo (opcional)"
                    value={motivos[s.id] ?? ''}
                    onChange={(e) => setMotivos({ ...motivos, [s.id]: e.target.value })}
                    className="max-w-64"
                  />
                  <Button size="sm" onClick={() => decidir(s.id, 'aprobar')}>
                    Aprobar
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => decidir(s.id, 'rechazar')}>
                    Rechazar
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
