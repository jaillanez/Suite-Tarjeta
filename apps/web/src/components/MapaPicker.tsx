'use client';

// Mapa con pin arrastrable (Leaflet). Se carga solo en el cliente (SSR seguro).
// §14.1: en desarrollo usa OSM público sin configurar nada; en producción, si no hay tiles propios
// configurados (NEXT_PUBLIC_TILES_URL), el mapa NO cae al server público: muestra "mapa no
// disponible" (fail-closed). La distinción es por entorno de compilación. Ver docs/tiles-mapa.md.

import { useEffect, useRef, useState } from 'react';
import 'leaflet/dist/leaflet.css';
import { resolverTiles } from '@/lib/tiles';

const TILES = resolverTiles(
  process.env.NEXT_PUBLIC_TILES_URL,
  process.env.NEXT_PUBLIC_TILES_ATTR,
  process.env.NODE_ENV === 'production',
);

interface Props {
  lat: number | null;
  lon: number | null;
  onChange: (lat: number, lon: number) => void;
  /** Centro por defecto si no hay pin (por ejemplo, el municipio). */
  centro?: { lat: number; lon: number };
}

export function MapaPicker({ lat, lon, onChange, centro }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  // §08.0.C / §14.1: si los tiles no cargan (o no hay tiles propios en prod), un aviso claro en
  // vez de un rectángulo en blanco. Si TILES es null (fail-closed), arranca ya con el aviso.
  const [tilesFallan, setTilesFallan] = useState(TILES === null);

  useEffect(() => {
    if (TILES === null) return; // fail-closed: sin tiles propios en prod, no se inicializa el mapa
    const nodo = ref.current;
    if (!nodo) return;
    let map: import('leaflet').Map | null = null;
    let cancelado = false;

    void (async () => {
      const L = await import('leaflet');
      if (cancelado || !nodo) return;
      const inicial: [number, number] = [
        lat ?? centro?.lat ?? -31.5375,
        lon ?? centro?.lon ?? -68.398,
      ];
      map = L.map(nodo).setView(inicial, 14);
      const capa = L.tileLayer(TILES.url, { attribution: TILES.attribution, maxZoom: 19 });
      capa.on('tileerror', () => setTilesFallan(true));
      capa.addTo(map);

      const icono = L.divIcon({
        className: '',
        html: '<div style="font-size:28px;line-height:1">📍</div>',
        iconSize: [28, 28],
        iconAnchor: [14, 28],
      });
      const marker = L.marker(inicial, { draggable: true, icon: icono }).addTo(map);
      marker.on('dragend', () => {
        const p = marker.getLatLng();
        onChangeRef.current(Number(p.lat.toFixed(6)), Number(p.lng.toFixed(6)));
      });
      map.on('click', (e: import('leaflet').LeafletMouseEvent) => {
        marker.setLatLng(e.latlng);
        onChangeRef.current(Number(e.latlng.lat.toFixed(6)), Number(e.latlng.lng.toFixed(6)));
      });
    })();

    return () => {
      cancelado = true;
      map?.remove();
    };
    // Solo se monta una vez; los cambios de pin externos no re-crean el mapa.
  }, []);

  return (
    <div className="relative">
      <div
        ref={ref}
        className="h-64 w-full overflow-hidden rounded-md border border-border"
        aria-label="Mapa para elegir la ubicación"
      />
      {tilesFallan ? (
        <div
          role="alert"
          className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-md bg-background/85 p-4 text-center text-sm"
        >
          El mapa no está disponible en este momento (no se pudieron cargar los tiles). Podés
          seguir usando la app; la ubicación también se puede ajustar más tarde.
        </div>
      ) : null}
    </div>
  );
}
