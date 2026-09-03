'use client';

import { type FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ApiError, type RegistroBody } from '@tarjeta/api-client';
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from '@tarjeta/ui';
import { api } from '@/lib/api';

const OPCIONALES = [
  { tipo: 'COMUNICACIONES_COMERCIALES', label: 'Comunicaciones comerciales' },
  { tipo: 'GEOLOCALIZACION', label: 'Geolocalización para beneficios cercanos' },
  { tipo: 'ESTADISTICA_ANONIMA', label: 'Datos anónimos para estadística municipal' },
];

export default function RegistroPage() {
  const router = useRouter();
  const [f, setF] = useState({ dni: '', cuil: '', apellido: '', nombre: '', celular: '', password: '' });
  const [tratamiento, setTratamiento] = useState(false);
  const [opcionales, setOpcionales] = useState<Record<string, boolean>>({});
  const [celularEnviado, setCelularEnviado] = useState<string | null>(null);
  const [codigo, setCodigo] = useState('');
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof typeof f) => (e: { target: { value: string } }) =>
    setF((prev) => ({ ...prev, [k]: e.target.value }));

  async function onRegistro(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    setError(null);
    const body: RegistroBody = {
      ...f,
      consentimientos: [
        { tipo: 'TRATAMIENTO_DATOS', otorgado: tratamiento },
        ...OPCIONALES.map((o) => ({ tipo: o.tipo, otorgado: Boolean(opcionales[o.tipo]) })),
      ],
    };
    try {
      await api.registro(body);
      setCelularEnviado(f.celular);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No pudimos registrarte.');
    }
  }

  async function onVerificar(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    if (!celularEnviado) return;
    try {
      await api.verificarCelular(celularEnviado, codigo);
      router.push('/login');
    } catch {
      setError('Código inválido.');
    }
  }

  if (celularEnviado) {
    return (
      <Card className="mx-auto max-w-sm">
        <CardHeader>
          <CardTitle>Verificá tu celular</CardTitle>
        </CardHeader>
        <CardContent>
          {error ? <p className="mb-3 text-sm text-destructive">{error}</p> : null}
          <form onSubmit={onVerificar} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="codigo">Código enviado por SMS</Label>
              <Input id="codigo" value={codigo} onChange={(e) => setCodigo(e.target.value)} required />
            </div>
            <Button type="submit" className="w-full">
              Verificar
            </Button>
          </form>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mx-auto max-w-lg">
      <CardHeader>
        <CardTitle>Crear cuenta</CardTitle>
      </CardHeader>
      <CardContent>
        {error ? (
          <p className="mb-3 text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
        <form onSubmit={onRegistro} className="grid gap-4 sm:grid-cols-2">
          <Field id="dni" label="DNI" value={f.dni} onChange={set('dni')} />
          <Field id="cuil" label="CUIL" value={f.cuil} onChange={set('cuil')} />
          <Field id="apellido" label="Apellido" value={f.apellido} onChange={set('apellido')} />
          <Field id="nombre" label="Nombre" value={f.nombre} onChange={set('nombre')} />
          <Field id="celular" label="Celular" value={f.celular} onChange={set('celular')} />
          <Field id="password" label="Contraseña" type="password" value={f.password} onChange={set('password')} />
          <fieldset className="sm:col-span-2 space-y-2">
            <legend className="text-sm font-medium">Consentimientos</legend>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                aria-label="Tratamiento de datos para operar el programa (obligatorio)"
                checked={tratamiento}
                onChange={(e) => setTratamiento(e.target.checked)}
                required
              />
              Tratamiento de datos para operar el programa (obligatorio)
            </label>
            {OPCIONALES.map((o) => (
              <label key={o.tipo} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  aria-label={o.label}
                  checked={Boolean(opcionales[o.tipo])}
                  onChange={(e) =>
                    setOpcionales((prev) => ({ ...prev, [o.tipo]: e.target.checked }))
                  }
                />
                {o.label} (opcional)
              </label>
            ))}
          </fieldset>
          <Button type="submit" className="sm:col-span-2">
            Registrarme
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function Field(props: {
  id: string;
  label: string;
  value: string;
  onChange: (e: { target: { value: string } }) => void;
  type?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={props.id}>{props.label}</Label>
      <Input
        id={props.id}
        type={props.type ?? 'text'}
        value={props.value}
        onChange={props.onChange}
        required
      />
    </div>
  );
}
