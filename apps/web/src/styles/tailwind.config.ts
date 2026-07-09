import type { Config } from "tailwindcss";

import { tailwindThemeExtend } from "./theme/tailwind-theme.js";

const config: Config = {
  content: [
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: tailwindThemeExtend,
  },
  plugins: [],
};

export default config;
