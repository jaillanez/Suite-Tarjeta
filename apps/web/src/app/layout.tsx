import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import Link from 'next/link';
import './globals.css';
import { HealthStatus } from '@/components/HealthStatus';

const municipio = process.env.NEXT_PUBLIC_MUNICIPIO_NOMBRE ?? 'Municipio';

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000'),
  title: {
    default: `Tarjeta de Beneficios · ${municipio}`,
    template: `%s · Tarjeta de Beneficios`,
  },
  description: 'Programa de beneficios municipal: descuentos en comercios adheridos.',
};

export const viewport: Viewport = {
  themeColor: '#1e40af',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-dvh">
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          <Link href="/" className="font-semibold">
            Tarjeta de Beneficios
          </Link>
          <nav className="flex items-center gap-4 text-sm" aria-label="Principal">
            <Link href="/beneficios">Beneficios</Link>
            <Link href="/promociones">Comercio</Link>
            <Link href="/tablero">Municipio</Link>
            <HealthStatus />
          </nav>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
