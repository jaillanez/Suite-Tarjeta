'use client';

import { useState } from 'react';
import { ApiError } from '@tarjeta/api-client';
import {
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

const CONVENIO_VERSION = process.env.NEXT_PUBLIC_CONVENIO_VERSION ?? 'v1';

export default function AdherirComercioPage() {
  const [cuit, setCuit] = useState('');
  const [razon, setRazon] = useState('');
  const [fantasia, setFantasia] = useState('');
  const [rubro, setRubro] = useState('');
  const [sucNombre, setSucNombre] = useState('');
  const [direccion, setDireccion] = useState('');
  const [lat, setLat] = useState<number | null>(null);
  const [lon, setLon] = useState<number | null>(null);
  const [aceptaConvenio, setAcepta] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [id, setId] = useState<string | null>(null);

  const listo = cuit && razon && sucNombre && lat !== null && lon !== null && aceptaConvenio;

  async function enviar(): Promise<void> {
    setMsg(null);
    try {
      const r = await api.adhesion({
        cuit,
        razon_social: razon,
        nombre_fantasia: fantasia,
        rubro,
        logo_url: '',
        convenio_version: CONVENIO_VERSION,
        sucursal: { nombre: sucNombre, direccion, lat: lat!, lon: lon!, telefono: '' },
      });
      setId(r.id_comercio);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo enviar la solicitud.');
    }
  }

  if (id) {
    return (
      <Card className="mx-auto max-w-lg">
        <CardHeader>
          <CardTitle>Solicitud enviada</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>Tu solicitud de adhesión quedó registrada y está en revisión del municipio.</p>
          <p className="text-muted-foreground">Vas a ver el estado en el portal del comercio.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mx-auto max-w-lg">
      <CardHeader>
        <CardTitle>Adherir mi comercio</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Verificamos tu CUIT contra el padrón municipal. Necesitás al menos una sucursal con su
          ubicación en el mapa.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <Label htmlFor="cuit">CUIT</Label>
            <Input id="cuit" value={cuit} onChange={(e) => setCuit(e.target.value)} className="mt-1" />
          </div>
          <div>
            <Label htmlFor="rubro">Rubro</Label>
            <Input id="rubro" value={rubro} onChange={(e) => setRubro(e.target.value)} className="mt-1" />
          </div>
          <div>
            <Label htmlFor="razon">Razón social</Label>
            <Input id="razon" value={razon} onChange={(e) => setRazon(e.target.value)} className="mt-1" />
          </div>
          <div>
            <Label htmlFor="fantasia">Nombre de fantasía</Label>
            <Input
              id="fantasia"
              value={fantasia}
              onChange={(e) => setFantasia(e.target.value)}
              className="mt-1"
            />
          </div>
        </div>

        <div className="space-y-2 rounded-md border border-border p-3">
          <p className="font-medium">Sucursal principal</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label htmlFor="sn">Nombre</Label>
              <Input id="sn" value={sucNombre} onChange={(e) => setSucNombre(e.target.value)} className="mt-1" />
            </div>
            <div>
              <Label htmlFor="dir">Dirección</Label>
              <Input id="dir" value={direccion} onChange={(e) => setDireccion(e.target.value)} className="mt-1" />
            </div>
          </div>
          <Label>Ubicación (tocá el mapa o arrastrá el pin)</Label>
          <MapaPicker lat={lat} lon={lon} onChange={(la, lo) => { setLat(la); setLon(lo); }} />
          {lat !== null ? (
            <p className="text-xs text-muted-foreground">
              Pin en {lat}, {lon}
            </p>
          ) : (
            <p className="text-xs text-amber-600">Falta marcar la ubicación.</p>
          )}
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            aria-label="Acepto el convenio de adhesión"
            checked={aceptaConvenio}
            onChange={(e) => setAcepta(e.target.checked)}
          />
          Acepto el convenio de adhesión ({CONVENIO_VERSION}).
        </label>

        {msg ? <p className="text-sm text-destructive">{msg}</p> : null}
        <Button disabled={!listo} onClick={enviar}>
          Enviar solicitud
        </Button>
      </CardContent>
    </Card>
  );
}
