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
SCHEMA_VERSION = 3
CLASSIFIER_VERSION = 3

CATEGORY_RULES = {
    "IA y entrenamiento": [r"artificial intelligence", r"machine learning", r"training (our )?models", r"train.*models", r"inteligencia artificial", r"entrenamiento.*modelos"],
    "Datos personales": [r"personal data", r"personal information", r"datos personales", r"información personal", r"biometric", r"biométric"],
    "Terceros y cesión de datos": [r"third part(y|ies)", r"affiliates", r"share.*data", r"sell.*personal", r"service providers", r"terceros", r"compartir.*datos", r"cesión.*datos"],
    "Transferencias internacionales": [r"overseas transfer", r"international transfer", r"cross-border", r"transfer.*countr", r"transferencia.*internacional", r"fuera.*país"],
    "Conservación y eliminación": [r"retention", r"retain.*data", r"account deletion", r"delete.*data", r"conservación", r"retención", r"eliminación.*datos"],
    "Publicidad y personalización": [r"advertis", r"personalized", r"personalised", r"targeted ads", r"publicidad", r"personalización"],
    "Propiedad y licencias": [r"license.*content", r"intellectual property", r"ownership.*content", r"licen[cs]e", r"licencia.*contenido", r"propiedad intelectual"],
    "Arbitraje y disputas": [r"binding arbitration", r"class action waiver", r"dispute resolution", r"arbitraje vinculante", r"demanda colectiva", r"resolución de disputas"],
    "Jurisdicción y ley aplicable": [r"governing law", r"jurisdiction", r"applicable law", r"legislación aplicable", r"tribunales competentes"],
    "Precios, pagos y suscripciones": [r"subscription", r"pricing", r"\bfees?\b", r"billing", r"renewal", r"suscripción", r"precio", r"tarifa", r"renovación", r"pago"],
    "Derechos y control del usuario": [r"your rights", r"right to object", r"right to access", r"opt.?out", r"consent", r"tus derechos", r"derecho.*oposición", r"consentimiento"],
    "Seguridad": [r"security measures", r"security incident", r"data breach", r"encryption", r"authentication", r"medidas de seguridad", r"incidente de seguridad", r"cifrado", r"autenticación"],
    "Cumplimiento y auditoría": [r"compliance", r"audit", r"certification", r"iso 27001", r"soc 2", r"cumplimiento", r"auditoría", r"certificación"],
    "Cuenta y acceso al servicio": [r"account", r"suspend", r"terminate", r"access to (the )?service", r"cuenta", r"suspender", r"cancelar.*cuenta", r"acceso.*servicio"]
}

HIGH_IMPACT = {"IA y entrenamiento", "Terceros y cesión de datos", "Arbitraje y disputas", "Propiedad y licencias", "Precios, pagos y suscripciones", "Seguridad"}
MEDIUM_IMPACT = {"Datos personales", "Transferencias internacionales", "Conservación y eliminación", "Publicidad y personalización", "Jurisdicción y ley aplicable", "Derechos y control del usuario", "Cumplimiento y auditoría", "Cuenta y acceso al servicio"}

PLAIN_LANGUAGE = {
    "IA y entrenamiento": "cómo puede utilizarse información o contenido en sistemas de inteligencia artificial o entrenamiento de modelos",
    "Datos personales": "qué datos personales se recopilan o utilizan",
    "Terceros y cesión de datos": "cuándo la información puede compartirse con proveedores, empresas vinculadas u otros terceros",
    "Transferencias internacionales": "cómo puede trasladarse información entre países",
    "Conservación y eliminación": "durante cuánto tiempo se conserva la información y cuándo puede eliminarse",
    "Publicidad y personalización": "cómo se usan datos para publicidad o personalización",
    "Propiedad y licencias": "los permisos, licencias o derechos relacionados con contenido y propiedad intelectual",
    "Arbitraje y disputas": "cómo se gestionan disputas, arbitrajes o reclamaciones colectivas",
    "Jurisdicción y ley aplicable": "qué legislación o tribunales pueden aplicarse",
    "Precios, pagos y suscripciones": "precios, cobros, renovaciones o suscripciones",
    "Derechos y control del usuario": "los derechos y opciones de control disponibles para las personas usuarias",
    "Seguridad": "medidas o compromisos relacionados con la seguridad de la información",
    "Cumplimiento y auditoría": "obligaciones de cumplimiento, auditorías o certificaciones",
    "Cuenta y acceso al servicio": "las reglas sobre cuentas, acceso, suspensión o finalización del servicio"
}


def clean_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def classify_categories(added_lines, removed_lines):
    text = " ".join(added_lines + removed_lines).lower()
    return [category for category, patterns in CATEGORY_RULES.items() if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)]


def classify_relevance(categories, added_count, removed_count):
    category_set = set(categories)
    if category_set & HIGH_IMPACT or len(categories) >= 3:
        return "Alta"
    if category_set & MEDIUM_IMPACT or (added_count + removed_count) >= 20:
        return "Media"
    return "Baja"


def build_plain_summary(categories, added_count, removed_count):
    total = added_count + removed_count
    if not categories:
        return f"Se han detectado {total} líneas modificadas, pero el sistema no ha podido asociarlas con una materia concreta. Conviene revisar el cambio exacto para conocer su alcance."
    descriptions = [PLAIN_LANGUAGE[c] for c in categories[:3]]
    if len(descriptions) == 1:
        subject = descriptions[0]
    elif len(descriptions) == 2:
        subject = f"{descriptions[0]} y {descriptions[1]}"
    else:
        subject = f"{descriptions[0]}, {descriptions[1]} y {descriptions[2]}"
    extra = " También se han detectado cambios en otras materias." if len(categories) > 3 else ""
    return f"Este documento ha cambiado en aspectos relacionados con {subject}.{extra} El resumen es automático; el texto exacto puede consultarse debajo."


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

    headers = {"User-Agent": "PolicyChangeObservatory/3.0 (+https://github.com/progeekts/cambios-en-terminos-y-condiciones)"}
    now = datetime.now(timezone.utc)
    current_date = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    status = {"schema_version": SCHEMA_VERSION, "classifier_version": CLASSIFIER_VERSION, "last_check": current_date, "targets": len(targets), "ok": 0, "errors": [], "changes": 0}

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
            status["errors"].append({"id": policy_id, "platform": target["platform"], "document_type": target.get("document_type", target.get("type", "Otro documento legal")), "error": str(exc)[:180]})
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
        categories = classify_categories(added_lines, removed_lines)
        relevance = classify_relevance(categories, len(added_lines), len(removed_lines))
        document_type = target.get("document_type", target.get("type", "Otro documento legal"))
        diff_log.insert(0, {
            "schema_version": SCHEMA_VERSION,
            "classifier_version": CLASSIFIER_VERSION,
            "id": policy_id,
            "platform": target["platform"],
            "type": document_type,
            "document_type": document_type,
            "url": target["url"],
            "date": current_date,
            "severity": relevance,
            "relevance": relevance,
            "categories": categories,
            "impacts": categories,
            "added_count": len(added_lines),
            "removed_count": len(removed_lines),
            "summary": build_plain_summary(categories, len(added_lines), len(removed_lines)),
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
