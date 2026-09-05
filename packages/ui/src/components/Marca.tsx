import { cn } from '../lib/utils';

export type MarcaVariante = 'wordmark' | 'emblema';

export interface MarcaProps {
  /** "wordmark" = logotipo completo "Rivadavia Cumple"; "emblema" = solo el tilde ✓. */
  variante?: MarcaVariante;
  /** Alto en píxeles. El ancho se ajusta manteniendo la proporción. */
  alto?: number;
  className?: string;
}

// Proporciones reales de los archivos oficiales (public/marca).
const RATIO: Record<MarcaVariante, number> = {
  wordmark: 960 / 401,
  emblema: 1,
};
const SRC: Record<MarcaVariante, string> = {
  wordmark: '/marca/rivadavia-cumple.png',
  emblema: '/marca/tilde.png',
};

/**
 * Logotipo oficial del municipio de Rivadavia ("Rivadavia Cumple").
 * Sirve los archivos desde `public/marca` de cada app, así funciona igual en web y
 * en el export estático de Capacitor. Sin lógica: solo presentación.
 */
export function Marca({ variante = 'wordmark', alto = 40, className }: MarcaProps) {
  const ancho = Math.round(alto * RATIO[variante]);
  return (
    // Paquete compartido sin Next: <img> plano (funciona en web y en el export estático móvil).
    <img
      src={SRC[variante]}
      alt="Rivadavia Cumple"
      width={ancho}
      height={alto}
      className={cn('select-none', className)}
      draggable={false}
    />
  );
}
