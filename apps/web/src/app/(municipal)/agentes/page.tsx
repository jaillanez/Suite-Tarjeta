'use client';

import { useCallback, useEffect, useState } from 'react';
import { ApiError, type AgenteMunicipal } from '@tarjeta/api-client';
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@tarjeta/ui';
import { api } from '@/lib/api';

const ROLES = ['SUPER_ADMIN', 'ADMINISTRADOR', 'ENCARGADO', 'PERSONAL', 'AUDITOR'];

export default function AgentesPage() {
  const [agentes, setAgentes] = useState<AgenteMunicipal[]>([]);
  const [idPersona, setIdPersona] = useState('');
  const [rol, setRol] = useState('PERSONAL');
  const [msg, setMsg] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      setAgentes(await api.agentes());
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo cargar la lista.');
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function asignar(): Promise<void> {
    setMsg(null);
    try {
      await api.asignarAgente(idPersona.trim(), rol);
      setIdPersona('');
      await cargar();
      setMsg('Agente asignado.');
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo asignar.');
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Asignar agente municipal</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-end gap-3">
            <div className="grow">
              <Label htmlFor="idp">ID de persona</Label>
              <Input
                id="idp"
                value={idPersona}
                onChange={(e) => setIdPersona(e.target.value)}
                placeholder="uuid de la persona"
                className="mt-1 max-w-96"
              />
            </div>
            <div>
              <Label>Rol</Label>
              <Select value={rol} onValueChange={setRol}>
                <SelectTrigger className="mt-1 w-52">
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
            <Button size="sm" disabled={!idPersona.trim()} onClick={asignar}>
              Asignar
            </Button>
          </div>
          {msg ? <p className="text-sm">{msg}</p> : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Agentes actuales</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID de persona</TableHead>
                  <TableHead>Rol</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agentes.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={2} className="text-muted-foreground">
                      Sin agentes.
                    </TableCell>
                  </TableRow>
                ) : (
                  agentes.map((a) => (
                    <TableRow key={a.id_persona}>
                      <TableCell className="font-mono text-xs">{a.id_persona}</TableCell>
                      <TableCell>{a.rol}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
