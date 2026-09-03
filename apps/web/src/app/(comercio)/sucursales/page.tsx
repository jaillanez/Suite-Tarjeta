'use client';

import { useCallback, useEffect, useState } from 'react';
import { ApiError, type SucursalOut } from '@tarjeta/api-client';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Label,
} from '@tarjeta/ui';
import { MapaPicker } from '@/components/MapaPicker';
import { api } from '@/lib/api';

export default function SucursalesPage() {
  const [sucursales, setSucursales] = useState<SucursalOut[]>([]);
  const [nombre, setNombre] = useState('');
  const [direccion, setDireccion] = useState('');
  const [lat, setLat] = useState<number | null>(null);
  const [lon, setLon] = useState<number | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      setSucursales(await api.listarSucursales());
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudieron cargar las sucursales.');
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function crear(): Promise<void> {
    setMsg(null);
    if (lat === null || lon === null) {
      setMsg('Marcá la ubicación en el mapa.');
      return;
    }
    try {
      await api.crearSucursal({
        nombre,
        direccion,
        lat,
        lon,
        telefono: '',
        es_casa_central: false,
        horarios: [],
        fotos: [],
      });
      setNombre('');
      setDireccion('');
      setLat(null);
      setLon(null);
      await cargar();
      setMsg('Sucursal creada.');
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo crear la sucursal.');
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Nueva sucursal</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label htmlFor="n">Nombre</Label>
              <Input id="n" value={nombre} onChange={(e) => setNombre(e.target.value)} className="mt-1" />
            </div>
            <div>
              <Label htmlFor="d">Dirección</Label>
              <Input id="d" value={direccion} onChange={(e) => setDireccion(e.target.value)} className="mt-1" />
            </div>
          </div>
          <Label>Ubicación (obligatoria)</Label>
          <MapaPicker lat={lat} lon={lon} onChange={(la, lo) => { setLat(la); setLon(lo); }} />
          {msg ? <p className="text-sm">{msg}</p> : null}
          <Button size="sm" disabled={!nombre || lat === null} onClick={crear}>
            Crear sucursal
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Sucursales</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {sucursales.length === 0 ? (
            <p className="text-sm text-muted-foreground">Todavía no cargaste sucursales.</p>
          ) : (
            sucursales.map((s) => (
              <div key={s.id} className="flex items-center justify-between border-b border-border/50 py-2">
                <div>
                  <p className="font-medium">
                    {s.nombre} {s.es_casa_central ? <Badge>Casa central</Badge> : null}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {s.direccion} · {s.lat}, {s.lon}
                  </p>
                </div>
                <Badge>{s.estado}</Badge>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
