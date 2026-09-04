'use client';

import QRCode from 'react-qr-code';

/**
 * §12.2-B: el token del ciudadano se muestra como un QR **escaneable** por el cajero, no en texto
 * plano. El token rota cada 45 s; este componente solo renderiza el vigente.
 */
export function QrToken({ token }: { token: string | null }) {
  if (!token) {
    return <p className="mt-2 text-xs text-muted-foreground">Generando tu código…</p>;
  }
  return (
    <div className="mt-2 flex justify-center">
      <div className="rounded-lg bg-white p-3">
        <QRCode value={token} size={192} aria-label="Código QR para escanear en la caja" />
      </div>
    </div>
  );
}
