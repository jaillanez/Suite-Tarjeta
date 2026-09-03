import { cn } from '../lib/utils';

export type Nivel = 'GENERAL' | 'BLACK';

export interface NivelBadgeProps {
  nivel: Nivel;
  className?: string;
}

/** Muestra el nivel del ciudadano (General o Black) con su color. */
export function NivelBadge({ nivel, className }: NivelBadgeProps) {
  const isBlack = nivel === 'BLACK';
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold tracking-wide',
        isBlack
          ? 'bg-nivel-black text-nivel-black-foreground'
          : 'bg-nivel-general text-nivel-general-foreground',
        className,
      )}
    >
      {isBlack ? 'Black' : 'General'}
    </span>
  );
}
