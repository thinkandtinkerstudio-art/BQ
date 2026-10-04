// Mirrors the lint rule Figma applies when building account-library plugins (unused vars must start with "_").
import tseslint from 'typescript-eslint';
export default [
  ...tseslint.configs.recommended,
  { rules: { '@typescript-eslint/no-unused-vars': ['error', { varsIgnorePattern: '^_', argsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' }] } },
];
