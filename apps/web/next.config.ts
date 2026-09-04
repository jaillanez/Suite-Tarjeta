import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Consumimos los paquetes del workspace como código fuente TS.
  transpilePackages: ['@tarjeta/ui', '@tarjeta/api-client'],
  // §07.0.A: los tiles del mapa son lo más pesado y no cambian entre visitas. Caché agresiva.
  async headers() {
    return [
      {
        source: '/tiles/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
    ];
  },
};

export default nextConfig;
