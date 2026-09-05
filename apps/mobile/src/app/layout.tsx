import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import { AlmacenSeguroInit } from '@/components/AlmacenSeguroInit';
import './globals.css';

export const metadata: Metadata = {
  title: 'Tarjeta de Beneficios · Rivadavia',
  description: 'Tu tarjeta de beneficios del municipio de Rivadavia.',
};

export const viewport: Viewport = {
  themeColor: '#4a863c',
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-dvh">
        <AlmacenSeguroInit />
        {children}
      </body>
    </html>
  );
}
