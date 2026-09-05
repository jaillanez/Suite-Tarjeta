// §14.1: resolución de la fuente de tiles del mapa, con "fail-closed" en producción.
//
// - Si hay tiles propios configurados (`NEXT_PUBLIC_TILES_URL`), se usan siempre.
// - Si NO hay configuración y el build es de **producción**, el mapa NO cae al servidor público de
//   OSM (eso filtraría la IP y la zona que mira cada vecino a un tercero, y viola la política de
//   OSM): devuelve `null` y la UI muestra "mapa no disponible".
// - Si NO hay configuración y el build es de **desarrollo**, usa OSM público (comodidad local).
//
// La distinción es por entorno de compilación (`esProd`), no por una bandera que alguien pueda
// olvidar de setear.

export interface TilesConfig {
  url: string;
  attribution: string;
}

const OSM_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const OSM_ATTR = '© OpenStreetMap contributors';

export function resolverTiles(
  urlConfigurada: string | undefined,
  attrConfigurada: string | undefined,
  esProd: boolean,
): TilesConfig | null {
  if (urlConfigurada) {
    return { url: urlConfigurada, attribution: attrConfigurada || OSM_ATTR };
  }
  if (esProd) {
    return null; // fail-closed: sin tiles propios no se usa el servidor público
  }
  return { url: OSM_URL, attribution: attrConfigurada || OSM_ATTR };
}
