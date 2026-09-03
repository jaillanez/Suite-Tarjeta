'use client';

// Utilidades del portal municipal (PASO 05):
//  - useIdleLogout: cierra la sesión municipal por inactividad (§ timeout de 10 min).
//  - useDraft: persiste el borrador de un formulario para no perder trabajo si vence la sesión.

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { limpiarSesion } from './session';

export const TIMEOUT_MIN = Number(process.env.NEXT_PUBLIC_SESION_MUNICIPAL_MIN ?? 10);

const EVENTOS = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'] as const;

/**
 * Cierra la sesión tras `min` minutos sin actividad. Avisa un minuto antes.
 * Los borradores ya viven en sessionStorage (useDraft), así que no se pierde lo tipeado.
 */
export function useIdleLogout(min: number = TIMEOUT_MIN): { restanteSeg: number | null } {
  const router = useRouter();
  const [restanteSeg, setRestanteSeg] = useState<number | null>(null);
  const vence = useRef<number>(Date.now() + min * 60_000);

  const reiniciar = useCallback(() => {
    vence.current = Date.now() + min * 60_000;
    setRestanteSeg(null);
  }, [min]);

  useEffect(() => {
    for (const e of EVENTOS) window.addEventListener(e, reiniciar, { passive: true });
    const timer = window.setInterval(() => {
      const restante = Math.round((vence.current - Date.now()) / 1000);
      if (restante <= 0) {
        limpiarSesion();
        router.push('/login?motivo=timeout');
      } else if (restante <= 60) {
        setRestanteSeg(restante);
      }
    }, 1000);
    return () => {
      for (const e of EVENTOS) window.removeEventListener(e, reiniciar);
      window.clearInterval(timer);
    };
  }, [reiniciar, router]);

  return { restanteSeg };
}

/** Persiste un valor de formulario en sessionStorage bajo `clave`. */
export function useDraft<T>(clave: string, inicial: T): [T, (v: T) => void, () => void] {
  const full = `tarjeta_draft_${clave}`;
  const [valor, setValor] = useState<T>(inicial);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(full);
      if (raw) setValor(JSON.parse(raw) as T);
    } catch {
      // almacenamiento no disponible
    }
  }, [full]);

  const set = useCallback(
    (v: T) => {
      setValor(v);
      try {
        sessionStorage.setItem(full, JSON.stringify(v));
      } catch {
        // ignore
      }
    },
    [full],
  );

  const limpiar = useCallback(() => {
    setValor(inicial);
    try {
      sessionStorage.removeItem(full);
    } catch {
      // ignore
    }
  }, [full, inicial]);

  return [valor, set, limpiar];
}
