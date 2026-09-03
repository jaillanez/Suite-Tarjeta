'use client';

import { useState } from 'react';
import { ApiError, type AltaPresencialResult, type Ficha360 } from '@tarjeta/api-client';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@tarjeta/ui';
import { api } from '@/lib/api';
import { useDraft } from '@/lib/municipal';

function FichaTab() {
  const [id, setId] = useState('');
  const [ficha, setFicha] = useState<Ficha360 | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function abrir(): Promise<void> {
    setMsg(null);
    setFicha(null);
    try {
      // §11.3: reautenticación explícita del agente para abrir la ficha.
      const ok = window.confirm('Confirmá tu identidad para abrir la ficha del ciudadano.');
      if (!ok) return;
      setFicha(await api.ficha360(id.trim(), 'ok'));
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo abrir la ficha.');
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="grow">
          <Label htmlFor="idp">ID de persona</Label>
          <Input
            id="idp"
            value={id}
            onChange={(e) => setId(e.target.value)}
            placeholder="uuid del ciudadano"
            className="mt-1 max-w-96"
          />
        </div>
        <Button size="sm" disabled={!id.trim()} onClick={abrir}>
          Abrir ficha
        </Button>
      </div>
      {msg ? <p className="text-sm text-destructive">{msg}</p> : null}
      {ficha ? (
        <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
          <Dato k="Nombre" v={`${ficha.nombre} ${ficha.apellido}`.trim() || '—'} />
          <Dato k="DNI" v={ficha.dni} />
          <Dato k="Identidad" v={ficha.estado_identidad} />
          <Dato k="Nivel" v={ficha.nivel ?? '—'} />
          <Dato k="Tarjeta" v={ficha.tarjeta ?? '—'} />
          <Dato k="Estado tarjeta" v={ficha.estado_tarjeta ?? '—'} />
          <Dato k="Padrón al día" v={ficha.padron_al_dia === null ? '—' : ficha.padron_al_dia ? 'Sí' : 'No'} />
          <Dato k="Dispositivos" v={String(ficha.dispositivos.length)} />
        </dl>
      ) : null}
    </div>
  );
}

function Dato({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border/50 py-1">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="text-right font-medium">{v}</dd>
    </div>
  );
}

function AltaTab() {
  const [form, setForm, limpiar] = useDraft('alta-presencial', { dni: '', fecha_nacimiento: '' });
  const [res, setRes] = useState<AltaPresencialResult | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function alta(): Promise<void> {
    setMsg(null);
    setRes(null);
    try {
      const r = await api.altaPresencial(form.dni.trim(), form.fecha_nacimiento);
      setRes(r);
      limpiar();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo dar el alta.');
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Label htmlFor="dni">DNI</Label>
          <Input
            id="dni"
            value={form.dni}
            onChange={(e) => setForm({ ...form, dni: e.target.value })}
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor="fn">Fecha de nacimiento</Label>
          <Input
            id="fn"
            type="date"
            value={form.fecha_nacimiento}
            onChange={(e) => setForm({ ...form, fecha_nacimiento: e.target.value })}
            className="mt-1"
          />
        </div>
      </div>
      <Button size="sm" disabled={!form.dni.trim() || !form.fecha_nacimiento} onClick={alta}>
        Dar de alta
      </Button>
      {msg ? <p className="text-sm text-destructive">{msg}</p> : null}
      {res ? (
        <div className="rounded-md border border-border bg-muted/40 p-3 text-sm">
          <p>Ciudadano dado de alta.</p>
          <p className="mt-1">
            Contraseña temporal:{' '}
            <code className="rounded bg-background px-1 py-0.5">{res.password_temporal}</code>
          </p>
          <p className="mt-1 text-muted-foreground">
            Entregala al ciudadano; deberá cambiarla al primer ingreso.
          </p>
        </div>
      ) : null}
    </div>
  );
}

function ReclamoTab() {
  const [form, setForm, limpiar] = useDraft('reclamo', { dni: '', motivo: '' });
  const [msg, setMsg] = useState<string | null>(null);

  async function reclamar(): Promise<void> {
    setMsg(null);
    try {
      await api.crearReclamo(form.dni.trim(), form.motivo.trim());
      limpiar();
      setMsg('Reclamo registrado. Requiere aprobación de otro agente (doble conformidad).');
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo registrar el reclamo.');
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        El reclamo de cuenta revoca la sesión anterior y resetea las credenciales; por eso lo debe
        aprobar un segundo agente.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Label htmlFor="rdni">DNI</Label>
          <Input
            id="rdni"
            value={form.dni}
            onChange={(e) => setForm({ ...form, dni: e.target.value })}
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor="rmotivo">Motivo</Label>
          <Input
            id="rmotivo"
            value={form.motivo}
            onChange={(e) => setForm({ ...form, motivo: e.target.value })}
            className="mt-1"
          />
        </div>
      </div>
      <Button size="sm" disabled={!form.dni.trim() || !form.motivo.trim()} onClick={reclamar}>
        Registrar reclamo
      </Button>
      {msg ? <p className="text-sm">{msg}</p> : null}
    </div>
  );
}

export default function CiudadanosPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Ciudadanos</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="ficha">
          <TabsList>
            <TabsTrigger value="ficha">Ficha 360</TabsTrigger>
            <TabsTrigger value="alta">Alta presencial</TabsTrigger>
            <TabsTrigger value="reclamo">Reclamo de cuenta</TabsTrigger>
          </TabsList>
          <TabsContent value="ficha" className="mt-4">
            <FichaTab />
          </TabsContent>
          <TabsContent value="alta" className="mt-4">
            <AltaTab />
          </TabsContent>
          <TabsContent value="reclamo" className="mt-4">
            <ReclamoTab />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
