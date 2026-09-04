'use client';

import { useCallback, useEffect, useState } from 'react';
import { ApiError, type PromocionOut } from '@tarjeta/api-client';
import { Button, Card, CardContent, CardHeader, CardTitle, Input } from '@tarjeta/ui';
import { api } from '@/lib/api';

export default function ModeracionPage() {
  const [cola, setCola] = useState<PromocionOut[]>([]);
  const [ediciones, setEd] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      setCola(await api.colaModeracion());
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo cargar la cola.');
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function aprobar(p: PromocionOut): Promise<void> {
    setMsg(null);
    const nuevoTitulo = ediciones[p.id];
    try {
      await api.moderarAprobar(
        p.id,
        nuevoTitulo && nuevoTitulo !== p.titulo ? { motivo: '', titulo: nuevoTitulo } : { motivo: '' },
      );
      await cargar();
      setMsg('Promoción aprobada.');
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo aprobar.');
    }
  }

  async function rechazar(p: PromocionOut): Promise<void> {
    setMsg(null);
    const motivo = prompt('Motivo del rechazo:') ?? '';
    try {
      await api.moderarRechazar(p.id, motivo);
      await cargar();
      setMsg('Promoción rechazada.');
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo rechazar.');
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cola de moderación de promociones</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Revisá que la imagen y los datos coincidan (la imagen dice 50% y la promo 20%, por
          ejemplo). Podés aprobar, aprobar con una corrección de título, o rechazar con motivo.
        </p>
        {msg ? <p className="text-sm">{msg}</p> : null}
        {cola.length === 0 ? (
          <p className="text-sm text-muted-foreground">No hay promociones en revisión.</p>
        ) : (
          cola.map((p) => (
            <div key={p.id} className="grid gap-4 rounded-md border border-border p-3 sm:grid-cols-2">
              {/* Creatividad (lado a lado con los datos) */}
              <div>
                {p.imagen_url ? (
                  <img src={p.imagen_url} alt={p.titulo} className="w-full rounded" />
                ) : (
                  <div className="flex h-32 items-center justify-center rounded bg-muted text-sm text-muted-foreground">
                    (sin imagen)
                  </div>
                )}
              </div>
              {/* Datos */}
              <div className="space-y-2 text-sm">
                <p>
                  <span className="text-muted-foreground">Mecánica:</span> {p.mecanica}
                </p>
                <p>
                  <span className="text-muted-foreground">Valores:</span> Black {p.valor_black}
                  {p.valor_platino !== null ? ` · Platino ${p.valor_platino}` : ' · exclusiva Black'}
                </p>
                <p className="text-muted-foreground">{p.descripcion}</p>
                <Input
                  defaultValue={p.titulo}
                  onChange={(e) => setEd({ ...ediciones, [p.id]: e.target.value })}
                  aria-label="Título (editable al aprobar)"
                />
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => aprobar(p)}>
                    Aprobar
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => rechazar(p)}>
                    Rechazar
                  </Button>
                </div>
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
