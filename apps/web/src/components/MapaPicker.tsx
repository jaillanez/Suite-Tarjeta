'use client';

// Mapa con pin arrastrable (Leaflet). Los tiles salen de configuración y por defecto se
// sirven como archivo estático desde el propio hosting (§07.0.A: no dependemos del tile
// server público de OSM). Ver docs/tiles-mapa.md. Se carga solo en el cliente (SSR seguro).

import { useEffect, useRef } from 'react';
import 'leaflet/dist/leaflet.css';

// URL de tiles configurable (sin recompilar). Por defecto, tiles propios estáticos.
const TILES_URL = process.env.NEXT_PUBLIC_TILES_URL ?? '/tiles/{z}/{x}/{y}.png';
const TILES_ATTR = process.env.NEXT_PUBLIC_TILES_ATTR ?? 'Mapa © OpenStreetMap · Municipio';

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

  useEffect(() => {
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
      L.tileLayer(TILES_URL, { attribution: TILES_ATTR, maxZoom: 19 }).addTo(map);

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
    <div
      ref={ref}
      className="h-64 w-full overflow-hidden rounded-md border border-border"
      aria-label="Mapa para elegir la ubicación"
    />
  );
}
