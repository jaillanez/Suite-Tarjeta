import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { QrToken } from './QrToken';

describe('QrToken (§12.2-B)', () => {
  it('renderiza un QR escaneable (svg) cuando hay token', () => {
    const { container } = render(<QrToken token="token-de-canje-vigente" />);
    expect(container.querySelector('svg')).not.toBeNull();
  });

  it('muestra un placeholder (no texto plano del token) cuando todavía no hay token', () => {
    const { container } = render(<QrToken token={null} />);
    expect(container.querySelector('svg')).toBeNull();
    expect(container.textContent).toContain('Generando');
  });
});
