import eslint from '@eslint/js';
import eslintConfigPrettier from 'eslint-config-prettier';
import eslintPluginVue from 'eslint-plugin-vue';
import globals from 'globals';
import typescriptEslint from 'typescript-eslint';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));

export default typescriptEslint.config(
  { ignores: ['*.d.ts', '**/coverage', '**/dist'] },
  {
    extends: [
      eslint.configs.recommended,
      ...typescriptEslint.configs.recommended,
      ...eslintPluginVue.configs['flat/recommended'],
    ],
    files: ['**/*.{ts,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: globals.browser,
      parserOptions: {
        // Vue SFC parser delegates <script> blocks to TS parser
        parser: typescriptEslint.parser,
        // Fix: explicitly set tsconfigRootDir to avoid ambiguity between src/ and project root
        tsconfigRootDir: __dirname,
        // Use the application tsconfig for type-aware linting
        project: ['./tsconfig.app.json'],
        extraFileExtensions: ['.vue'],
      },
    },
  },
  // Override for Node/Vite config files which are covered by tsconfig.node.json
  {
    files: ['vite.config.ts'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: {
        parser: typescriptEslint.parser,
        tsconfigRootDir: __dirname,
        project: ['./tsconfig.node.json'],
      },
    },
  },
  eslintConfigPrettier
);