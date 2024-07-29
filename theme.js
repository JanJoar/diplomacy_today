// Initialize theme based on preferred color scheme
const prefersDarkScheme = window.matchMedia("(prefers-color-scheme: dark)").matches;
if (prefersDarkScheme) {
    document.documentElement.className = "theme-dark";
} else {
    document.documentElement.className = "theme-light";
}
