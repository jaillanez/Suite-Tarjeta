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

export const config = {
  matcher: [
    // Portal comercio
    '/promociones/:path*',
    '/sucursales/:path*',
    '/usuarios/:path*',
    '/caja/:path*',
    '/reportes/:path*',
    // Portal municipal
    '/comercios/:path*',
    '/ciudadanos/:path*',
    '/moderacion/:path*',
    '/campanias/:path*',
    '/tablero/:path*',
    '/parametria/:path*',
  ],
};
