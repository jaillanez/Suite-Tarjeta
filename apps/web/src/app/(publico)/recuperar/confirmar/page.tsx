'use client';

import { type FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from '@tarjeta/ui';
import { api } from '@/lib/api';
import { mensajeDeError } from '@/lib/errores';

export default function RecuperarConfirmarPage() {
  const router = useRouter();
  const [token, setToken] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    // El enlace del email trae ?token=...; también se puede pegar a mano.
    const t = new URLSearchParams(window.location.search).get('token');
    if (t) setToken(t);
  }, []);

  async function onSubmit(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    setError(null);
    setCargando(true);
    try {
      await api.recuperarConfirmar(token, password);
      router.push('/login?recuperada=1');
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setCargando(false);
    }
  }

  return (
    <Card className="mx-auto max-w-sm">
      <CardHeader>
        <CardTitle>Nueva contraseña</CardTitle>
      </CardHeader>
      <CardContent>
        {error ? (
          <p className="mb-3 text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="token">Código de recuperación</Label>
            <Input id="token" value={token} onChange={(e) => setToken(e.target.value)} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Nueva contraseña</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <Button type="submit" disabled={cargando} className="w-full">
            Cambiar contraseña
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
