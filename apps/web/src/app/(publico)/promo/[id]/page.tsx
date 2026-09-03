import type { Metadata } from 'next';

interface PromoParams {
  params: Promise<{ id: string }>;
}

// La razón de que esta app sea SSR: los links compartidos en redes necesitan
// vista previa (Open Graph) generada en el servidor. La imagen la produce
// opengraph-image.tsx (Next la agrega automáticamente a los metadatos).
export async function generateMetadata({ params }: PromoParams): Promise<Metadata> {
  const { id } = await params;
  const title = `Promoción #${id}`;
  const description = 'Beneficio exclusivo en comercios adheridos. Mostrá tu tarjeta y ahorrá.';
  return {
    title,
    description,
    openGraph: { title, description, type: 'website' },
    twitter: { card: 'summary_large_image', title, description },
  };
}

export default async function PromoPage({ params }: PromoParams) {
  const { id } = await params;
  return (
    <article className="space-y-3">
      <h1 className="text-2xl font-semibold">Promoción #{id}</h1>
      <p className="text-muted-foreground">
        Detalle de la promoción (datos de prueba, PASO 02). Esta página genera Open Graph para
        compartir en redes.
      </p>
    </article>
  );
}
