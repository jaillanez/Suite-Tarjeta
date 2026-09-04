// P2-C: la pantalla de perfil solo expulsa al login si la sesión venció (401). Ante 500/red
// muestra el error con opción de reintentar, en vez de disfrazar todo de "sesión vencida".

import { ApiError } from '@tarjeta/api-client';
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const push = vi.hoisted(() => vi.fn());

vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }));
vi.mock('@/lib/api', () => ({
  api: { me: vi.fn(), dispositivos: vi.fn(), consentimientos: vi.fn() },
}));

import { api } from '@/lib/api';
import PerfilPage from './page';

const apiMock = api as unknown as {
  me: ReturnType<typeof vi.fn>;
  dispositivos: ReturnType<typeof vi.fn>;
  consentimientos: ReturnType<typeof vi.fn>;
};

afterEach(() => {
  vi.clearAllMocks();
});

describe('PerfilPage — manejo de errores', () => {
  it('con 401 vuelve al login', async () => {
    apiMock.me.mockRejectedValue(new ApiError('no auth', 'http_401', 401));
    apiMock.dispositivos.mockResolvedValue([]);
    apiMock.consentimientos.mockResolvedValue({});

    render(<PerfilPage />);

    await waitFor(() => expect(push).toHaveBeenCalledWith('/login'));
    expect(screen.queryByRole('alert')).toBeNull();
    expect(apiMock.me).toHaveBeenCalled();
  });

  it('con 500 muestra el error y NO redirige', async () => {
    apiMock.me.mockRejectedValue(new ApiError('boom', 'http_500', 500));
    apiMock.dispositivos.mockResolvedValue([]);
    apiMock.consentimientos.mockResolvedValue({});

    render(<PerfilPage />);

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(push).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /reintentar/i })).toBeTruthy();
  });
});
