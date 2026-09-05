import Link from 'next/link';
import { ChevronRight, Repeat2, Store, UserRound } from 'lucide-react';
import { cn, Marca } from '@tarjeta/ui';
import { HealthStatus } from '@/components/HealthStatus';

const municipio = process.env.NEXT_PUBLIC_MUNICIPIO_NOMBRE ?? 'Rivadavia';

const accesos = [
  {
    href: '/inicio',
    icon: UserRound,
    titulo: 'Entrar como ciudadano',
    desc: 'Tu tarjeta, beneficios y puntos',
    principal: true,
  },
  {
    href: '/caja',
    icon: Store,
    titulo: 'Caja del comercio',
    desc: 'Validar y registrar consumos',
    principal: false,
  },
  {
    href: '/seleccionar-perfil',
    icon: Repeat2,
    titulo: 'Cambiar de perfil',
    desc: 'Alternar entre tus perfiles',
    principal: false,
  },
];

export default function Home() {
  return (
    <div className="min-h-dvh bg-background">
      <header className="flex items-center justify-between px-5 pb-3 pt-[calc(env(safe-area-inset-top)+1rem)]">
        <Marca variante="wordmark" alto={34} />
        <HealthStatus />
      </header>

      <main className="mx-auto max-w-md space-y-8 px-5 pb-10">
        {/* Hero de marca: no muestra una credencial de ejemplo (no aparentar datos reales). */}
        <section className="rounded-2xl bg-gradient-to-br from-brand-600 to-brand-900 p-6 text-white shadow-lg">
          <p className="text-sm font-medium text-white/80">Municipio de {municipio}</p>
          <h1 className="mt-1 text-2xl font-bold leading-tight">Tarjeta de Beneficios</h1>
          <p className="mt-2 text-sm leading-relaxed text-white/85">
            Descuentos en comercios adheridos. Iniciá sesión para ver tu tarjeta y tus beneficios.
          </p>
        </section>

        <nav className="space-y-3" aria-label="Accesos">
          {accesos.map(({ href, icon: Icon, titulo, desc, principal }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-4 rounded-xl border p-4 transition-colors',
                principal
                  ? 'border-transparent bg-primary text-primary-foreground shadow-sm active:bg-primary/90'
                  : 'border-border bg-card active:bg-accent',
              )}
            >
              <span
                className={cn(
                  'flex size-11 shrink-0 items-center justify-center rounded-full',
                  principal ? 'bg-white/15' : 'bg-brand-50 text-brand-700',
                )}
              >
                <Icon className="size-5" aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold">{titulo}</span>
                <span
                  className={cn('block text-sm', principal ? 'text-white/80' : 'text-muted-foreground')}
                >
                  {desc}
                </span>
              </span>
              <ChevronRight
                className={cn('size-5 shrink-0', principal ? 'text-white/70' : 'text-muted-foreground')}
                aria-hidden="true"
              />
            </Link>
          ))}
        </nav>

        <p className="text-center text-xs text-muted-foreground">
          Municipalidad de {municipio} · San Juan
        </p>
      </main>
    </div>
  );
}
