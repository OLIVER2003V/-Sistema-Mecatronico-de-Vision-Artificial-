// Reglas minimas pero utiles: atrapan variables muertas, dependencias
// faltantes en los hooks y errores de JSX que no se ven hasta que la
// pantalla se rompe en produccion.
module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module', ecmaFeatures: { jsx: true } },
  settings: { react: { version: 'detect' } },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', 'node_modules'],
  rules: {
    // El proyecto no usa PropTypes; los componentes son chicos y locales.
    'react/prop-types': 'off',
    'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
  },
}
