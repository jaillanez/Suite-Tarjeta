'use client';

import { type FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from '@tarjeta/ui';
import { api } from '@/lib/api';
import { mensajeDeError } from '@/lib/errores';
import { guardarAccessToken } from '@/lib/session';

export default function LoginPage() {
  const router = useRouter();
  const [dni, setDni] = useState('');
  const [password, setPassword] = useState('');
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [codigo, setCodigo] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  function continuar(): void {
    const next = new URLSearchParams(window.location.search).get('next');
    router.push(next ?? '/perfil');
  }

  async function onLogin(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    setError(null);
    setCargando(true);
    try {
      const r = await api.login(dni, password);
      if (r.mfa_requerido && r.mfa_token) {
        setMfaToken(r.mfa_token);
      } else if (r.tokens) {
        // El refresh quedó en la cookie HttpOnly; solo guardamos el access en memoria.
        guardarAccessToken(r.tokens.access_token);
        continuar();
      }
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setCargando(false);
    }
  }

  async function onMfa(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    if (!mfaToken) return;
    setError(null);
    setCargando(true);
    try {
      const r = await api.mfaVerificar(mfaToken, codigo);
      if (r.tokens) {
        guardarAccessToken(r.tokens.access_token);
        continuar();
      }
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setCargando(false);
    }
  }

  return (
    <Card className="mx-auto max-w-sm">
      <CardHeader>
        <CardTitle>Iniciar sesión</CardTitle>
      </CardHeader>
      <CardContent>
        {error ? (
          <p className="mb-3 text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
        {mfaToken === null ? (
          <form onSubmit={onLogin} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="dni">DNI</Label>
              <Input id="dni" value={dni} onChange={(e) => setDni(e.target.value)} required />
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
            <Button type="submit" disabled={cargando} className="w-full">
              Entrar
            </Button>
          </form>
        ) : (
          <form onSubmit={onMfa} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="codigo">Código de verificación (MFA)</Label>
              <Input
                id="codigo"
                inputMode="numeric"
                value={codigo}
                onChange={(e) => setCodigo(e.target.value)}
                required
              />
            </div>
            <Button type="submit" disabled={cargando} className="w-full">
              Verificar
            </Button>
          </form>
        )}
        <p className="mt-4 text-sm text-muted-foreground">
          ¿No tenés cuenta? <Link href="/registro" className="underline">Registrate</Link>
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          ¿Olvidaste tu contraseña?{' '}
          <Link href="/recuperar" className="underline">
            Recuperala
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
