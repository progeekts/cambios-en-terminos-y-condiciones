import os
import shutil
from pathlib import Path

SOURCE = Path("docs")
OUTPUT = Path("hosting-package")
LEGACY_URL = "https://progeekts.github.io/cambios-en-terminos-y-condiciones/"
SITE_URL = os.getenv("SITE_URL", "https://progeekts.es/tyc/").rstrip("/") + "/"
EXCLUDE_SUFFIXES = {".md"}

def should_copy(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() not in EXCLUDE_SUFFIXES

def main():
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)
    for source in SOURCE.rglob("*"):
        if not should_copy(source):
            continue
        relative = source.relative_to(SOURCE)
        target = OUTPUT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            content = source.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            shutil.copy2(source, target)
            continue
        content = content.replace(LEGACY_URL, SITE_URL)
        target.write_text(content, encoding="utf-8")
    (OUTPUT / ".nojekyll").touch(exist_ok=True)
    required = ["index.html", "diffs.json", "status.json"]
    missing = [name for name in required if not (OUTPUT / name).exists()]
    if missing:
        raise SystemExit(f"Faltan archivos esenciales en el paquete: {', '.join(missing)}")
    print(f"Paquete listo para hosting: {OUTPUT.resolve()}")
    print(f"URL objetivo: {SITE_URL}")

if __name__ == "__main__":
    main()
