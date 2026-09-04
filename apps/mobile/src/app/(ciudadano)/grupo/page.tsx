'use client';

import { useCallback, useEffect, useState } from 'react';
import { ApiError, type MiGrupoOut } from '@tarjeta/api-client';
import { Button } from '@tarjeta/ui';
import { api } from '@/lib/api';

export default function GrupoPage() {
  const [grupo, setGrupo] = useState<MiGrupoOut | null>(null);
  const [token, setToken] = useState('');
  const [invitacion, setInvitacion] = useState<{ token: string; texto: string } | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      setGrupo(await api.miGrupo());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo cargar el grupo.');
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function accion(fn: () => Promise<unknown>, ok: string): Promise<void> {
    setMsg(null);
    setError(null);
    try {
      await fn();
      setMsg(ok);
      await cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo completar la acción.');
    }
  }

  async function crear(modo: string): Promise<void> {
    await accion(() => api.crearGrupo(modo), 'Grupo creado.');
  }

  async function invitar(): Promise<void> {
    setError(null);
    try {
      const inv = await api.invitarAlGrupo();
      setInvitacion({ token: inv.token, texto: inv.texto_declaracion });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo invitar.');
    }
  }

  async function aceptar(): Promise<void> {
    if (!token.trim()) return;
    await accion(() => api.aceptarInvitacionGrupo(token.trim()), 'Te uniste al grupo.');
    setToken('');
  }

  if (!grupo) return <p className="p-4 text-muted-foreground">Cargando…</p>;

  return (
    <main className="mx-auto max-w-md space-y-5 p-4">
      <h1 className="text-lg font-semibold">Grupo familiar</h1>

      {grupo.sin_grupo ? (
        <>
          <section className="rounded-lg border border-border p-4">
            <h2 className="font-medium">Crear un grupo</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Podés compartir tu nivel Black con tu familia. Sos responsable de a quién sumás.
            </p>
            <div className="mt-3 flex gap-2">
              <Button onClick={() => void crear('COMUN')}>Billetera común</Button>
              <Button variant="outline" onClick={() => void crear('INDIVIDUAL')}>
                Billetera individual
              </Button>
            </div>
          </section>
          <section className="rounded-lg border border-border p-4">
            <h2 className="font-medium">Unirme con un código</h2>
            <input
              aria-label="Código de invitación"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Pegá el código que te compartieron"
              className="mt-2 w-full rounded-md border border-border bg-background p-2 text-sm"
            />
            <Button className="mt-2" size="sm" onClick={() => void aceptar()}>
              Unirme
            </Button>
          </section>
        </>
      ) : grupo.es_titular ? (
        <>
          <section className="rounded-lg border border-border p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-medium">Tu grupo</h2>
              <span className="text-xs text-muted-foreground">Modo: {grupo.modo_billetera}</span>
            </div>
            <ul className="mt-3 space-y-2">
              {grupo.miembros.map((m) => (
                <li key={m.id_persona} className="rounded-md border border-border p-2 text-sm">
                  <div className="flex justify-between">
                    <span className="font-mono text-xs">{m.id_persona.slice(0, 8)}…</span>
                    <span className="text-muted-foreground">
                      {m.rol === 'TITULAR' ? 'Titular' : m.estado}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Este mes: {m.consumo_mes.operaciones} compras · ${m.consumo_mes.monto} ·{' '}
                    {m.consumo_mes.puntos_acreditados} pts
                  </p>
                  {m.rol !== 'TITULAR' ? (
                    <div className="mt-2 flex gap-2">
                      {m.estado === 'SUSPENDIDO' ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            void accion(() => api.reactivarMiembro(m.id_persona), 'Reactivado.')
                          }
                        >
                          Reactivar
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            void accion(() => api.suspenderMiembro(m.id_persona), 'Suspendido.')
                          }
                        >
                          Suspender
                        </Button>
                      )}
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>

          <section className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => void invitar()}>
              Invitar a alguien
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                void accion(
                  () =>
                    api.cambiarModoGrupo(
                      grupo.modo_billetera === 'COMUN' ? 'INDIVIDUAL' : 'COMUN',
                    ),
                  'Modo actualizado.',
                )
              }
            >
              Pasar a {grupo.modo_billetera === 'COMUN' ? 'individual' : 'común'}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => void accion(() => api.disolverGrupo(), 'Grupo disuelto.')}
            >
              Disolver
            </Button>
          </section>

          {invitacion ? (
            <section className="rounded-lg border-2 border-primary p-4">
              <p className="text-sm">{invitacion.texto}</p>
              <p className="mt-2 text-xs text-muted-foreground">
                Compartí este código (vence en 7 días):
              </p>
              <p className="mt-1 break-all font-mono text-xs">{invitacion.token}</p>
            </section>
          ) : null}
        </>
      ) : (
        <section className="rounded-lg border border-border p-4">
          <p className="text-sm">Pertenecés a un grupo familiar (modo {grupo.modo_billetera}).</p>
          <Button
            className="mt-3"
            size="sm"
            variant="outline"
            onClick={() => void accion(() => api.salirDelGrupo(), 'Saliste del grupo.')}
          >
            Salir del grupo
          </Button>
        </section>
      )}

      {msg ? <p className="text-sm text-green-600">{msg}</p> : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </main>
  );
}
