import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      // Axios 客户端模式需要 any 泛型参数，在 API 文件中放宽
      '@typescript-eslint/no-explicit-any': ['error', {
        ignoreRestArgs: false,
        fixToUnknown: false,
      }],
      // 数据获取模式中 useEffect 内调用 setState 是标准 React 实践
      'react-hooks/set-state-in-effect': 'warn',
      // 组件内函数声明提升是 JS 标准行为
      'react-hooks/purity': 'warn',
      'react-hooks/immutability': 'warn',
    },
  },
  {
    // API 文件允许 any（Axios 泛型模式）
    files: ['src/api/**/*.{ts,tsx}'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
])
