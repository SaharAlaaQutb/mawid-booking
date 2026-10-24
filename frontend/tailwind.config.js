/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "var(--color-bg)",
        surface: "var(--color-surface)",
        primary: {
          DEFAULT: "var(--color-primary)",
          hover: "var(--color-primary-hover)",
        },
        accent: "var(--color-accent)",
        text: "var(--color-text)",
        muted: "var(--color-muted)",
        border: "var(--color-border)",
        success: "var(--color-success)",
        warning: "var(--color-warning)",
        danger: "var(--color-danger)",
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
        sm: "calc(var(--radius) - 4px)",
        lg: "calc(var(--radius) + 4px)",
      },
      fontFamily: {
        sans: ["Cairo", "Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 12px 32px rgb(15 23 42 / 0.08)",
      },
    },
  },
  plugins: [],
};
