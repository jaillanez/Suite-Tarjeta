import base from '@tarjeta/config/eslint';

export default [...base, { ignores: ['.next/**', 'out/**', 'next-env.d.ts'] }];
