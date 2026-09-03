import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Consumimos los paquetes del workspace como código fuente TS.
  transpilePackages: ['@tarjeta/ui', '@tarjeta/api-client'],
};

export default nextConfig;
