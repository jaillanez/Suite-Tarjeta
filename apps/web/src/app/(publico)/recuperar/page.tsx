'use client';

import { type FormEvent, useState } from 'react';
import Link from 'next/link';
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from '@tarjeta/ui';
import { api } from '@/lib/api';
import { mensajeDeError } from '@/lib/errores';

export default function RecuperarPage() {
  const [email, setEmail] = useState('');
  const [enviado, setEnviado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    setError(null);
    setCargando(true);
    try {
      await api.recuperar(email);
      setEnviado(true); // respuesta uniforme: no revela si la cuenta existe
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setCargando(false);
    }
  }

  if (enviado) {
    return (
      <Card className="mx-auto max-w-sm">
        <CardHeader>
          <CardTitle>Revisá tu correo</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p>Si la cuenta existe, te enviamos instrucciones para restablecer la contraseña.</p>
          <Link href="/login" className="text-primary underline">
            Volver a iniciar sesión
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mx-auto max-w-sm">
      <CardHeader>
        <CardTitle>Recuperar cuenta</CardTitle>
      </CardHeader>
      <CardContent>
        {error ? (
          <p className="mb-3 text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <Button type="submit" disabled={cargando} className="w-full">
            Enviar instrucciones
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
