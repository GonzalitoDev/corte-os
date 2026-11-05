const state = {
  release: null,
};

function humanSize(bytes) {
  const value = Number(bytes || 0);
  if (!value) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let index = 0;
  let current = value;
  while (current >= 1024 && index < units.length - 1) {
    current /= 1024;
    index += 1;
  }
  return `${current.toFixed(current >= 100 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function disableDownload(button, label) {
  if (!button) return;
  button.classList.add("disabled");
  button.setAttribute("aria-disabled", "true");
  button.setAttribute("href", "#");
  button.addEventListener("click", (event) => {
    if (button.getAttribute("aria-disabled") === "true") {
      event.preventDefault();
    }
  });
  if (label) {
    const span = button.querySelector("span");
    if (span) span.textContent = label;
  }
}

function enableDownload(button, url, size) {
  if (!button) return;
  button.classList.remove("disabled");
  button.setAttribute("aria-disabled", "false");
  button.setAttribute("href", url);
  button.setAttribute("download", "");
  const span = button.querySelector("span");
  if (span) span.textContent = "Descargar Corte OS (beta)";
  const small = button.querySelector("small");
  if (small) small.textContent = `ISO · ${humanSize(size)}`;
}

function renderScreenshots(items) {
  const container = document.getElementById("screenshots");
  if (!container || !Array.isArray(items) || items.length === 0) return;
  container.innerHTML = "";
  items.forEach((item) => {
    if (!item || !item.src) return;
    const figure = document.createElement("figure");
    figure.className = "screenshot";
    const image = document.createElement("img");
    image.src = item.src;
    image.alt = item.caption || "Captura de Corte OS";
    image.loading = "lazy";
    const caption = document.createElement("figcaption");
    caption.textContent = item.caption || "";
    figure.append(image, caption);
    container.append(figure);
  });
}

async function loadRelease() {
  try {
    const response = await fetch("release.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    return null;
  }
}

async function boot() {
  const release = await loadRelease();
  const buttons = [
    document.getElementById("download-button"),
    document.getElementById("download-button-2"),
  ];

  if (!release) {
    setText("status-badge", "Beta ? metadatos no disponibles");
    setText("download-description", "No se pudo leer release.json. La descarga beta permanece desactivada.");
    buttons.forEach((button) => disableDownload(button, "Descarga no disponible"));
    return;
  }

  state.release = release;
  const iso = release.iso || {};
  const available = Boolean(iso.url);
  setText("meta-version", release.version || "—");
  setText("download-version", (release.version || "—") + " · beta");
  setText("iso-size", available ? humanSize(iso.size) : "—");
  setText("release-date", formatDate(release.released));
  setText("release-state", available ? "Beta disponible" : "Beta pendiente");
  setText("status-badge", available ? "Beta · descarga disponible" : "Beta · compilación pendiente");
  setText("sha256", iso.sha256 || "Pendiente de compilación");
  setText(
    "download-description",
    available
      ? "Esta es la beta 0.1.0 de Corte OS para VirtualBox. Arranca e instala, pero puede tener fallos. Probalá en una máquina virtual y reportá lo que se rompa."
      : "La ISO beta se publica únicamente después de compilarla y superar las pruebas automáticas de arranque e instalación."
  );

  if (available) {
    buttons.forEach((button) => enableDownload(button, iso.url, iso.size));
  } else {
    buttons.forEach((button) => disableDownload(button, "Descarga no disponible"));
  }

  renderScreenshots(release.screenshots);
}

document.getElementById("copy-sha")?.addEventListener("click", async () => {
  const value = document.getElementById("sha256")?.textContent || "";
  if (!value || value.startsWith("Pendiente")) return;
  try {
    await navigator.clipboard.writeText(value);
    const button = document.getElementById("copy-sha");
    button.textContent = "Copiado";
    setTimeout(() => { button.textContent = "Copiar"; }, 1600);
  } catch (error) {
    /* El portapapeles requiere contexto seguro; no se simula el resultado. */
  }
});

boot();
