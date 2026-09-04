'use client';

import { useCallback, useEffect, useState } from 'react';
import { ApiError, type ItemCatalogoOut } from '@tarjeta/api-client';
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from '@tarjeta/ui';
import { api } from '@/lib/api';

const VACIO = { titulo: '', descripcion: '', costo_pm: '', stock: '', fecha_desde: '', fecha_hasta: '' };

export default function PuntosMunicipalPage() {
  const [items, setItems] = useState<ItemCatalogoOut[]>([]);
  const [circulante, setCirculante] = useState<number | null>(null);
  const [form, setForm] = useState({ ...VACIO });
  const [msg, setMsg] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    const [cat, pm] = await Promise.all([api.catalogoMunicipal(), api.pmCirculante()]);
    setItems(cat);
    setCirculante(pm.total);
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function publicar(): Promise<void> {
    setMsg(null);
    try {
      await api.publicarItemCatalogo({
        titulo: form.titulo,
        descripcion: form.descripcion,
        costo_pm: Number(form.costo_pm),
        stock: Number(form.stock),
        fecha_desde: form.fecha_desde,
        fecha_hasta: form.fecha_hasta,
      });
      setForm({ ...VACIO });
      await cargar();
      setMsg('Ítem publicado.');
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo publicar.');
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm text-muted-foreground">
            PM en circulación (pasivo del municipio)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-3xl font-semibold">{circulante ?? '—'}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Nuevo ítem de catálogo</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Label htmlFor="titulo">Título</Label>
            <Input
              id="titulo"
              value={form.titulo}
              onChange={(e) => setForm({ ...form, titulo: e.target.value })}
            />
          </div>
          <div className="sm:col-span-2">
            <Label htmlFor="descripcion">Descripción</Label>
            <Input
              id="descripcion"
              value={form.descripcion}
              onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="costo">Costo (PM)</Label>
            <Input
              id="costo"
              type="number"
              value={form.costo_pm}
              onChange={(e) => setForm({ ...form, costo_pm: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="stock">Stock</Label>
            <Input
              id="stock"
              type="number"
              value={form.stock}
              onChange={(e) => setForm({ ...form, stock: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="desde">Vigencia desde</Label>
            <Input
              id="desde"
              type="date"
              value={form.fecha_desde}
              onChange={(e) => setForm({ ...form, fecha_desde: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="hasta">Vigencia hasta</Label>
            <Input
              id="hasta"
              type="date"
              value={form.fecha_hasta}
              onChange={(e) => setForm({ ...form, fecha_hasta: e.target.value })}
            />
          </div>
          <div className="sm:col-span-2">
            <Button onClick={publicar}>Publicar</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Catálogo</CardTitle>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sin ítems cargados.</p>
          ) : (
            <ul className="divide-y divide-border">
              {items.map((i) => (
                <li key={i.id} className="flex items-center justify-between py-2 text-sm">
                  <span>
                    {i.titulo}{' '}
                    <span className="text-muted-foreground">
                      ({i.estado}, vence {i.fecha_hasta})
                    </span>
                  </span>
                  <span className="font-medium">
                    {i.costo_pm} PM · stock {i.stock}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {msg ? <p className="text-sm text-muted-foreground">{msg}</p> : null}
    </div>
  );
}
