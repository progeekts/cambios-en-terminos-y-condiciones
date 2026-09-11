import os
import json
import difflib
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

TRACKED_DIR = "tracked_policies"
DATA_FILE = "docs/diffs.json"
TARGETS_FILE = "scripts/targets.json"

# Diccionario de palabras clave para clasificar el impacto
IMPACT_RULES = {
    "Entrenamiento de IA / Machine Learning": [
        r"\bartificial intelligence\b", r"\bmachine learning\b", r"\btrain(ing)? models?\b",
        r"\bentrenamiento de modelos\b", r"\binteligencia artificial\b"
    ],
    "Cesión de datos a terceros / Venta": [
        r"\bthird-party partners?\b", r"\bshare your data\b", r"\bsell personal information\b",
        r"\bcompartir con terceros\b", r"\bcesión de datos\b"
    ],
    "Arbitraje obligatorio / Renuncia a demandas colectivas": [
        r"\bbinding arbitration\b", r"\bclass action waiver\b", r"\barbitraje vinculante\b",
        r"\brenuncia a demanda colectiva\b"
    ],
    "Cambio de jurisdicción / Ley aplicable": [
        r"\bgoverning law\b", r"\bjurisdiction\b", r"\blegislación aplicable\b",
        r"\btribunales competentes\b"
    ]
}

def clean_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        tag.decompose()
    
    text = soup.get_text(separator="\n")
    # Normalizar saltos de línea y espacios
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    clean_lines = [line for line in lines if line]
    return "\n".join(clean_lines)

def analyze_impact(added_lines):
    detected_impacts = []
    combined_text = " ".join(added_lines).lower()
    
    for category, patterns in IMPACT_RULES.items():
        for pattern in patterns:
            if re.search(pattern, combined_text):
                detected_impacts.append(category)
                break
    return detected_impacts

def main():
    os.makedirs(TRACKED_DIR, exist_ok=True)
    os.makedirs("docs", exist_ok=True)

    with open(TARGETS_FILE, "r", encoding="utf-8") as f:
        targets = json.load(f)

    diff_log = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                diff_log = json.load(f)
        except Exception:
            diff_log = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    current_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    for target in targets:
        policy_id = target["id"]
        filepath = os.path.join(TRACKED_DIR, f"{policy_id}.txt")
        
        try:
            res = requests.get(target["url"], headers=headers, timeout=20)
            if res.status_code != 200:
                print(f"Error {res.status_code} fetching {target['url']}")
                continue
            
            new_text = clean_html(res.text)
        except Exception as e:
            print(f"Fallo al descargar {target['url']}: {e}")
            continue

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                old_text = f.read()

            old_lines = old_text.splitlines(keepends=True)
            new_lines = new_text.splitlines(keepends=True)

            diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))

            if diff:
                added_lines = [line[1:] for line in diff if line.startswith("+") and not line.startswith("+++")]
                removed_lines = [line[1:] for line in diff if line.startswith("-") and not line.startswith("---")]

                impacts = analyze_impact(added_lines)
                severity = "Alta" if len(impacts) > 0 else "Baja"

                diff_entry = {
                    "id": policy_id,
                    "platform": target["platform"],
                    "type": target["type"],
                    "url": target["url"],
                    "date": current_date,
                    "severity": severity,
                    "impacts": impacts,
                    "added_count": len(added_lines),
                    "removed_count": len(removed_lines),
                    "raw_diff": "".join(diff[:150]) # Limitar tamaño si es masivo
                }
                diff_log.insert(0, diff_entry)

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_text)
        else:
            # Primera inicialización
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_text)

    # Mantener el log en los últimos 200 cambios
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(diff_log[:200], f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()