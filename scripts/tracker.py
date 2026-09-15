import os
import json
import difflib
import re
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

TRACKED_DIR = "tracked_policies"
DATA_FILE = "docs/diffs.json"
STATUS_FILE = "docs/status.json"
TARGETS_FILE = "scripts/targets.json"
MAX_LOG = 300
MAX_DIFF_LINES = 220

IMPACT_RULES = {
    "IA y entrenamiento": [r"artificial intelligence", r"machine learning", r"training (our )?models", r"train.*models", r"inteligencia artificial", r"entrenamiento.*modelos"],
    "Datos personales": [r"personal data", r"personal information", r"datos personales", r"información personal", r"biometric", r"biométric"],
    "Terceros y cesión de datos": [r"third part(y|ies)", r"affiliates", r"partners", r"share.*data", r"sell.*personal", r"service providers", r"terceros", r"compartir.*datos", r"cesión.*datos"],
    "Transferencias internacionales": [r"overseas transfer", r"international transfer", r"cross-border", r"transfer.*countr", r"transferencia.*internacional", r"fuera.*país"],
    "Conservación y eliminación": [r"retention", r"retain.*data", r"account deletion", r"delete.*data", r"conservación", r"retención", r"eliminación.*datos"],
    "Publicidad y personalización": [r"advertis", r"personalized", r"personalised", r"targeted ads", r"publicidad", r"personalización"],
    "Propiedad y licencias de contenido": [r"license.*content", r"intellectual property", r"ownership.*content", r"licencia.*contenido", r"propiedad intelectual"],
    "Arbitraje y acciones colectivas": [r"binding arbitration", r"class action waiver", r"dispute resolution", r"arbitraje vinculante", r"demanda colectiva"],
    "Jurisdicción y ley aplicable": [r"governing law", r"jurisdiction", r"applicable law", r"legislación aplicable", r"tribunales competentes"],
    "Precios y suscripciones": [r"subscription", r"pricing", r"fees?", r"billing", r"renewal", r"suscripción", r"precio", r"tarifa", r"renovación"],
    "Derechos del usuario": [r"your rights", r"right to object", r"right to access", r"opt.?out", r"consent", r"tus derechos", r"derecho.*oposición", r"consentimiento"]
}

HIGH_IMPACT = {"IA y entrenamiento", "Terceros y cesión de datos", "Arbitraje y acciones colectivas", "Propiedad y licencias de contenido", "Precios y suscripciones"}
MEDIUM_IMPACT = {"Datos personales", "Transferencias internacionales", "Conservación y eliminación", "Publicidad y personalización", "Jurisdicción y ley aplicable", "Derechos del usuario"}


def clean_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def analyze_impact(added_lines, removed_lines):
    text = " ".join(added_lines + removed_lines).lower()
    impacts = []
    for category, patterns in IMPACT_RULES.items():
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            impacts.append(category)
    return impacts


def classify_relevance(impacts, added_count, removed_count):
    impact_set = set(impacts)
    if impact_set & HIGH_IMPACT or len(impacts) >= 3:
        return "Alta"
    if impact_set & MEDIUM_IMPACT or (added_count + removed_count) >= 20:
        return "Media"
    return "Baja"


def build_summary(impacts, added_count, removed_count):
    total = added_count + removed_count
    if impacts:
        topics = ", ".join(impacts[:3])
        suffix = " y otras áreas" if len(impacts) > 3 else ""
        return f"Se detectaron {total} líneas modificadas con posibles cambios relacionados con {topics}{suffix}."
    return f"Se detectaron {total} líneas modificadas. No coincidieron con las categorías sensibles configuradas."


def main():
    os.makedirs(TRACKED_DIR, exist_ok=True)
    os.makedirs("docs", exist_ok=True)
    with open(TARGETS_FILE, "r", encoding="utf-8") as f:
        targets = json.load(f)

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            diff_log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        diff_log = []

    headers = {"User-Agent": "PolicyChangeObservatory/2.0 (+https://github.com/progeekts/cambios-en-terminos-y-condiciones)"}
    now = datetime.now(timezone.utc)
    current_date = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    status = {"last_check": current_date, "targets": len(targets), "ok": 0, "errors": [], "changes": 0}

    for target in targets:
        policy_id = target["id"]
        filepath = os.path.join(TRACKED_DIR, f"{policy_id}.txt")
        try:
            res = requests.get(target["url"], headers=headers, timeout=30, allow_redirects=True)
            res.raise_for_status()
            new_text = clean_html(res.text)
            if len(new_text) < 500:
                raise ValueError("contenido extraído demasiado corto")
            status["ok"] += 1
        except Exception as exc:
            status["errors"].append({"id": policy_id, "platform": target["platform"], "error": str(exc)[:180]})
            continue

        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_text)
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            old_text = f.read()
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        diff = list(difflib.unified_diff(old_lines, new_lines, fromfile="versión anterior", tofile="versión nueva", lineterm=""))
        if not diff:
            continue

        added_lines = [line[1:] for line in diff if line.startswith("+") and not line.startswith("+++")]
        removed_lines = [line[1:] for line in diff if line.startswith("-") and not line.startswith("---")]
        impacts = analyze_impact(added_lines, removed_lines)
        relevance = classify_relevance(impacts, len(added_lines), len(removed_lines))
        diff_log.insert(0, {
            "id": policy_id,
            "platform": target["platform"],
            "type": target["type"],
            "url": target["url"],
            "date": current_date,
            "severity": relevance,
            "relevance": relevance,
            "impacts": impacts,
            "added_count": len(added_lines),
            "removed_count": len(removed_lines),
            "summary": build_summary(impacts, len(added_lines), len(removed_lines)),
            "raw_diff": "".join(diff[:MAX_DIFF_LINES])
        })
        status["changes"] += 1
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_text)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(diff_log[:MAX_LOG], f, indent=2, ensure_ascii=False)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
