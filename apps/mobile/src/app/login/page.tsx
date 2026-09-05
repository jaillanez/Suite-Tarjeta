'use client';

import { type FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ApiError } from '@tarjeta/api-client';
import { Button, Input, Label, Marca } from '@tarjeta/ui';
import { api } from '@/lib/api';
import { guardarSesion } from '@/lib/session';

export default function LoginPage() {
  const router = useRouter();
  const [dni, setDni] = useState('');
  const [password, setPassword] = useState('');
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [codigo, setCodigo] = useState('');
  const [error, setError] = useState<string | null>(null);

  async function onLogin(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    setError(null);
    try {
      const r = await api.login(dni, password);
      if (r.mfa_requerido && r.mfa_token) {
        setMfaToken(r.mfa_token);
      } else if (r.tokens) {
        await guardarSesion(r.tokens.access_token, r.tokens.refresh_token);
        router.push('/seleccionar-perfil');
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No pudimos iniciar sesión.');
    }
  }

  async function onMfa(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    if (!mfaToken) return;
    setError(null);
    try {
      const r = await api.mfaVerificar(mfaToken, codigo);
      if (r.tokens) {
        await guardarSesion(r.tokens.access_token, r.tokens.refresh_token);
        router.push('/seleccionar-perfil');
      }
    } catch {
      setError('Código inválido.');
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center gap-6 p-6">
      <div className="flex flex-col items-center gap-3 text-center">
        <Marca variante="wordmark" alto={44} />
        <h1 className="text-lg font-semibold">
          {mfaToken === null ? 'Iniciar sesión' : 'Verificación en dos pasos'}
        </h1>
      </div>
      {error ? (
        <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
      {mfaToken === null ? (
        <form onSubmit={onLogin} className="space-y-4 rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="space-y-1.5">
            <Label htmlFor="dni">DNI</Label>
            <Input id="dni" inputMode="numeric" value={dni} onChange={(e) => setDni(e.target.value)} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Contraseña</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <Button type="submit" size="lg" className="w-full">
            Entrar
          </Button>
        </form>
      ) : (
        <form onSubmit={onMfa} className="space-y-4 rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="space-y-1.5">
            <Label htmlFor="codigo">Código de verificación</Label>
            <Input
              id="codigo"
              inputMode="numeric"
              value={codigo}
              onChange={(e) => setCodigo(e.target.value)}
              required
            />
          </div>
          <Button type="submit" size="lg" className="w-full">
            Verificar
          </Button>
        </form>
      )}
    </main>
  );
}
