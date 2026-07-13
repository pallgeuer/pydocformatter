document.documentElement.dataset.pydocformatterDocs = "true";

(() => {
  const getPalette = () => (typeof __md_get === "function" ? __md_get("__palette") : null);
  const autoInput = document.querySelector('[data-md-color-media="(prefers-color-scheme)"]');
  const media = window.matchMedia("(prefers-color-scheme: dark)");

  const applyAutoPalette = () => {
    if (getPalette() || !(autoInput instanceof HTMLInputElement)) {
      return;
    }
    const resolvedInput = document.querySelector(media.matches ? '[data-md-color-media="(prefers-color-scheme: dark)"]' : '[data-md-color-media="(prefers-color-scheme: light)"]');
    if (!(resolvedInput instanceof HTMLInputElement)) {
      return;
    }
    autoInput.checked = true;
    document.body.setAttribute("data-md-color-media", resolvedInput.dataset.mdColorMedia || "");
    document.body.setAttribute("data-md-color-scheme", resolvedInput.dataset.mdColorScheme || "");
    document.body.setAttribute("data-md-color-primary", resolvedInput.dataset.mdColorPrimary || "");
    document.body.setAttribute("data-md-color-accent", resolvedInput.dataset.mdColorAccent || "");
  };

  applyAutoPalette();
  media.addEventListener("change", applyAutoPalette);
})();
