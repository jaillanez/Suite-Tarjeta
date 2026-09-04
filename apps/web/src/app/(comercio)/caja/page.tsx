'use client';

import { useState } from 'react';
import { ApiError, type OpcionOut, type ResolverOut, type TransaccionOut } from '@tarjeta/api-client';
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

const VIAS = [
  { v: 'CAJERO_ESCANEA', label: 'Escanear QR del cliente' },
  { v: 'CODIGO', label: 'Código de 6 dígitos' },
  { v: 'TARJETA_FISICA', label: 'Tarjeta física + DNI' },
];

function _uuid(): string {
  return crypto.randomUUID();
}

export default function CajaPage() {
  const [via, setVia] = useState('CAJERO_ESCANEA');
  const [token, setToken] = useState('');
  const [codigo, setCodigo] = useState('');
  const [dni, setDni] = useState('');
  const [idSucursal, setSucursal] = useState('');
  const [monto, setMonto] = useState('');
  const [datos, setDatos] = useState<ResolverOut | null>(null);
  const [op, setOp] = useState<TransaccionOut | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  function credencial(): Record<string, string> {
    if (via === 'CAJERO_ESCANEA') return { token };
    if (via === 'CODIGO') return { codigo };
    return { dni };
  }

  async function resolver(): Promise<void> {
    setMsg(null);
    setDatos(null);
    try {
      const r = await api.resolverCanje({
        via,
        monto: Number(monto),
        id_sucursal: idSucursal,
        ...credencial(),
      });
      setDatos(r);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo identificar al cliente.');
    }
  }

  async function iniciar(opcion: OpcionOut | null): Promise<void> {
    setMsg(null);
    try {
      const t = await api.iniciarCanje({
        via,
        monto: Number(monto),
        id_sucursal: idSucursal,
        clave_idempotencia: _uuid(),
        id_promocion: opcion?.id_promocion ?? null,
        ...credencial(),
      });
      setOp(t);
      setDatos(null);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo iniciar la operación.');
    }
  }

  async function actualizar(): Promise<void> {
    if (!op) return;
    const t = await api.estadoOperacionCanje(op.id);
    setOp(t);
  }

  async function confirmarComercio(): Promise<void> {
    if (!op) return;
    setOp(await api.confirmarComercioCanje(op.id));
  }

  function nuevo(): void {
    setOp(null);
    setDatos(null);
    setMonto('');
    setToken('');
    setCodigo('');
    setDni('');
    setMsg(null);
  }

  if (op) {
    const esperaCliente = op.confirmador === 'CIUDADANO' && op.estado === 'PENDIENTE_CONFIRMACION';
    const esperaComercio = op.confirmador === 'CAJERO' && op.estado === 'PENDIENTE_CONFIRMACION';
    return (
      <Card className="mx-auto max-w-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {op.numero_comprobante} <Badge>{op.estado}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-3xl font-semibold">Total: ${op.total_pagar}</p>
          <p className="text-sm text-muted-foreground">
            Monto ${op.monto_bruto} · Descuento ${op.descuento} · Nivel {op.nivel_aplicado}
          </p>
          {esperaCliente ? (
            <>
              <p className="rounded-md bg-muted p-3 text-sm">
                Pedile al cliente que confirme en su teléfono.
              </p>
              <Button size="sm" variant="outline" onClick={actualizar}>
                Actualizar estado
              </Button>
            </>
          ) : null}
          {esperaComercio ? (
            <Button size="sm" onClick={confirmarComercio}>
              Confirmar operación
            </Button>
          ) : null}
          {op.estado === 'APLICADA' ? (
            <p className="rounded-md border border-green-500/50 bg-green-500/10 p-3 text-sm">
              ✅ Descuento aplicado.
            </p>
          ) : null}
          <Button onClick={nuevo}>Nueva operación</Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mx-auto max-w-md">
      <CardHeader>
        <CardTitle>Caja</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label>Vía</Label>
          <Select value={via} onValueChange={setVia}>
            <SelectTrigger className="mt-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {VIAS.map((x) => (
                <SelectItem key={x.v} value={x.v}>
                  {x.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {via === 'CAJERO_ESCANEA' ? (
          <div>
            <Label htmlFor="tk">QR del cliente</Label>
            <Input id="tk" value={token} onChange={(e) => setToken(e.target.value)} className="mt-1" />
          </div>
        ) : null}
        {via === 'CODIGO' ? (
          <div>
            <Label htmlFor="cd">Código de 6 dígitos</Label>
            <Input id="cd" inputMode="numeric" value={codigo} onChange={(e) => setCodigo(e.target.value)} className="mt-1" />
          </div>
        ) : null}
        {via === 'TARJETA_FISICA' ? (
          <div>
            <Label htmlFor="dn">DNI del cliente</Label>
            <Input id="dn" value={dni} onChange={(e) => setDni(e.target.value)} className="mt-1" />
          </div>
        ) : null}
        <div>
          <Label htmlFor="su">Sucursal (ID)</Label>
          <Input id="su" value={idSucursal} onChange={(e) => setSucursal(e.target.value)} className="mt-1" />
        </div>
        <div>
          <Label htmlFor="mo">Monto</Label>
          <Input
            id="mo"
            type="number"
            inputMode="numeric"
            value={monto}
            onChange={(e) => setMonto(e.target.value)}
            className="mt-1 text-2xl"
          />
        </div>
        {msg ? <p className="text-sm text-destructive">{msg}</p> : null}
        <Button className="w-full" disabled={!monto || !idSucursal} onClick={resolver}>
          Buscar promociones
        </Button>

        {datos ? (
          <div className="space-y-2">
            <p className="text-sm">
              {datos.nombre} {datos.inicial_apellido}. · <Badge>{datos.nivel}</Badge>
            </p>
            <p className="text-xs text-muted-foreground">Ordenadas por descuento real en pesos:</p>
            {datos.opciones.map((o) => (
              <button
                key={o.id_promocion}
                type="button"
                onClick={() => iniciar(o)}
                className="flex w-full items-center justify-between rounded-md border border-border px-3 py-2 text-left hover:bg-muted"
              >
                <span>
                  {o.titulo}
                  {!o.auto_propuesta ? (
                    <span className="ml-1 text-xs text-amber-600">(elegir a mano)</span>
                  ) : null}
                </span>
                <span className="font-semibold text-primary">
                  −${o.descuento} → ${o.total}
                </span>
              </button>
            ))}
            <Button size="sm" variant="outline" onClick={() => iniciar(null)}>
              Sin promoción
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
