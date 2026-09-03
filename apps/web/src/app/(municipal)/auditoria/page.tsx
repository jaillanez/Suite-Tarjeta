'use client';

import { useCallback, useEffect, useState } from 'react';
import { ApiError, type RegistroAuditoria } from '@tarjeta/api-client';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@tarjeta/ui';
import { api } from '@/lib/api';

export default function AuditoriaPage() {
  const [registros, setRegistros] = useState<RegistroAuditoria[]>([]);
  const [accion, setAccion] = useState('');
  const [entidad, setEntidad] = useState('');
  const [err, setErr] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setErr(null);
    try {
      setRegistros(
        await api.auditoria({
          accion: accion || undefined,
          entidad: entidad || undefined,
          limite: 100,
        }),
      );
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : 'No se pudo cargar la auditoría.');
    }
  }, [accion, entidad]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Auditoría (registro inmutable)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-end gap-2">
          <Input
            placeholder="Filtrar por acción"
            value={accion}
            onChange={(e) => setAccion(e.target.value)}
            className="max-w-52"
          />
          <Input
            placeholder="Filtrar por entidad"
            value={entidad}
            onChange={(e) => setEntidad(e.target.value)}
            className="max-w-52"
          />
          <Button size="sm" variant="outline" onClick={() => void cargar()}>
            Aplicar
          </Button>
        </div>

        {err ? <p className="text-sm text-destructive">{err}</p> : null}

        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fecha</TableHead>
                <TableHead>Acción</TableHead>
                <TableHead>Entidad</TableHead>
                <TableHead>Actor</TableHead>
                <TableHead>Motivo</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {registros.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-muted-foreground">
                    Sin registros.
                  </TableCell>
                </TableRow>
              ) : (
                registros.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="whitespace-nowrap tabular-nums">
                      {new Date(r.timestamp).toLocaleString('es-AR')}
                    </TableCell>
                    <TableCell>{r.accion}</TableCell>
                    <TableCell>{r.entidad}</TableCell>
                    <TableCell className="font-mono text-xs">{r.actor ?? '—'}</TableCell>
                    <TableCell>{r.motivo || '—'}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
