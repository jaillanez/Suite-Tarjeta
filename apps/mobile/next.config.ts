import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Export estático para empaquetar dentro de Capacitor.
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,
  transpilePackages: ['@tarjeta/ui', '@tarjeta/api-client'],
};

export default nextConfig;
