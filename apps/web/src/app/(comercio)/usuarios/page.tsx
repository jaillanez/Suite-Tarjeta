'use client';

import { useCallback, useEffect, useState } from 'react';
import { ApiError, type UsuarioComercioOut } from '@tarjeta/api-client';
import {
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

const ROLES = ['ADMIN_SUCURSALES', 'ENCARGADO', 'CAJERO'];

export default function UsuariosComercioPage() {
  const [usuarios, setUsuarios] = useState<UsuarioComercioOut[]>([]);
  const [rol, setRol] = useState('ENCARGADO');
  const [destino, setDestino] = useState('');
  const [linkInvitacion, setLink] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      setUsuarios(await api.listarUsuarios());
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudieron cargar los usuarios.');
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function invitar(): Promise<void> {
    setMsg(null);
    setLink(null);
    try {
      const r = await api.invitarUsuario(rol, destino);
      setDestino('');
      const base = typeof window !== 'undefined' ? window.location.origin : '';
      setLink(`${base}/invitacion/${r.token}`);
      await cargar();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo invitar.');
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Invitar usuario</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-end gap-3">
            <div className="grow">
              <Label htmlFor="dest">Celular o email</Label>
              <Input id="dest" value={destino} onChange={(e) => setDestino(e.target.value)} className="mt-1" />
            </div>
            <div>
              <Label>Rol</Label>
              <Select value={rol} onValueChange={setRol}>
                <SelectTrigger className="mt-1 w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((r) => (
                    <SelectItem key={r} value={r}>
                      {r}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button size="sm" disabled={!destino} onClick={invitar}>
              Invitar
            </Button>
          </div>
          {linkInvitacion ? (
            <p className="break-all text-sm">
              Link de invitación (vence en 72 h):{' '}
              <code className="rounded bg-muted px-1">{linkInvitacion}</code>
            </p>
          ) : null}
          {msg ? <p className="text-sm">{msg}</p> : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Usuarios del comercio</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {usuarios.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sin usuarios.</p>
          ) : (
            usuarios.map((u) => (
              <div key={u.id} className="flex items-center justify-between border-b border-border/50 py-2 text-sm">
                <span className="font-mono text-xs">{u.id_persona}</span>
                <span>{u.rol}</span>
                <span className="text-muted-foreground">{u.estado}</span>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
