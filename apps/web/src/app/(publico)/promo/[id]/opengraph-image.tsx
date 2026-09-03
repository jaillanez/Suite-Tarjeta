import { ImageResponse } from 'next/og';

export const alt = 'Promoción · Tarjeta de Beneficios';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

interface Props {
  params: Promise<{ id: string }>;
}

export default async function OgImage({ params }: Props) {
  const { id } = await params;
  const municipio = process.env.NEXT_PUBLIC_MUNICIPIO_NOMBRE ?? 'Municipio';
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          padding: 80,
          background: 'linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%)',
          color: 'white',
          fontSize: 48,
        }}
      >
        <div style={{ fontSize: 32, opacity: 0.85 }}>Tarjeta de Beneficios · {municipio}</div>
        <div style={{ fontSize: 88, fontWeight: 700 }}>Promoción #{id}</div>
        <div style={{ fontSize: 36, opacity: 0.9 }}>Mostrá tu tarjeta y ahorrá</div>
      </div>
    ),
    size,
  );
}
