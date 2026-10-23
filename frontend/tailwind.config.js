export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: { 950: "#060A12", 900: "#0A101C", 800: "#101828", 700: "#1A2540", 600: "#26324D" },
        paper: { DEFAULT: "#F3F4F6", dim: "#E5E7EB", ink: "#0B1220" },
        safety: {
          orange: "#FF6A13",
          yellow: "#FFC72C",
          red: "#E5322D", // icons, borders (not for small text)
          "red-text": "#FF7A75", // red as text on navy: 7:1
          "red-fill": "#C9261F", // red behind white text: 5.5:1
        },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "Segoe UI", "Roboto", "Helvetica", "Arial", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
