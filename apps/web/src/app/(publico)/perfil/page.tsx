'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Dispositivo, PersonaMe } from '@tarjeta/api-client';
import { Button, Card, CardContent, CardHeader, CardTitle, NivelBadge } from '@tarjeta/ui';
import { api } from '@/lib/api';
import { esSesionVencida, mensajeDeError } from '@/lib/errores';
import { limpiarAccessToken } from '@/lib/session';

export default function PerfilPage() {
  const router = useRouter();
  const [me, setMe] = useState<PersonaMe | null>(null);
  const [dispositivos, setDispositivos] = useState<Dispositivo[]>([]);
  const [consentimientos, setConsentimientos] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      const [m, d, c] = await Promise.all([
        api.me(),
        api.dispositivos(),
        api.consentimientos(),
      ]);
      setMe(m);
      setDispositivos(d);
      setConsentimientos(c);
    } catch (err) {
      // Solo una sesión vencida expulsa al login; el resto se muestra con opción de reintentar.
      if (esSesionVencida(err)) router.push('/login');
      else setError(mensajeDeError(err));
    }
  }, [router]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function revocar(id: string): Promise<void> {
    await api.revocarDispositivo(id);
    await cargar();
  }

  async function salir(): Promise<void> {
    try {
      await api.logout(); // el refresh viaja en la cookie HttpOnly; el server la revoca y la borra
    } catch {
      // ignore
    }
    limpiarAccessToken();
    router.push('/login');
  }

  if (error) {
    return (
      <div className="space-y-3" role="alert">
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" onClick={() => void cargar()}>
          Reintentar
        </Button>
      </div>
    );
  }

  if (!me) {
    return <p className="text-muted-foreground">Cargando…</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">
          {me.nombre} {me.apellido}
        </h1>
        <Button variant="outline" onClick={salir}>
          Cerrar sesión
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Datos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          <p>DNI: {me.dni}</p>
          <p>CUIL: {me.cuil}</p>
          <p>Celular: {me.celular} {me.celular_verificado ? '✓' : '(sin verificar)'}</p>
          <p>Estado de identidad: {me.estado_identidad}</p>
          <p className="flex items-center gap-2">
            Perfiles:
            {me.perfiles.map((p) =>
              p.tipo === 'CIUDADANO' ? <NivelBadge key={p.clave} nivel="PLATINO" /> : (
                <span key={p.clave} className="rounded bg-secondary px-2 py-0.5 text-xs">
                  {p.tipo}
                </span>
              ),
            )}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Consentimientos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          {Object.entries(consentimientos).map(([tipo, otorgado]) => (
            <p key={tipo}>
              {tipo}: {otorgado ? 'Sí' : 'No'}
            </p>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Dispositivos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {dispositivos.length === 0 ? <p className="text-muted-foreground">Sin dispositivos.</p> : null}
          {dispositivos.map((d) => (
            <div key={d.id} className="flex items-center justify-between">
              <span>
                {d.nombre_declarado} ({d.plataforma}) — {d.estado}
              </span>
              {d.estado === 'ACTIVO' ? (
                <Button size="sm" variant="outline" onClick={() => revocar(d.id)}>
                  Cerrar sesión remota
                </Button>
              ) : null}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
