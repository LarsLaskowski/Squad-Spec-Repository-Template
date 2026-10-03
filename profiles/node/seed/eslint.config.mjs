// ESLint flat config seeded by the Squad-Spec-Repository-Template `node` profile.
// eslint-plugin-sonarjs runs the SonarQube JS/TS rules locally, so the analyzer gate finds
// what SonarQube Cloud would report.
import js from "@eslint/js";
import sonarjs from "eslint-plugin-sonarjs";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist/**", "coverage/**", "node_modules/**"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  sonarjs.configs.recommended,
);
