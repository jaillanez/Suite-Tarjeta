'use client';

import { useCallback, useEffect, useState } from 'react';
import { ApiError, type PromocionIn, type PromocionOut, type SucursalOut } from '@tarjeta/api-client';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@tarjeta/ui';
import { api } from '@/lib/api';

const MECANICAS = [
  'PORCENTAJE',
  'MONTO_FIJO',
  'DOS_POR_UNO',
  'PRECIO_ESPECIAL',
  'MULTIPLICADOR_PUNTOS',
  'CUPON_UNICO',
  'COMBO',
];
const PASOS = ['Qué ofrecés', 'A quién', 'Dónde y cuándo', 'Límites', 'Imagen y texto'];

type Borrador = {
  titulo: string;
  descripcion: string;
  mecanica: string;
  segmento: string;
  valor_platino: number | null;
  valor_black: number;
  fecha_desde: string;
  fecha_hasta: string;
  sucursales: string[];
  tope_total: number | null;
  imagen_url: string;
};

const INICIAL: Borrador = {
  titulo: '',
  descripcion: '',
  mecanica: 'PORCENTAJE',
  segmento: 'AMBOS',
  valor_platino: 10,
  valor_black: 20,
  fecha_desde: '',
  fecha_hasta: '',
  sucursales: [],
  tope_total: null,
  imagen_url: '',
};

