'use client';

import { useCallback, useEffect, useState } from 'react';
import { ApiError, type PiezaOut } from '@tarjeta/api-client';
import { Badge, Button, Card, CardContent, CardHeader, CardTitle } from '@tarjeta/ui';
import { api } from '@/lib/api';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export default function PiezasModeracionPage() {
  const [cola, setCola] = useState<PiezaOut[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      setCola(await api.colaModeracionPiezas());
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo cargar la cola.');
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function decidir(fn: () => Promise<unknown>, ok: string): Promise<void> {
    setMsg(null);
    try {
      await fn();
      setMsg(ok);
      await cargar();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo decidir.');
    }
  }

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Moderación de piezas</h1>
      <p className="text-sm text-muted-foreground">
        Las piezas de comercios verificados se publican solas; acá llegan las que requieren revisión.
      </p>

      {cola.length === 0 ? (
        <p className="text-muted-foreground">No hay piezas esperando moderación.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {cola.map((pieza) => (
            <Card key={pieza.id}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between text-sm">
                  <span>{pieza.origen === 'IA' ? 'IA' : 'Foto propia'}</span>
                  <Badge variant="secondary">{pieza.superposicion.porcentaje}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {pieza.formatos.CUADRADO ? (
                  <img
                    src={`${API}${pieza.formatos.CUADRADO}`}
                    alt={`Pieza de ${pieza.superposicion.nombre}`}
                    className="w-full rounded-md border border-border"
                  />
                ) : null}
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => void decidir(() => api.aprobarPieza(pieza.id), 'Aprobada.')}
                  >
                    Aprobar
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      void decidir(
                        () => api.rechazarPieza(pieza.id, 'No cumple los guardarraíles'),
                        'Rechazada.',
                      )
                    }
                  >
                    Rechazar
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      {msg ? <p className="text-sm text-muted-foreground">{msg}</p> : null}
    </section>
  );
}
