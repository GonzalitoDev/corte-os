# Publicar Corte OS en Corte Editor

La página de descarga está en `web/corte-os/`. Es una página estática que funciona en Vercel o en cualquier hosting estático.

## Archivos

```text
web/corte-os/
  index.html      Página completa
  styles.css      Estilos oscuros de Corte OS
  app.js          Carga release.json y activa la descarga real
  release.json    Metadatos de la versión publicada
  logo.svg        Logo (copiar desde src/assets/logo.svg)
```

## Integración con el sitio actual

El código fuente de Corte Editor no forma parte de este repositorio. Para integrar la sección:

1. Copia `web/corte-os/` al proyecto de Corte Editor, por ejemplo en `public/corte-os/`.
2. Añade un enlace **Sistemas Operativos** en la navegación principal que apunte a `/corte-os/`.
3. Si el sitio usa un framework con rutas, crea una ruta `/corte-os` que renderice el contenido de `index.html` o que redirija a la página estática.
4. No modifiques las rutas ni las funciones existentes de Corte Editor.
5. Mantén el enlace de vuelta a `https://corte-editor-nine.vercel.app/`.

También puedes incrustar solo la sección de descarga en una página existente. Conserva los identificadores `download-button`, `sha256`, `iso-size` y el script `app.js`, o adapta el script al framework.

## release.json

El archivo debe describir el artefacto real. Ejemplo de una versión publicada:

```json
{
  "version": "0.1.0",
  "released": "2026-11-04T12:00:00Z",
  "summary": "Primera versión base de Corte OS para VirtualBox.",
  "iso": {
    "filename": "CorteOS-0.1.0-amd64.iso",
    "size": 1845123456,
    "sha256": "hexadecimal...",
    "sha512": "hexadecimal...",
    "url": "https://github.com/<usuario>/<repo>/releases/download/v0.1.0/CorteOS-0.1.0-amd64.iso"
  },
  "screenshots": [
    {
      "src": "/corte-os/capturas/escritorio.png",
      "caption": "Escritorio de Corte OS"
    }
  ],
  "notes": []
}
```

Reglas:

- `url` debe ser un enlace real y permanente al archivo ISO. GitHub Releases es compatible.
- `size` debe ser el tamaño real en bytes.
- `sha256` y `sha512` deben calcularse sobre la ISO publicada.
- `screenshots` solo debe contener capturas reales obtenidas de una máquina virtual con la ISO arrancada.
- Si `url` está vacío, la página desactiva el botón y muestra “Descarga no disponible”. No se inventa ningún enlace.

## Generar los metadatos desde CI

El workflow de GitHub Actions puede generar `release.json` después de compilar y probar la ISO:

```bash
VERSION=$(cat VERSION)
ISO="dist/CorteOS-${VERSION}-amd64.iso"
SIZE=$(stat -c%s "$ISO")
SHA256=$(sha256sum "$ISO" | cut -d' ' -f1)
SHA512=$(sha512sum "$ISO" | cut -d' ' -f1)
URL="https://github.com/${GITHUB_REPOSITORY}/releases/download/v${VERSION}/$(basename "$ISO")"

python3 - "$VERSION" "$SIZE" "$SHA256" "$SHA512" "$URL" <<'PY'
import json, sys
version, size, sha256, sha512, url = sys.argv[1:6]
data = {
    "version": version,
    "released": __import__("datetime").datetime.utcnow().isoformat(timespec="seconds") + "Z",
    "summary": "Corte OS para VirtualBox.",
    "iso": {
        "filename": f"CorteOS-{version}-amd64.iso",
        "size": int(size),
        "sha256": sha256,
        "sha512": sha512,
        "url": url,
    },
    "screenshots": [],
    "notes": [],
}
with open("web/corte-os/release.json", "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, ensure_ascii=False)
PY
```

Sube `release.json` junto con la página o genera la versión en el despliegue.

## Capturas reales

No publiques maquetas como si fueran capturas. Para obtener capturas:

1. Arranca la ISO en VirtualBox o QEMU.
2. Abre cada aplicación principal.
3. Usa `Print` o `xfce4-screenshooter`.
4. Guarda PNG en `web/corte-os/capturas/`.
5. Añádelas a `screenshots` con una descripción.

## Comprobaciones antes de publicar

- [ ] La ISO arranca en BIOS.
- [ ] La ISO arranca en UEFI.
- [ ] La instalación automática termina.
- [ ] El sistema instalado arranca.
- [ ] Las aplicaciones principales abren.
- [ ] La descarga apunta a un archivo real.
- [ ] El SHA-256 coincide.
- [ ] Las capturas son reales.
- [ ] La página funciona en móvil y escritorio.
- [ ] No se ha roto ninguna función de Corte Editor.
