/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        field: "#1f6f3a",
        endzone: "#174d29",
      },
    },
  },
  plugins: [],
};