export default function PromocionesComercioPage() {
  const [promos, setPromos] = useState<PromocionOut[]>([]);
  const [sucursales, setSucursales] = useState<SucursalOut[]>([]);
  const [paso, setPaso] = useState(0);
  const [b, setB] = useState<Borrador>(INICIAL);
  const [msg, setMsg] = useState<string | null>(null);
  const [creando, setCreando] = useState(false);

  const cargar = useCallback(async () => {
    const [ps, ss] = await Promise.all([api.listarPromociones(), api.listarSucursales()]);
    setPromos(ps);
    setSucursales(ss);
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const set = (cambios: Partial<Borrador>) => setB((prev) => ({ ...prev, ...cambios }));

  async function crear(publicar: boolean): Promise<void> {
    setMsg(null);
    const body: PromocionIn = {
      titulo: b.titulo,
      descripcion: b.descripcion,
      mecanica: b.mecanica,
      segmento: b.segmento,
      valor_platino: b.segmento === 'SOLO_BLACK' ? null : b.valor_platino,
      valor_black: b.valor_black,
      vigencia: { fecha_desde: b.fecha_desde, fecha_hasta: b.fecha_hasta, dias_semana: [] },
      sucursales: b.sucursales,
      tope_total: b.tope_total,
      imagen_url: b.imagen_url,
      acumulable: false,
      monto_minimo: 0,
    };
    try {
      const r = await api.crearPromocion(body);
      if (publicar) await api.publicarPromocion(r.mensaje);
      setB(INICIAL);
      setPaso(0);
      setCreando(false);
      await cargar();
      setMsg(publicar ? 'Promoción enviada.' : 'Borrador guardado.');
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo crear.');
    }
  }

  async function accion(id: string, fn: (id: string) => Promise<unknown>): Promise<void> {
    setMsg(null);
    try {
      await fn(id);
      await cargar();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo aplicar la acción.');
    }
  }

  const black0 = b.segmento !== 'SOLO_BLACK' && b.valor_black <= (b.valor_platino ?? 0);

  return (
    <div className="space-y-6">
      {creando ? (
        <Card>
          <CardHeader>
            <CardTitle>
              Nueva promoción · Paso {paso + 1}/5: {PASOS[paso]}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {paso === 0 ? (
              <div className="space-y-3">
                <div>
                  <Label>Mecánica</Label>
                  <Select value={b.mecanica} onValueChange={(v) => set({ mecanica: v })}>
                    <SelectTrigger className="mt-1 w-64">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {MECANICAS.map((m) => (
                        <SelectItem key={m} value={m}>
                          {m}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="t">Título</Label>
                  <Input id="t" value={b.titulo} onChange={(e) => set({ titulo: e.target.value })} className="mt-1" />
                </div>
              </div>
            ) : null}

            {paso === 1 ? (
              <div className="space-y-3">
                <div>
                  <Label>Segmento</Label>
                  <Select value={b.segmento} onValueChange={(v) => set({ segmento: v })}>
                    <SelectTrigger className="mt-1 w-64">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="AMBOS">Platino y Black</SelectItem>
                      <SelectItem value="SOLO_BLACK">Exclusiva Black</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex gap-3">
                  {b.segmento !== 'SOLO_BLACK' ? (
                    <div>
                      <Label htmlFor="vp">Valor Platino</Label>
                      <Input
                        id="vp"
                        type="number"
                        value={b.valor_platino ?? 0}
                        onChange={(e) => set({ valor_platino: Number(e.target.value) })}
                        className="mt-1 w-32"
                      />
                    </div>
                  ) : null}
                  <div>
                    <Label htmlFor="vb">Valor Black</Label>
                    <Input
                      id="vb"
                      type="number"
                      value={b.valor_black}
                      onChange={(e) => set({ valor_black: Number(e.target.value) })}
                      className="mt-1 w-32"
                    />
                  </div>
                </div>
                {black0 ? (
                  <p className="rounded-md border border-amber-500/50 bg-amber-500/10 px-3 py-2 text-sm">
                    💡 Dale más a Black: es el nivel de quienes están al día con el municipio, y
                    diferenciarlo ayuda a que más vecinos se pongan al día.
                  </p>
                ) : null}
              </div>
            ) : null}

            {paso === 2 ? (
              <div className="space-y-3">
                <div className="flex gap-3">
                  <div>
                    <Label htmlFor="fd">Desde</Label>
                    <Input id="fd" type="date" value={b.fecha_desde} onChange={(e) => set({ fecha_desde: e.target.value })} className="mt-1" />
                  </div>
                  <div>
                    <Label htmlFor="fh">Hasta</Label>
                    <Input id="fh" type="date" value={b.fecha_hasta} onChange={(e) => set({ fecha_hasta: e.target.value })} className="mt-1" />
                  </div>
                </div>
                <div>
                  <Label>Sucursales</Label>
                  <div className="mt-1 space-y-1">
                    {sucursales.map((s) => (
                      <label key={s.id} className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          aria-label={s.nombre}
                          checked={b.sucursales.includes(s.id)}
                          onChange={(e) =>
                            set({
                              sucursales: e.target.checked
                                ? [...b.sucursales, s.id]
                                : b.sucursales.filter((x) => x !== s.id),
                            })
                          }
                        />
                        {s.nombre}
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}

            {paso === 3 ? (
              <div>
                <Label htmlFor="tt">Tope total de usos (opcional)</Label>
                <Input
                  id="tt"
                  type="number"
                  value={b.tope_total ?? ''}
                  onChange={(e) => set({ tope_total: e.target.value ? Number(e.target.value) : null })}
                  className="mt-1 w-40"
                />
              </div>
            ) : null}

            {paso === 4 ? (
              <div className="space-y-3">
                <div>
                  <Label htmlFor="img">URL de imagen</Label>
                  <Input id="img" value={b.imagen_url} onChange={(e) => set({ imagen_url: e.target.value })} className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="d">Descripción</Label>
                  <Input id="d" value={b.descripcion} onChange={(e) => set({ descripcion: e.target.value })} className="mt-1" />
                </div>
                <div className="rounded-md border border-border p-3">
                  <p className="text-xs text-muted-foreground">Vista previa</p>
                  <p className="font-medium">{b.titulo || 'Título'}</p>
                  <p className="text-sm text-primary">
                    {b.mecanica === 'PORCENTAJE' ? `${b.valor_black}%` : b.mecanica} · Black
                  </p>
                </div>
              </div>
            ) : null}

            {msg ? <p className="text-sm">{msg}</p> : null}
            <div className="flex justify-between">
              <Button size="sm" variant="outline" onClick={() => (paso === 0 ? setCreando(false) : setPaso(paso - 1))}>
                {paso === 0 ? 'Cancelar' : 'Atrás'}
              </Button>
              {paso < 4 ? (
                <Button size="sm" onClick={() => setPaso(paso + 1)}>
                  Siguiente
                </Button>
              ) : (
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => crear(false)}>
                    Guardar borrador
                  </Button>
                  <Button size="sm" onClick={() => crear(true)}>
                    Enviar
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">Promociones</h1>
          <Button size="sm" onClick={() => setCreando(true)}>
            Nueva promoción
          </Button>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Mis promociones</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {msg && !creando ? <p className="text-sm">{msg}</p> : null}
          {promos.length === 0 ? (
            <p className="text-sm text-muted-foreground">Todavía no cargaste promociones.</p>
          ) : (
            promos.map((p) => (
              <div key={p.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-border/50 py-2">
                <div>
                  <p className="font-medium">
                    {p.titulo} <Badge>{p.estado}</Badge>
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Black {p.valor_black}
                    {p.valor_platino !== null ? ` · Platino ${p.valor_platino}` : ' · exclusiva Black'}
                    {p.tope_total !== null ? ` · usos ${p.usos_totales}/${p.tope_total}` : ''}
                  </p>
                </div>
                <div className="flex gap-2">
                  {p.estado === 'BORRADOR' ? (
                    <Button size="sm" onClick={() => accion(p.id, api.publicarPromocion)}>
                      Publicar
                    </Button>
                  ) : null}
                  {p.estado === 'ACTIVA' ? (
                    <Button size="sm" variant="outline" onClick={() => accion(p.id, api.pausarPromocion)}>
                      Pausar
                    </Button>
                  ) : null}
                  {p.estado === 'PAUSADA' ? (
                    <Button size="sm" variant="outline" onClick={() => accion(p.id, api.reanudarPromocion)}>
                      Reanudar
                    </Button>
                  ) : null}
                  <Button size="sm" variant="outline" onClick={() => accion(p.id, api.duplicarPromocion)}>
                    Duplicar
                  </Button>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
