import type { Config } from "tailwindcss";

import { tailwindThemeExtend } from "./theme/tailwind-theme.js";

const config: Config = {
  content: [
    "../components/**/*.{js,ts,jsx,tsx,mdx}",
    "../features/**/*.{js,ts,jsx,tsx,mdx}",
    "../app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: tailwindThemeExtend,
  },
  plugins: [],
};

export default config;
