// P3: flujo de recuperación de cuenta en la web (solicitar + confirmar).

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const push = vi.hoisted(() => vi.fn());

vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }));
vi.mock('@/lib/api', () => ({
  api: { recuperar: vi.fn(), recuperarConfirmar: vi.fn() },
}));

import { api } from '@/lib/api';
import RecuperarConfirmarPage from './confirmar/page';
import RecuperarPage from './page';

const apiMock = api as unknown as {
  recuperar: ReturnType<typeof vi.fn>;
  recuperarConfirmar: ReturnType<typeof vi.fn>;
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('RecuperarPage', () => {
  it('envía el email y muestra el aviso uniforme', async () => {
    apiMock.recuperar.mockResolvedValue({ mensaje: 'ok' });
    render(<RecuperarPage />);

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'vecino@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /enviar instrucciones/i }));

    await waitFor(() => expect(screen.getByText(/revisá tu correo/i)).toBeTruthy());
    expect(apiMock.recuperar).toHaveBeenCalledWith('vecino@example.com');
  });
});

describe('RecuperarConfirmarPage', () => {
  it('confirma la nueva contraseña y va al login', async () => {
    apiMock.recuperarConfirmar.mockResolvedValue({ mensaje: 'ok' });
    render(<RecuperarConfirmarPage />);

    fireEvent.change(screen.getByLabelText(/código de recuperación/i), {
      target: { value: 'token-123' },
    });
    fireEvent.change(screen.getByLabelText(/nueva contraseña/i), {
      target: { value: 'contrasena-nueva-123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /cambiar contraseña/i }));

    await waitFor(() =>
      expect(apiMock.recuperarConfirmar).toHaveBeenCalledWith('token-123', 'contrasena-nueva-123'),
    );
    expect(push).toHaveBeenCalledWith('/login?recuperada=1');
  });
});
