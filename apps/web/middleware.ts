import { NextResponse } from 'next/server';

// TODO(PASO 03): implementar autenticación real junto con el módulo `identidad`.
// Placeholder: no bloquea ninguna ruta todavía.
export function middleware() {
  return NextResponse.next();
}

export const config = {
  matcher: [],
};
