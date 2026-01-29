export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}"
  ],
  theme: {
    extend: {},
  },
  plugins: [
  require('@tailwindcss/typography'),
],
}

const toggleTheme = () => {
  document.documentElement.classList.toggle("dark");
};
