import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'ar.gob.tarjeta.app',
  appName: 'Tarjeta de Beneficios',
  // El export estático de Next produce apps/mobile/out
  webDir: 'out',
};

export default config;
