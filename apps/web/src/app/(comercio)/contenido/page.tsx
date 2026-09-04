'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  ApiError,
  type CuotaContenidoOut,
  type PiezaOut,
  type PlantillaContenidoOut,
  type PromocionOut,
} from '@tarjeta/api-client';
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

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

function _sinPrefijo(dataUrl: string): string {
  const i = dataUrl.indexOf(',');
  return i >= 0 ? dataUrl.slice(i + 1) : dataUrl;
}

export default function ContenidoPage() {
  const [creditos, setCreditos] = useState<CuotaContenidoOut | null>(null);
  const [plantillas, setPlantillas] = useState<PlantillaContenidoOut[]>([]);
  const [promos, setPromos] = useState<PromocionOut[]>([]);
  const [piezas, setPiezas] = useState<PiezaOut[]>([]);
  const [idPromo, setIdPromo] = useState('');
  const [plantilla, setPlantilla] = useState('clasica');
  const [idea, setIdea] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    const [c, pl, pr, pz] = await Promise.all([
      api.creditosContenido(),
      api.plantillasContenido(),
      api.listarPromociones(),
      api.listarPiezas(),
    ]);
    setCreditos(c);
    setPlantillas(pl);
    setPromos(pr);
    setPiezas(pz);
    const primera = pr[0];
    if (!idPromo && primera) setIdPromo(primera.id);
  }, [idPromo]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function correr(fn: () => Promise<unknown>, ok: string): Promise<void> {
    setMsg(null);
    setError(null);
    try {
      await fn();
      setMsg(ok);
      await cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo completar.');
    }
  }

  async function generarIA(): Promise<void> {
    if (!idPromo || !idea.trim()) {
      setError('Elegí una promoción y escribí (o dictá) la idea.');
      return;
    }
    await correr(
      () => api.generarPieza({ id_promocion: idPromo, idea, plantilla }),
      'Pieza generada.',
    );
    setIdea('');
  }

  async function subirFoto(file: File): Promise<void> {
    if (!idPromo) {
      setError('Elegí primero la promoción.');
      return;
    }
    const dataUrl = await new Promise<string>((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve(String(r.result));
      r.onerror = () => reject(new Error('No se pudo leer la foto.'));
      r.readAsDataURL(file);
    });
    await correr(
      () => api.piezaDesdeFoto({ id_promocion: idPromo, foto_base64: _sinPrefijo(dataUrl), plantilla }),
      'Pieza creada con tu foto.',
    );
  }

  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Piezas para promocionar</h1>
        {creditos ? (
          <Badge variant={creditos.disponibles > 0 ? 'default' : 'secondary'}>
            {creditos.disponibles} de {creditos.cuota} generaciones este mes
          </Badge>
        ) : null}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Label>Promoción</Label>
          <Select value={idPromo} onValueChange={setIdPromo}>
            <SelectTrigger>
              <SelectValue placeholder="Elegí una promoción" />
            </SelectTrigger>
            <SelectContent>
              {promos.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.titulo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label>Plantilla</Label>
          <Select value={plantilla} onValueChange={setPlantilla}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {plantillas.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.nombre}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* §11.7: el camino recomendado va primero. La mejor pieza es tu propia foto. */}
      <Card>
        <CardHeader>
          <CardTitle>Usá tu propia foto (recomendado)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm text-muted-foreground">
            Una foto real de lo que ofrecés queda mejor, es verdadera y no gasta generaciones.
          </p>
          <Input
            type="file"
            accept="image/*"
            aria-label="Subir foto propia"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void subirFoto(f);
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>¿No tenés foto? Generá un fondo con IA</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <Label htmlFor="idea">Escribí o dictá la idea (usá el micrófono de tu teclado)</Label>
          <textarea
            id="idea"
            aria-label="Idea para la pieza"
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            rows={4}
            placeholder="Ej: un fondo cálido con mesa de madera y luz de mañana, sin mostrar el producto."
            className="w-full rounded-md border border-border bg-background p-2 text-sm"
          />
          <p className="text-xs text-muted-foreground">
            La IA hace solo el fondo. El descuento, la vigencia y tu nombre se agregan aparte, con el
            dato exacto de la promoción. Generar una pieza usa 1 de tus {creditos?.cuota ?? 10}{' '}
            generaciones.
          </p>
          <Button onClick={() => void generarIA()} disabled={(creditos?.disponibles ?? 0) <= 0}>
            Generar con IA
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {piezas.map((pieza) => (
          <Card key={pieza.id}>
            <CardHeader>
              <CardTitle className="flex items-center justify-between text-sm">
                <span>{pieza.origen === 'IA' ? 'Generada con IA' : 'Con tu foto'}</span>
                <Badge variant="secondary">{pieza.estado}</Badge>
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
              <p className="text-xs text-muted-foreground">
                {pieza.superposicion.porcentaje} · {pieza.superposicion.vigencia}
              </p>
              <Select
                value={pieza.plantilla}
                onValueChange={(v) =>
                  void correr(() => api.cambiarPlantillaPieza(pieza.id, v), 'Plantilla actualizada.')
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {plantillas.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>
        ))}
      </div>

      {msg ? <p className="text-sm text-green-600">{msg}</p> : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </section>
  );
}
