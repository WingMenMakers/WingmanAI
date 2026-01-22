export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}"
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}

const toggleTheme = () => {
  document.documentElement.classList.toggle("dark");
};
