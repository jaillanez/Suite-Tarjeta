import { NextResponse, type NextRequest } from 'next/server';

// Protección real de rutas de comercio y municipio (reemplaza el placeholder del PASO 02).
// La cookie solo indica presencia de sesión; la validez del token la valida la API.
export function middleware(req: NextRequest) {
  const logueado = req.cookies.get('tarjeta_sesion')?.value === '1';
  if (!logueado) {
    const url = req.nextUrl.clone();
    url.pathname = '/login';
    url.searchParams.set('next', req.nextUrl.pathname);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

// §12.3-C: política centralizada por espacio de nombres de rutas. Toda ruta privada nueva se
// suma acá; la API igual valida siempre (el middleware es comodidad, no seguridad).
export const config = {
  matcher: [
    // Portal comercio
    '/promociones/:path*',
    '/sucursales/:path*',
    '/usuarios/:path*',
    '/caja/:path*',
    '/reportes/:path*',
    '/mi-comercio/:path*',
    '/contenido/:path*',
    // Portal municipal
    '/comercios/:path*',
    '/ciudadanos/:path*',
    '/moderacion/:path*',
    '/campanias/:path*',
    '/tablero/:path*',
    '/parametria/:path*',
    '/agentes/:path*',
    '/aprobaciones/:path*',
    '/auditoria/:path*',
    '/puntos/:path*',
    '/piezas/:path*',
    // Ciudadano autenticado
    '/perfil/:path*',
    '/seleccionar-perfil/:path*',
    '/mi-estado/:path*',
  ],
};
