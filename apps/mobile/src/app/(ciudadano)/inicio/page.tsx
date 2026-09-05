'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { BadgeCheck, ChevronRight, Coins, Ticket, Users } from 'lucide-react';
import type { EstadoCiudadano, PersonaMe } from '@tarjeta/api-client';
import { Button, Marca, type Nivel, TarjetaCredencial } from '@tarjeta/ui';
import { api } from '@/lib/api';
import { esSesionVencida, mensajeDeError } from '@/lib/errores';

const municipio = process.env.NEXT_PUBLIC_MUNICIPIO_NOMBRE ?? 'Rivadavia';

const ACCIONES = [
  { href: '/beneficios', icon: Ticket, titulo: 'Beneficios', desc: 'Descuentos en comercios adheridos' },
  { href: '/puntos', icon: Coins, titulo: 'Puntos', desc: 'Tu saldo y movimientos' },
  { href: '/mi-estado', icon: BadgeCheck, titulo: 'Mi estado', desc: 'Tu nivel y cómo subir' },
  { href: '/grupo', icon: Users, titulo: 'Grupo familiar', desc: 'Integrantes y billetera común' },
];

export default function InicioPage() {
  const router = useRouter();
  const [me, setMe] = useState<PersonaMe | null>(null);
  const [estado, setEstado] = useState<EstadoCiudadano | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      const [m, e] = await Promise.all([api.me(), api.miEstado()]);
      setMe(m);
      setEstado(e);
    } catch (err) {
      if (esSesionVencida(err)) router.push('/login');
      else setError(mensajeDeError(err));
    }
  }, [router]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const nombre = me?.nombre ?? '';

  return (
    <main className="mx-auto max-w-md space-y-6 p-5 pt-[calc(env(safe-area-inset-top)+1rem)]">
      <header className="flex items-center justify-between">
        <div className="min-w-0">
          <p className="truncate text-sm text-muted-foreground">Hola{nombre ? `, ${nombre}` : ''}</p>
          <h1 className="text-xl font-bold">Tu tarjeta de {municipio}</h1>
        </div>
        <Marca variante="emblema" alto={28} />
      </header>

      {error && !estado ? (
        <div className="space-y-3" role="alert">
          <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
          <Button variant="outline" onClick={() => void cargar()}>
            Reintentar
          </Button>
        </div>
      ) : null}

      {estado ? (
        <Link href="/tarjeta" className="block">
          <TarjetaCredencial
            nombre={me ? `${me.nombre} ${me.apellido}`.trim() : '—'}
            numero={estado.numero_tarjeta}
            nivel={estado.nivel as Nivel}
            municipio={municipio}
          />
          <p className="mt-2 flex items-center justify-center gap-1 text-sm font-medium text-primary">
            Ver mi tarjeta y QR <ChevronRight className="size-4" aria-hidden="true" />
          </p>
        </Link>
      ) : !error ? (
        <div className="aspect-[1.586/1] w-full animate-pulse rounded-xl bg-muted" aria-hidden="true" />
      ) : null}

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground">Accesos</h2>
        <div className="grid gap-3">
          {ACCIONES.map(({ href, icon: Icon, titulo, desc }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-4 rounded-xl border border-border bg-card p-4 transition-colors active:bg-accent"
            >
              <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-700">
                <Icon className="size-5" aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold">{titulo}</span>
                <span className="block text-sm text-muted-foreground">{desc}</span>
              </span>
              <ChevronRight className="size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
