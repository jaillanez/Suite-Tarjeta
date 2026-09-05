import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Marca,
  NivelBadge,
  TarjetaCredencial,
} from '@tarjeta/ui';

const municipio = process.env.NEXT_PUBLIC_MUNICIPIO_NOMBRE ?? 'Rivadavia';

export default function Home() {
  return (
    <div className="space-y-8">
      <section className="flex flex-col items-start gap-3">
        <span className="inline-flex items-center gap-2 rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700">
          <Marca variante="emblema" alto={18} />
          Municipio de {municipio}
        </span>
        <h1 className="text-3xl font-bold tracking-tight">Tarjeta de Beneficios</h1>
        <p className="max-w-prose text-muted-foreground">
          Descuentos en comercios adheridos de {municipio}. Iniciá sesión para ver tu tarjeta.
        </p>
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <div className="space-y-2">
          <TarjetaCredencial nombre="Nombre y apellido" numero="" nivel="BLACK" municipio={municipio} />
          <p className="text-xs text-muted-foreground">Ejemplo ilustrativo de la tarjeta.</p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Niveles <NivelBadge nivel="PLATINO" /> <NivelBadge nivel="BLACK" />
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            El nivel Black se obtiene al estar al día con el municipio (o heredado por grupo
            familiar).
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
