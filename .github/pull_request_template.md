<!-- Describí qué cambia y por qué. -->

## Qué cambia



## Criterios de aceptación (antes de mergear)

Marcá lo que corresponda. Los docs de estado se actualizan **como el lint o la cobertura**: antes de
mergear, no después.

- [ ] Tests y gates en verde (ruff/mypy/import-linter, lint/typecheck/build/vitest según el área).
- [ ] Si cambió el contrato, regeneré el cliente (`openapi.json` + `schema.generated.ts`).
- [ ] **`docs/estado-funcional.md` refleja este cambio** (lo exige el job `docs_al_dia`). Si el cambio
      no toca el estado funcional, poné en la descripción una línea `docs-al-dia: n/a — <razón>`.
- [ ] **`docs/lista-para-lanzar.md` actualizada** si cambió algo del estado de lanzamiento (un ítem
      pasó a abierto/cerrado, o cambió su dueño/fecha). Ninguna línea queda sin dueño y sin fecha.

<!-- Opt-out del gate de docs (sólo si el cambio no afecta el estado funcional):
docs-al-dia: n/a — <razón>
-->
