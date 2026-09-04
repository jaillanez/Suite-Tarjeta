import type { Metadata } from 'next';
import type { FichaPublicaOut } from '@tarjeta/api-client';

interface PromoParams {
  params: Promise<{ id: string }>;
}

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function getFicha(id: string): Promise<FichaPublicaOut | null> {
  try {
    const r = await fetch(`${API}/api/v1/promociones/${encodeURIComponent(id)}`, {
      next: { revalidate: 60 },
    });
    if (!r.ok) return null;
    return (await r.json()) as FichaPublicaOut;
  } catch {
    return null;
  }
}

function beneficioTexto(f: FichaPublicaOut): string {
  if (f.mecanica === 'PORCENTAJE') return `${f.valor_black}% de descuento`;
  if (f.mecanica === 'DOS_POR_UNO') return '2x1';
  if (f.mecanica === 'MONTO_FIJO') return `$${f.valor_black} de descuento`;
  return f.titulo;
}

// La razón de que esta app sea SSR: los links compartidos en redes necesitan vista previa
// (Open Graph) generada en el servidor. La imagen la produce opengraph-image.tsx.
export async function generateMetadata({ params }: PromoParams): Promise<Metadata> {
  const { id } = await params;
  const ficha = await getFicha(id);
  const title = ficha ? ficha.titulo : `Promoción #${id}`;
  const description = ficha
    ? `${beneficioTexto(ficha)} en comercios adheridos. Mostrá tu tarjeta y ahorrá.`
    : 'Beneficio en comercios adheridos.';
  return {
    title,
    description,
    openGraph: { title, description, type: 'website' },
    twitter: { card: 'summary_large_image', title, description },
  };
}

export default async function PromoPage({ params }: PromoParams) {
  const { id } = await params;
  const ficha = await getFicha(id);

  if (!ficha) {
    return (
      <article className="space-y-3">
        <h1 className="text-2xl font-semibold">Promoción no encontrada</h1>
        <p className="text-muted-foreground">Puede que el enlace sea incorrecto.</p>
      </article>
    );
  }

  return (
    <article className="mx-auto max-w-lg space-y-4">
      {ficha.imagen_url ? (
        <img src={ficha.imagen_url} alt={ficha.titulo} className="w-full rounded-lg" />
      ) : null}
      <h1 className="text-2xl font-semibold">{ficha.titulo}</h1>
      <p className="text-lg font-medium text-primary">{beneficioTexto(ficha)}</p>
      <p className="text-muted-foreground">{ficha.descripcion}</p>
      {ficha.disponible ? (
        <p className="text-sm">Mostrá tu tarjeta en la caja para aprovecharla.</p>
      ) : (
        <p className="rounded-md border border-amber-500/50 bg-amber-500/10 px-4 py-2 text-sm">
          Esta promoción no está disponible en este momento
          {ficha.estado === 'VENCIDA' ? ' (venció)' : ''}
          {ficha.estado === 'PAUSADA' ? ' (pausada por el comercio)' : ''}.
        </p>
      )}
    </article>
  );
}
