import base from '@tarjeta/config/eslint';

export default [
  // Los componentes de shadcn/ui son código vendido (upstream): no se lintean.
  { ignores: ['src/components/ui/**'] },
  ...base,
];
