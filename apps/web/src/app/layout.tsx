import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import Link from 'next/link';
import { Marca } from '@tarjeta/ui';
import './globals.css';
import { HealthStatus } from '@/components/HealthStatus';

const municipio = process.env.NEXT_PUBLIC_MUNICIPIO_NOMBRE ?? 'Rivadavia';

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000'),
  title: {
    default: `Tarjeta de Beneficios · ${municipio}`,
    template: `%s · Tarjeta de Beneficios`,
  },
  description: 'Programa de beneficios municipal: descuentos en comercios adheridos.',
};

export const viewport: Viewport = {
  themeColor: '#4a863c',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-dvh">
        <header className="sticky top-0 z-10 border-b border-border bg-background/90 backdrop-blur">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
            <Link href="/" aria-label={`Tarjeta de Beneficios · ${municipio}`}>
              <Marca variante="wordmark" alto={34} />
            </Link>
            <nav className="flex items-center gap-4 text-sm font-medium" aria-label="Principal">
              <Link className="text-muted-foreground hover:text-foreground" href="/beneficios">
                Beneficios
              </Link>
              <Link className="text-muted-foreground hover:text-foreground" href="/promociones">
                Comercio
              </Link>
              <Link className="text-muted-foreground hover:text-foreground" href="/tablero">
                Municipio
              </Link>
              <HealthStatus />
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
