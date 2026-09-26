import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import globals from "globals";

export default [
  { ignores: ["dist/**", "dist-ssr/**", "coverage/**"] },
  js.configs.recommended,
  ...pluginVue.configs["flat/essential"],
  {
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.browser },
    },
  },
  {
    files: ["*.config.js", "replace-html-vars.js"],
    languageOptions: { globals: { ...globals.node } },
  },
];
