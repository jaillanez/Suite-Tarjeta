import Link from 'next/link';

// Selector de contexto (§11.2): una sola credencial, varios perfiles.
const PERFILES = [
  { href: '/inicio', titulo: 'Ciudadano', desc: 'Tu tarjeta, beneficios y puntos' },
  { href: '/caja', titulo: 'Comercio', desc: 'Caja y turno' },
  { href: '/operacion', titulo: 'Municipal', desc: 'Operación en calle' },
];

export default function SeleccionarPerfil() {
  return (
    <main className="mx-auto max-w-md space-y-4 p-4">
      <h1 className="text-lg font-semibold">Elegí con qué perfil entrás</h1>
      <ul className="grid gap-3">
        {PERFILES.map((p) => (
          <li key={p.href}>
            <Link className="block rounded-lg border border-border p-4" href={p.href}>
              <span className="font-medium">{p.titulo}</span>
              <span className="block text-sm text-muted-foreground">{p.desc}</span>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
