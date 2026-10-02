import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'

export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  js.configs.recommended,
  ...pluginVue.configs['flat/essential'],
  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: globals.browser,
    },
    rules: {
      // Course tabs and form widgets edit the object their parent passes in, by design.
      'vue/no-mutating-props': 'off',
      // Screen components keep their one-word names (Home, Login, Navbar...).
      'vue/multi-word-component-names': 'off',
    },
  },
  {
    files: ['vite.config.js', 'replace-html-vars.js', 'eslint.config.js'],
    languageOptions: { globals: globals.node },
  },
]
