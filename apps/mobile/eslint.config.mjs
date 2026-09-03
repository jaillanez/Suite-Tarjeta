import base from '@tarjeta/config/eslint';

export default [...base, { ignores: ['.next/**', 'out/**', 'android/**', 'ios/**', 'next-env.d.ts'] }];
