// Configuración ESLint compartida (flat config, ESLint 9).
// Las apps la importan y le agregan eslint-config-next.
import js from '@eslint/js';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import tseslint from 'typescript-eslint';

// jsx-a11y en modo ERROR (requisito del PASO 02 / WCAG 2.1 AA).
const a11yRecommended = jsxA11y.flatConfigs.recommended.rules ?? {};
const a11yErrors = Object.fromEntries(
  Object.entries(a11yRecommended).map(([rule, value]) => [rule, value === 'off' ? 'off' : 'error']),
);

export default [
  { ignores: ['**/.next/**', '**/out/**', '**/dist/**', '**/node_modules/**', '**/*.generated.ts'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    plugins: { 'jsx-a11y': jsxA11y },
    rules: {
      ...a11yErrors,
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    },
  },
];
