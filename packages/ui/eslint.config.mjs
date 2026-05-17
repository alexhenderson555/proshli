import otklik from "@otklik/eslint-config";

export default [
  ...otklik,
  {
    ignores: ["dist/**", "node_modules/**"],
  },
];
