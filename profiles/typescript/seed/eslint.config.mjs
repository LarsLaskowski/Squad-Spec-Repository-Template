// ESLint flat config seeded by the Squad-Spec-Repository-Template `typescript` profile.
// typescript-eslint's type-aware rules (strictTypeChecked, through the project service) and
// eslint-plugin-sonarjs run locally, so the analyzer gate finds what SonarQube Cloud would report.
import js from "@eslint/js";
import sonarjs from "eslint-plugin-sonarjs";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist/**", "coverage/**", "node_modules/**"] },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  sonarjs.configs.recommended,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    // Configuration files are plain JavaScript outside the TypeScript project.
    files: ["**/*.js", "**/*.mjs", "**/*.cjs"],
    ...tseslint.configs.disableTypeChecked,
  },
);
