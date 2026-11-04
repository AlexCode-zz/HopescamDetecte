/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "#FDF9F5",
        surface: "#FFFFFF",
        ink: "#1A181A",
        muted: "#6E6670",
        border: "#E7E4E0",
        primary: "#7C3AED",
        "primary-hover": "#6D28D9",
        attention: "#D97706",
        success: "#047857",
        danger: "#B91C1C",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["'Source Serif 4'", "ui-serif", "Georgia", "serif"],
      },
      fontSize: {
        "display": ["2.5rem", { lineHeight: "2.8", fontWeight: "700", letterSpacing: "-0.02em" }],
        "h1": ["2.5rem", { lineHeight: "2.8", fontWeight: "700", letterSpacing: "-0.02em" }],
        "h2": ["1.5rem", { lineHeight: "2", fontWeight: "600" }],
        "h3": ["1.125rem", { lineHeight: "1.6", fontWeight: "600" }],
        "body": ["1rem", { lineHeight: "1.7", fontWeight: "400" }],
        "small": ["0.875rem", { lineHeight: "1.5", fontWeight: "400" }],
        "xs": ["0.75rem", { lineHeight: "1.5", fontWeight: "400" }],
      },
      spacing: {
        "section": "2.5rem",
      },
      borderRadius: {
        "sm": "0.5rem",
        "md": "0.75rem",
        "lg": "1rem",
        "none": "0",
      },
      boxShadow: {
        "soft": "0 1px 3px 0 rgb(0 0 0 / 0.04), 0 1px 2px -1px rgb(0 0 0 / 0.04)",
        "card": "0 4px 6px -1px rgb(0 0 0 / 0.03), 0 2px 4px -2px rgb(0 0 0 / 0.03)",
      },
      animation: {
        "fade-up": "fadeUp 0.6s ease-out forwards",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
