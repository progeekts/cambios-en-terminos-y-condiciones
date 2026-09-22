import os
import json
import difflib
import re
import hashlib
import time
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape as xml_escape
import requests
from bs4 import BeautifulSoup

TRACKED_DIR = "tracked_policies"
DATA_FILE = "docs/diffs.json"
STATUS_FILE = "docs/status.json"
TARGETS_FILE = "scripts/targets.json"
RSS_FILE = "docs/feed.xml"
ATOM_FILE = "docs/atom.xml"
MAX_LOG = 300
MAX_DIFF_LINES = 220
SCHEMA_VERSION = 5
CLASSIFIER_VERSION = 3
MIN_CONTENT_LENGTH = 500
MAX_SIZE_RATIO = 4.0
MIN_SIZE_RATIO = 0.35
RETRIES = 3
SITE_URL = "https://progeekts.github.io/cambios-en-terminos-y-condiciones/"

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
EFFECTIVE_DATE_PATTERNS = [r"(?:A partir del|Vigente desde|En vigor desde|Effective date|Effective|Last updated|Última actualización)[: ]+([^\\n|]{6,80})"]


def clean_html(html_content, selector=None):
    soup = BeautifulSoup(html_content, "html.parser")
    if selector:
        selected = soup.select_one(selector)
        if selected is None:
            raise ValueError(f"selector no encontrado: {selector}")
        soup = selected
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form", "aside"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_effective_date(text):
    head = canonical_text(text)[:5000]
    for pattern in EFFECTIVE_DATE_PATTERNS:
        match = re.search(pattern, head, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .|")
    return None


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
    subject = descriptions[0] if len(descriptions) == 1 else (f"{descriptions[0]} y {descriptions[1]}" if len(descriptions) == 2 else f"{descriptions[0]}, {descriptions[1]} y {descriptions[2]}")
    extra = " También se han detectado cambios en otras materias." if len(categories) > 3 else ""
    return f"Este documento ha cambiado en aspectos relacionados con {subject}.{extra} El resumen es automático; el texto exacto puede consultarse debajo."


def canonical_text(text):
    lines = []
    for line in text.splitlines():
        line = " ".join(line.split()).strip()
        if not line:
            continue
        if "Trace Id:" in line:
            continue
        lines.append(line)
    return "\n".join(lines)


def content_hash(text):
    return hashlib.sha256(canonical_text(text).encode("utf-8")).hexdigest()


def semantic_fingerprint(text):
    normalized = sorted(x.casefold() for x in canonical_text(text).splitlines() if x)
    return hashlib.sha256("\n".join(normalized).encode("utf-8")).hexdigest()


def diff_fingerprint(policy_id, added_lines, removed_lines):
    payload = {
        "id": policy_id,
        "added": sorted(" ".join(x.split()).casefold() for x in added_lines if x.strip()),
        "removed": sorted(" ".join(x.split()).casefold() for x in removed_lines if x.strip()),
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def historical_fingerprints(entries):
    result = set()
    for e in entries:
        fp = e.get("diff_fingerprint")
        if fp:
            result.add(fp)
            continue
        raw = e.get("raw_diff", "")
        added = [x[1:] for x in raw.splitlines() if x.startswith("+") and not x.startswith("+++")]
        removed = [x[1:] for x in raw.splitlines() if x.startswith("-") and not x.startswith("---")]
        if added or removed:
            result.add(diff_fingerprint(e.get("id", "change"), added, removed))
    return result


def change_id(policy_id, date, diff_text):
    digest = hashlib.sha256(f"{policy_id}|{date}|{diff_text}".encode("utf-8")).hexdigest()[:12]
    return f"{policy_id}-{digest}"


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def ensure_change_ids(entries):
    for entry in entries:
        if not entry.get("change_id"):
            entry["change_id"] = change_id(entry.get("id", "change"), entry.get("date", ""), entry.get("raw_diff", ""))
        entry["permalink"] = f"{SITE_URL}#change-{entry['change_id']}"


def write_feeds(entries):
    ensure_change_ids(entries)
    items = entries[:50]
    rss_items = []
    atom_items = []
    for e in items:
        title = f"{e.get('platform', 'Servicio')} — {e.get('document_type') or e.get('type', 'Documento')}"
        summary = e.get("summary", "Cambio detectado en un documento oficial.")
        link = e["permalink"]
        dt = parse_date(e.get("date"))
        rss_items.append(f"<item><title>{xml_escape(title)}</title><link>{xml_escape(link)}</link><guid isPermaLink=\"true\">{xml_escape(link)}</guid><pubDate>{format_datetime(dt)}</pubDate><description>{xml_escape(summary)}</description></item>")
        atom_items.append(f"<entry><title>{xml_escape(title)}</title><id>{xml_escape(link)}</id><link href=\"{xml_escape(link)}\"/><updated>{dt.isoformat()}</updated><summary>{xml_escape(summary)}</summary></entry>")
    rss = f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Observatorio de Cambios</title><link>{SITE_URL}</link><description>Cambios detectados en términos, privacidad y otras condiciones de servicios digitales.</description>{"".join(rss_items)}</channel></rss>'
    updated = parse_date(items[0].get("date")) if items else datetime.now(timezone.utc)
    atom = f'<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Observatorio de Cambios</title><id>{SITE_URL}</id><link href="{SITE_URL}"/><link rel="self" href="{SITE_URL}atom.xml"/><updated>{updated.isoformat()}</updated>{"".join(atom_items)}</feed>'
    with open(RSS_FILE, "w", encoding="utf-8") as f:
        f.write(rss)
    with open(ATOM_FILE, "w", encoding="utf-8") as f:
        f.write(atom)


def validate_response(response, text, old_text=None):
    ctype = response.headers.get("content-type", "").lower()
    if "text/html" not in ctype and "text/plain" not in ctype and "application/xhtml" not in ctype:
        raise ValueError(f"tipo de contenido inesperado: {ctype or 'desconocido'}")
    if len(text) < MIN_CONTENT_LENGTH:
        raise ValueError("contenido extraído demasiado corto")
    sample = text[:6000].lower()
    for pattern in BLOCK_PATTERNS:
        if re.search(pattern, sample, re.IGNORECASE):
            raise ValueError(f"posible página de bloqueo detectada ({pattern})")
    if old_text and len(old_text) >= MIN_CONTENT_LENGTH:
        ratio = len(text) / len(old_text)
        if ratio < MIN_SIZE_RATIO or ratio > MAX_SIZE_RATIO:
            raise ValueError(f"cambio de tamaño sospechoso ({ratio:.2f}x); snapshot no actualizado")


def fetch_document(session, target):
    last_error = None
    for attempt in range(RETRIES):
        try:
            response = session.get(target["url"], timeout=30, allow_redirects=True)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt < RETRIES - 1:
                time.sleep(2 ** attempt)
    raise last_error


def main():
    os.makedirs(TRACKED_DIR, exist_ok=True)
    os.makedirs("docs", exist_ok=True)
    with open(TARGETS_FILE, "r", encoding="utf-8") as f:
        targets = [t for t in json.load(f) if t.get("enabled", True)]
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            diff_log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        diff_log = []
    ensure_change_ids(diff_log)
    seen_fingerprints = historical_fingerprints(diff_log)

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; PolicyChangeObservatory/5.0; +https://github.com/progeekts/cambios-en-terminos-y-condiciones)", "Accept": "text/html,application/xhtml+xml;q=0.9,text/plain;q=0.8,*/*;q=0.5", "Accept-Language": "es-ES,es;q=0.8,en;q=0.6"})
    now = datetime.now(timezone.utc)
    current_date = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    status = {"schema_version": SCHEMA_VERSION, "classifier_version": CLASSIFIER_VERSION, "last_check": current_date, "targets": len(targets), "ok": 0, "errors": [], "changes": 0, "sources": []}

    for target in targets:
        policy_id = target["id"]
        document_type = target.get("document_type", target.get("type", "Otro documento legal"))
        filepath = os.path.join(TRACKED_DIR, f"{policy_id}.txt")
        source_status = {"id": policy_id, "platform": target["platform"], "document_type": document_type, "url": target["url"], "state": "error", "changed": False, "checked_at": current_date}
        old_text = ""
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                old_text = f.read()
        try:
            res = fetch_document(session, target)
            new_text = clean_html(res.text, target.get("selector"))
            validate_response(res, new_text, old_text or None)
            source_status.update({"state": "ok", "http_status": res.status_code, "final_url": res.url, "content_length": len(new_text), "content_hash": content_hash(new_text), "effective_date": extract_effective_date(new_text)})
            status["ok"] += 1
        except Exception as exc:
            message = str(exc)[:220]
            source_status["error"] = message
            status["errors"].append({"id": policy_id, "platform": target["platform"], "document_type": document_type, "error": message})
            status["sources"].append(source_status)
            continue
        if not old_text:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_text)
            source_status["state"] = "initialized"
            status["sources"].append(source_status)
            continue
        if content_hash(old_text) == source_status["content_hash"]:
            status["sources"].append(source_status)
            continue
        if semantic_fingerprint(old_text) == semantic_fingerprint(new_text):
            source_status["noise_ignored"] = "reordered_content"
            status["sources"].append(source_status)
            continue
        old_lines = canonical_text(old_text).splitlines(keepends=True)
        new_lines = canonical_text(new_text).splitlines(keepends=True)
        diff = list(difflib.unified_diff(old_lines, new_lines, fromfile="versión anterior", tofile="versión nueva", lineterm=""))
        if not diff:
            status["sources"].append(source_status)
            continue
        added_lines = [line[1:] for line in diff if line.startswith("+") and not line.startswith("+++")]
        removed_lines = [line[1:] for line in diff if line.startswith("-") and not line.startswith("---")]
        fingerprint = diff_fingerprint(policy_id, added_lines, removed_lines)
        if fingerprint in seen_fingerprints:
            source_status["noise_ignored"] = "duplicate_historical_change"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_text)
            status["sources"].append(source_status)
            continue
        categories = classify_categories(added_lines, removed_lines)
        relevance = classify_relevance(categories, len(added_lines), len(removed_lines))
        raw_diff = "".join(diff[:MAX_DIFF_LINES])
        cid = change_id(policy_id, current_date, raw_diff)
        diff_log.insert(0, {"schema_version": SCHEMA_VERSION, "classifier_version": CLASSIFIER_VERSION, "id": policy_id, "change_id": cid, "permalink": f"{SITE_URL}#change-{cid}", "platform": target["platform"], "type": document_type, "document_type": document_type, "url": target["url"], "date": current_date, "severity": relevance, "relevance": relevance, "categories": categories, "impacts": categories, "added_count": len(added_lines), "removed_count": len(removed_lines), "summary": build_plain_summary(categories, len(added_lines), len(removed_lines)), "raw_diff": raw_diff, "diff_fingerprint": fingerprint})
        seen_fingerprints.add(fingerprint)
        status["changes"] += 1
        source_status.update({"changed": True, "change_id": cid, "relevance": relevance, "categories": categories, "added_count": len(added_lines), "removed_count": len(removed_lines)})
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_text)
        status["sources"].append(source_status)

    diff_log = diff_log[:MAX_LOG]
    ensure_change_ids(diff_log)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(diff_log, f, indent=2, ensure_ascii=False)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
    write_feeds(diff_log)


if __name__ == "__main__":
    main()
