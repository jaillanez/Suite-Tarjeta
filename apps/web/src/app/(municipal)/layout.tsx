'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@tarjeta/ui';
import { useIdleLogout } from '@/lib/municipal';

const NAV = [
  { href: '/tablero', label: 'Tablero' },
  { href: '/ciudadanos', label: 'Ciudadanos' },
  { href: '/comercios', label: 'Comercios' },
  { href: '/moderacion', label: 'Moderación' },
  { href: '/piezas', label: 'Piezas' },
  { href: '/puntos', label: 'Puntos' },
  { href: '/parametria', label: 'Parametría' },
  { href: '/aprobaciones', label: 'Aprobaciones' },
  { href: '/auditoria', label: 'Auditoría' },
  { href: '/agentes', label: 'Agentes' },
];

export default function MunicipalLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { restanteSeg } = useIdleLogout();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Portal municipal</h1>
        <nav className="flex flex-wrap gap-1 text-sm" aria-label="Portal municipal">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'rounded-md px-3 py-1.5',
                pathname === item.href
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted',
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>

      {restanteSeg !== null ? (
        <div
          role="alert"
          className="rounded-md border border-amber-500/50 bg-amber-500/10 px-4 py-2 text-sm"
        >
          Tu sesión municipal se cerrará por inactividad en {restanteSeg}s. Movete o tocá algo
          para seguir. Lo que tengas escrito queda guardado.
        </div>
      ) : null}

      {children}
    </div>
  );
}
