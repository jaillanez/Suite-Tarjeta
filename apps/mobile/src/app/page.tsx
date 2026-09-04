import Link from 'next/link';
import { HealthStatus } from '@/components/HealthStatus';

const municipio = process.env.NEXT_PUBLIC_MUNICIPIO_NOMBRE ?? 'Municipio';

export default function Home() {
  return (
    <main className="mx-auto max-w-md space-y-6 p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Tarjeta de Beneficios</h1>
        <HealthStatus />
      </div>
      {/* Landing previa al login: no se muestra una credencial de ejemplo (no aparentar datos
          reales). La tarjeta real vive en /tarjeta una vez iniciada la sesión. */}
      <p className="text-sm text-muted-foreground">
        Beneficios del municipio de {municipio}. Iniciá sesión para ver tu tarjeta y tus
        descuentos.
      </p>
      <nav className="grid gap-3" aria-label="Accesos">
        <Link className="rounded-lg border border-border p-4" href="/inicio">
          Entrar como ciudadano
        </Link>
        <Link className="rounded-lg border border-border p-4" href="/caja">
          Caja del comercio
        </Link>
        <Link className="rounded-lg border border-border p-4" href="/seleccionar-perfil">
          Cambiar de perfil
        </Link>
      </nav>
    </main>
  );
}
