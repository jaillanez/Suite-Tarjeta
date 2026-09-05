'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BadgeCheck, Coins, CreditCard, House, Ticket } from 'lucide-react';
import { cn } from '@tarjeta/ui';

// Navegación del ciudadano: barra inferior fija (patrón móvil) para que todas las
// pantallas sean alcanzables. Antes no existía y las pantallas quedaban inconexas.
const TABS = [
  { href: '/inicio', label: 'Inicio', icon: House },
  { href: '/tarjeta', label: 'Tarjeta', icon: CreditCard },
  { href: '/beneficios', label: 'Beneficios', icon: Ticket },
  { href: '/puntos', label: 'Puntos', icon: Coins },
  { href: '/mi-estado', label: 'Mi estado', icon: BadgeCheck },
];

export default function CiudadanoLayout({ children }: { children: ReactNode }) {
  const path = usePathname();
  return (
    <div className="min-h-dvh pb-[calc(env(safe-area-inset-bottom)+4.5rem)]">
      {children}
      <nav
        className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur"
        aria-label="Navegación principal"
      >
        <ul className="mx-auto flex max-w-md items-stretch justify-around">
          {TABS.map(({ href, label, icon: Icon }) => {
            const activo = path === href || path.startsWith(`${href}/`);
            return (
              <li key={href} className="flex-1">
                <Link
                  href={href}
                  aria-current={activo ? 'page' : undefined}
                  className={cn(
                    'flex flex-col items-center gap-0.5 py-2 text-[11px] transition-colors',
                    activo ? 'font-medium text-primary' : 'text-muted-foreground',
                  )}
                >
                  <Icon className="size-5" aria-hidden="true" />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
