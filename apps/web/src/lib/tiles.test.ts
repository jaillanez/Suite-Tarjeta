// §14.1: el mapa falla cerrado en producción y funciona en desarrollo.

import { describe, expect, it } from 'vitest';
import { resolverTiles } from './tiles';

describe('resolverTiles', () => {
  it('producción SIN tiles propios => null (no cae al OSM público)', () => {
    expect(resolverTiles(undefined, undefined, true)).toBeNull();
    expect(resolverTiles('', '', true)).toBeNull();
  });

  it('desarrollo SIN configurar => usa OSM público', () => {
    const t = resolverTiles(undefined, undefined, false);
    expect(t).not.toBeNull();
    expect(t?.url).toContain('tile.openstreetmap.org');
    expect(t?.attribution).toContain('OpenStreetMap');
  });

  it('con tiles propios configurados => se usan (en prod y en dev)', () => {
    const propia = 'https://tiles.rivadavia.gob.ar/{z}/{x}/{y}.png';
    for (const esProd of [true, false]) {
      const t = resolverTiles(propia, 'Municipio de Rivadavia', esProd);
      expect(t).toEqual({ url: propia, attribution: 'Municipio de Rivadavia' });
    }
  });
});
