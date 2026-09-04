import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import { AlmacenSeguroInit } from '@/components/AlmacenSeguroInit';
import './globals.css';

export const metadata: Metadata = {
  title: 'Tarjeta de Beneficios',
  description: 'Tu tarjeta de beneficios municipal.',
};

export const viewport: Viewport = {
  themeColor: '#1e40af',
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
