import proshli from "@proshli/eslint-config";

export default [
  ...proshli,
  {
    ignores: ["dist/**", "node_modules/**"],
  },
];
