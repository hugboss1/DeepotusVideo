/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        deep: {
          950: "#020D24",
          900: "#051226",
          800: "#0A1A38",
          700: "#0F2350",
        },
        bio: {
          cyan: "#00E0FF",
          violet: "#7B2CFF",
          gold: "#F5C518",
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', "system-ui", "sans-serif"],
        body: ['"Inter"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      boxShadow: {
        glow: "0 0 24px -2px rgba(0, 224, 255, 0.4)",
        "glow-violet": "0 0 24px -2px rgba(123, 44, 255, 0.4)",
      },
    },
  },
  plugins: [],
};
