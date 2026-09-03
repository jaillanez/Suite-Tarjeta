'use client';

import { useCallback, useEffect, useState } from 'react';
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
import { api } from '@/lib/api';
import { useDraft } from '@/lib/municipal';

export default function ParametriaPage() {
  const [params, setParams] = useState<Record<string, number> | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  // Borrador: valores editados que aún no se guardaron (se conservan si vence la sesión).
  const [borrador, setBorrador, limpiarBorrador] = useDraft<Record<string, string>>(
    'parametria',
    {},
  );

  const cargar = useCallback(async () => {
    try {
      setParams(await api.parametros());
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo cargar la parametría.');
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function guardar(clave: string): Promise<void> {
    setMsg(null);
    const crudo = borrador[clave];
    if (crudo === undefined || crudo === '') return;
    const valor = Number(crudo);
    if (!Number.isInteger(valor)) {
      setMsg('El valor debe ser un número entero.');
      return;
    }
    try {
      await api.cambiarParametro(clave, valor, 'edición desde el portal');
      const resto = { ...borrador };
      delete resto[clave];
      setBorrador(resto);
      await cargar();
      setMsg(`"${clave}" actualizado.`);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'No se pudo guardar.');
    }
  }

  if (!params) return <p className="text-muted-foreground">Cargando…</p>;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Parametría del programa</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Cambiar reglas sensibles de niveles requiere doble conformidad; estos parámetros se
          aplican al confirmar.
        </p>
        {msg ? <p className="text-sm">{msg}</p> : null}
        <div className="space-y-3">
          {Object.entries(params).map(([clave, valor]) => {
            const editado = borrador[clave];
            const dirty = editado !== undefined && editado !== '' && Number(editado) !== valor;
            return (
              <div key={clave} className="flex flex-wrap items-end gap-3">
                <div className="grow">
                  <Label htmlFor={clave}>{clave}</Label>
                  <Input
                    id={clave}
                    type="number"
                    value={editado ?? String(valor)}
                    onChange={(e) => setBorrador({ ...borrador, [clave]: e.target.value })}
                    className="mt-1 max-w-40"
                  />
                </div>
                <Button size="sm" disabled={!dirty} onClick={() => guardar(clave)}>
                  Guardar
                </Button>
              </div>
            );
          })}
        </div>
        {Object.keys(borrador).length > 0 ? (
          <Button size="sm" variant="outline" onClick={limpiarBorrador}>
            Descartar cambios sin guardar
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
