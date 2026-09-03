import { cn } from '../lib/utils';
import { NivelBadge, type Nivel } from './NivelBadge';

export interface TarjetaCredencialProps {
  nombre: string;
  numero: string;
  nivel: Nivel;
  municipio: string;
  className?: string;
}

function formatNumero(numero: string): string {
  const digits = numero.replace(/\D/g, '').padEnd(16, '•').slice(0, 16);
  return digits.replace(/(.{4})/g, '$1 ').trim();
}

/** Tarjeta visual del ciudadano (credencial). Sin lógica: solo presentación. */
export function TarjetaCredencial({
  nombre,
  numero,
  nivel,
  municipio,
  className,
}: TarjetaCredencialProps) {
  const isBlack = nivel === 'BLACK';
  return (
    <div
      className={cn(
        'flex aspect-[1.586/1] w-full max-w-sm flex-col justify-between rounded-xl p-5 shadow-lg',
        isBlack
          ? 'bg-nivel-black text-nivel-black-foreground'
          : 'bg-gradient-to-br from-brand-500 to-brand-900 text-white',
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <span className="text-sm font-medium opacity-90">{municipio}</span>
        <NivelBadge nivel={nivel} />
      </div>
      <div className="space-y-1">
        <p className="font-mono text-lg tracking-widest tabular-nums">{formatNumero(numero)}</p>
        <p className="text-sm uppercase tracking-wide opacity-90">{nombre}</p>
      </div>
    </div>
  );
}
