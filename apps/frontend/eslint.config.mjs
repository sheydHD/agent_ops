// =============================================================================
// ESLint v9 Flat Config — AgentOps Demo Frontend
// =============================================================================
import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintcompat";
import js from "@eslint/js";
import tseslint from "typescript-eslint";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

export default tseslint.config(
  // Base JS recommended rules
  js.configs.recommended,

  // TypeScript strict + stylistic rules
  ...tseslint.configs.strict,
  ...tseslint.configs.stylistic,

  // Next.js recommended rules (via compat layer)
  ...compat.extends("next/core-web-vitals"),

  // Project-specific overrides
  {
    rules: {
      // TypeScript
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/consistent-type-imports": [
        "error",
        { prefer: "type-imports", fixStyle: "inline-type-imports" },
      ],
      "@typescript-eslint/no-empty-interface": "off",
      "@typescript-eslint/no-non-null-assertion": "warn",

      // React
      "react/self-closing-comp": "error",
      "react/jsx-curly-brace-presence": [
        "error",
        { props: "never", children: "never" },
      ],

      // General
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "prefer-const": "error",
      eqeqeq: ["error", "always"],
      "no-var": "error",
    },
  },

  // Ignore patterns
  {
    ignores: [
      ".next/",
      "node_modules/",
      "out/",
      "next-env.d.ts",
      "*.config.js",
      "*.config.mjs",
    ],
  },
);
