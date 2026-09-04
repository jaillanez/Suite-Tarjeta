// §12.5 / P2-C (móvil): el error al confirmar un canje NO se ignora en silencio. Se muestra al
// ciudadano y la operación queda pendiente para reintentar (no se aplica ni desaparece).

import { ApiError } from '@tarjeta/api-client';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const push = vi.hoisted(() => vi.fn());

vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }));
vi.mock('@/lib/api', () => ({
  api: {
    me: vi.fn(),
    miEstado: vi.fn(),
    misTokensCanje: vi.fn(),
    misPendientesCanje: vi.fn(),
    confirmarCanje: vi.fn(),
    rechazarCanje: vi.fn(),
    generarCodigoCanje: vi.fn(),
  },
}));

import { api } from '@/lib/api';
import TarjetaPage from './page';

const m = api as unknown as {
  me: ReturnType<typeof vi.fn>;
  miEstado: ReturnType<typeof vi.fn>;
  misTokensCanje: ReturnType<typeof vi.fn>;
  misPendientesCanje: ReturnType<typeof vi.fn>;
  confirmarCanje: ReturnType<typeof vi.fn>;
  rechazarCanje: ReturnType<typeof vi.fn>;
  generarCodigoCanje: ReturnType<typeof vi.fn>;
};

const PENDIENTE = {
  id: 'op1',
  numero_comprobante: 'RIV-1',
  estado: 'PENDIENTE_CONFIRMACION',
  monto_bruto: 1000,
  descuento: 200,
  total_pagar: 800,
  confirmador: 'CIUDADANO',
  id_promocion: null,
  nivel_aplicado: 'PLATINO',
  puntos_ciudadano: 0,
  puntos_consumidos: 0,
};

function seedCarga() {
  m.me.mockResolvedValue({ nombre: 'Ana', apellido: 'Gómez' });
  m.miEstado.mockResolvedValue({
    numero_tarjeta: '4000000000000001',
    nivel: 'PLATINO',
    estado_tarjeta: 'ACTIVA',
  });
  m.misTokensCanje.mockResolvedValue([]);
  m.misPendientesCanje.mockResolvedValue([PENDIENTE]);
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('TarjetaPage — confirmación de canje', () => {
  it('si confirmar falla, muestra el error y la operación sigue pendiente', async () => {
    seedCarga();
    m.confirmarCanje.mockRejectedValue(new ApiError('Se agotó el cupo', 'tope', 409));

    render(<TarjetaPage />);

    await waitFor(() => expect(screen.getByText(/confirmá tu compra/i)).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: /aceptar/i }));

    await waitFor(() => expect(screen.getByText('Se agotó el cupo')).toBeTruthy());
    // La operación NO se aplicó: sigue el botón Aceptar disponible; no se redirigió.
    expect(screen.getByRole('button', { name: /aceptar/i })).toBeTruthy();
    expect(push).not.toHaveBeenCalled();
  });

  it('si confirmar sale bien, muestra el descuento aplicado', async () => {
    seedCarga();
    m.confirmarCanje.mockResolvedValue({ ...PENDIENTE, estado: 'APLICADA', puntos_consumidos: 0 });

    render(<TarjetaPage />);

    await waitFor(() => expect(screen.getByText(/confirmá tu compra/i)).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: /aceptar/i }));

    await waitFor(() => expect(screen.getByText(/descuento aplicado/i)).toBeTruthy());
  });
});
