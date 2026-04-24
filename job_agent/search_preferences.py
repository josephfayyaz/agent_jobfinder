from __future__ import annotations

from collections import Counter
import json
import re


LANGUAGE_OPTIONS: list[dict[str, str]] = [
    {"code": "en", "name": "English"},
    {"code": "it", "name": "Italian"},
    {"code": "de", "name": "German"},
    {"code": "fr", "name": "French"},
    {"code": "es", "name": "Spanish"},
    {"code": "pt", "name": "Portuguese"},
    {"code": "nl", "name": "Dutch"},
]

_LANGUAGE_ALIASES = {
    "en": "English",
    "eng": "English",
    "english": "English",
    "inglese": "English",
    "it": "Italian",
    "ita": "Italian",
    "italian": "Italian",
    "italiano": "Italian",
    "de": "German",
    "ger": "German",
    "german": "German",
    "tedesco": "German",
    "deutsch": "German",
    "fr": "French",
    "french": "French",
    "francese": "French",
    "francais": "French",
    "es": "Spanish",
    "spanish": "Spanish",
    "spagnolo": "Spanish",
    "espanol": "Spanish",
    "pt": "Portuguese",
    "portuguese": "Portuguese",
    "portoghese": "Portuguese",
    "pt-br": "Portuguese",
    "nl": "Dutch",
    "dutch": "Dutch",
    "nederlands": "Dutch",
    "olandese": "Dutch",
}

LEVEL_OPTIONS: list[dict[str, str]] = [
    {"value": "basic", "label": "Basic"},
    {"value": "working", "label": "Working"},
    {"value": "professional", "label": "Professional"},
    {"value": "fluent", "label": "Fluent"},
]

_LEVEL_ALIASES = {
    "a1": "basic",
    "a2": "basic",
    "basic": "basic",
    "elementary": "basic",
    "limited": "basic",
    "limited_working": "basic",
    "b1": "working",
    "intermediate": "working",
    "working": "working",
    "conversational": "working",
    "professional_working": "professional",
    "b2": "professional",
    "upper_intermediate": "professional",
    "professional": "professional",
    "c1": "fluent",
    "advanced": "fluent",
    "fluent": "fluent",
    "full_professional": "fluent",
    "c2": "fluent",
    "native": "fluent",
    "native_or_bilingual": "fluent",
    "bilingual": "fluent",
}

_LEVEL_RANK = {
    "basic": 1,
    "working": 2,
    "professional": 3,
    "fluent": 4,
}

_JOB_LANGUAGE_HINTS = {
    "English": {
        "code": "en",
        "stopwords": {"the", "and", "with", "you", "your", "will", "experience", "requirements"},
        "phrases": {"you will", "we are looking", "required skills", "about the role"},
    },
    "Italian": {
        "code": "it",
        "stopwords": {"con", "per", "esperienza", "requisiti", "responsabilita", "lavoro", "candidato", "sarai"},
        "phrases": {"siamo alla ricerca", "requisiti richiesti", "sede di lavoro", "lingua italiana"},
    },
    "German": {
        "code": "de",
        "stopwords": {"und", "mit", "der", "die", "das", "erfahrung", "anforderungen", "rolle"},
        "phrases": {"wir suchen", "deine aufgaben", "dein profil", "gute deutschkenntnisse"},
    },
    "French": {
        "code": "fr",
        "stopwords": {"avec", "pour", "vous", "experience", "profil", "poste", "competences", "requis"},
        "phrases": {"nous recherchons", "votre profil", "vos missions", "langue francaise"},
    },
    "Spanish": {
        "code": "es",
        "stopwords": {"con", "para", "experiencia", "requisitos", "puesto", "perfil", "idioma", "equipo"},
        "phrases": {"estamos buscando", "tu perfil", "requisitos del puesto", "idioma espanol"},
    },
    "Portuguese": {
        "code": "pt",
        "stopwords": {"com", "para", "experiencia", "requisitos", "perfil", "vaga", "idioma", "equipe"},
        "phrases": {"estamos procurando", "seu perfil", "descricao da vaga", "idioma portugues"},
    },
    "Dutch": {
        "code": "nl",
        "stopwords": {"met", "voor", "ervaring", "vereisten", "functie", "profiel", "taal", "team"},
        "phrases": {"wij zoeken", "jouw profiel", "functie eisen", "nederlandse taal"},
    },
}


def normalize_language_name(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    normalized = raw.casefold().replace("_", " ").replace("-", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return _LANGUAGE_ALIASES.get(normalized, raw.title())


def normalize_language_level(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "professional"
    normalized = raw.casefold().replace("-", "_").replace(" ", "_")
    return _LEVEL_ALIASES.get(normalized, "professional")


def language_level_rank(value: object) -> int:
    return _LEVEL_RANK[normalize_language_level(value)]


def language_level_label(value: object) -> str:
    normalized = normalize_language_level(value)
    return normalized.capitalize()


def normalize_country_list(value: object) -> list[str]:
    if value in (None, ""):
        return ["Italy"]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ["Italy"]
        try:
            parsed = json.loads(stripped)
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = re.split(r"[\n,;]+", stripped)
        value = parsed
    if not isinstance(value, list):
        return ["Italy"]

    countries: list[str] = []
    for item in value:
        country = str(item or "").strip()
        if not country:
            continue
        if any(existing.casefold() == country.casefold() for existing in countries):
            continue
        countries.append(country)
    return countries or ["Italy"]


def normalize_job_language_preferences(value: object) -> list[dict[str, str]]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = []
            for line in stripped.splitlines():
                text = line.strip()
                if not text:
                    continue
                if ":" in text:
                    name, level = text.split(":", 1)
                    parsed.append({"name": name.strip(), "level": level.strip()})
                else:
                    parsed.append({"name": text, "level": "professional"})
        value = parsed

    if not isinstance(value, list):
        return []

    normalized_rows: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            name = normalize_language_name(item.get("name") or item.get("language") or item.get("code"))
            level = normalize_language_level(item.get("level"))
        else:
            name = normalize_language_name(item)
            level = "professional"
        if not name:
            continue
        key = name.casefold()
        if any(existing["name"].casefold() == key for existing in normalized_rows):
            continue
        normalized_rows.append(
            {
                "name": name,
                "level": level,
                "label": language_level_label(level),
                "code": _language_code(name),
            }
        )
    return normalized_rows


def allowed_job_language_names(preferences: object) -> set[str]:
    return {row["name"] for row in normalize_job_language_preferences(preferences)}


def detect_job_languages(text: str) -> list[dict[str, object]]:
    sample = " ".join((text or "").split())[:1800].casefold()
    if not sample:
        return []

    words = re.findall(r"[a-zA-ZÀ-ÿ']+", sample)
    counts = Counter(words)
    detected: list[dict[str, object]] = []
    for language, config in _JOB_LANGUAGE_HINTS.items():
        stopword_score = sum(counts.get(token, 0) for token in config["stopwords"])
        phrase_score = sum(2 for phrase in config["phrases"] if phrase in sample)
        score = stopword_score + phrase_score
        if score < 4:
            continue
        detected.append(
            {
                "name": language,
                "code": config["code"],
                "score": score,
            }
        )
    detected.sort(key=lambda item: int(item["score"]), reverse=True)
    return detected[:3]


def job_matches_language_preferences(text: str, preferences: object) -> bool:
    allowed = allowed_job_language_names(preferences)
    if not allowed:
        return True
    detected = detect_job_languages(text)
    if not detected:
        return True
    return any(item["name"] in allowed for item in detected)


def profile_language_suggestions(value: object) -> list[dict[str, object]]:
    suggestions: list[dict[str, object]] = []
    for row in normalize_job_language_preferences(value):
        rank = language_level_rank(row["level"])
        suggestions.append(
            {
                **row,
                "auto_selected": rank >= _LEVEL_RANK["professional"],
            }
        )
    return suggestions


def fallback_job_language_preferences(profile_languages: object, current: object) -> list[dict[str, str]]:
    existing = normalize_job_language_preferences(current)
    if existing:
        return existing
    suggested = [row for row in profile_language_suggestions(profile_languages) if row["auto_selected"]]
    if suggested:
        return [
            {"name": row["name"], "level": row["level"], "label": row["label"], "code": row["code"]}
            for row in suggested
        ]
    return [{"name": "English", "level": "professional", "label": "Professional", "code": "en"}]


def search_preference_recommendations(
    session,
    *,
    candidate_id: str | None,
    current_roles: object = None,
    current_countries: object = None,
    current_languages: object = None,
) -> dict[str, object]:
    from job_agent.models import Candidate, JobSource, MatchProfile

    candidate = session.get(Candidate, candidate_id) if candidate_id else None
    match_profile = (
        session.query(MatchProfile).filter(MatchProfile.candidate_id == candidate_id).first()
        if candidate_id
        else None
    )

    detected_roles = []
    if match_profile and isinstance(match_profile.target_roles, list):
        detected_roles = [str(role).strip() for role in match_profile.target_roles if str(role).strip()]

    country_source = current_countries
    if not country_source and match_profile:
        country_source = (match_profile.location_preferences or {}).get("preferred_countries")
    countries = normalize_country_list(country_source)
    roles = normalize_role_list(current_roles or detected_roles)
    profile_languages = list(candidate.spoken_languages or []) if candidate and candidate.spoken_languages else []
    selected_languages = fallback_job_language_preferences(profile_languages, current_languages)

    job_sources = session.query(JobSource).filter(JobSource.active.is_(True)).order_by(JobSource.priority.asc()).all()
    recommended_sources = []
    role_families = _infer_role_families(roles)
    country_set = {country.casefold() for country in countries}

    for source in job_sources:
        score = 0
        target_regions = {str(region).casefold() for region in (source.target_regions or [])}
        if country_set & target_regions:
            score += 3
        elif {"italy", "eu"} & target_regions:
            score += 2
        source_families = {str(family).casefold() for family in (source.role_families or [])}
        if role_families & source_families:
            score += 2
        if "research" in role_families and source.slug == "euraxess":
            score += 3
        if source.slug in {"greenhouse", "lever", "ashby"}:
            score += 1
        if source.slug == "linkedin-manual":
            score += 1
        if score <= 0:
            continue
        recommended_sources.append(
            {
                "slug": source.slug,
                "name": source.name,
                "score": score,
                "why": _source_reason(source.slug),
            }
        )

    recommended_sources.sort(key=lambda item: (-int(item["score"]), item["name"]))

    return {
        "countries": countries,
        "suggested_roles": roles[:3],
        "detected_languages": profile_language_suggestions(profile_languages),
        "selected_languages": selected_languages,
        "recommended_sources": recommended_sources[:4],
        "language_options": LANGUAGE_OPTIONS,
        "level_options": LEVEL_OPTIONS,
    }


def normalize_role_list(value: object) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        parts = re.split(r"[\n,;]+", value)
    elif isinstance(value, list):
        parts = value
    else:
        return []
    roles: list[str] = []
    for item in parts:
        role = str(item or "").strip()
        if not role:
            continue
        if any(existing.casefold() == role.casefold() for existing in roles):
            continue
        roles.append(role)
    return roles


def primary_search_country(countries: object, fallback: str = "Italy") -> str:
    normalized = normalize_country_list(countries)
    return normalized[0] if normalized else fallback


def _language_code(name: str) -> str:
    for option in LANGUAGE_OPTIONS:
        if option["name"].casefold() == name.casefold():
            return option["code"]
    return name[:2].lower()


def _infer_role_families(roles: list[str]) -> set[str]:
    joined = " ".join(roles).casefold()
    families: set[str] = set()
    if any(token in joined for token in ("ml", "machine learning", "ai", "llm", "nlp")):
        families.add("ai")
    if any(token in joined for token in ("data", "analytics", "bi", "analyst", "dbt")):
        families.add("analytics")
        families.add("data")
    if any(token in joined for token in ("cloud", "platform", "mlops", "kubernetes", "devops")):
        families.add("cloud")
    if any(token in joined for token in ("research", "thesis", "phd", "internship", "traineeship")):
        families.add("research")
    return families or {"data"}


def _source_reason(slug: str) -> str:
    if slug == "eures":
        return "Best for cross-border EU roles and early-career mobility."
    if slug == "euraxess":
        return "Strong for research, thesis, and university-linked placements."
    if slug == "linkedin-manual":
        return "High-signal market discovery; keep manual because LinkedIn automation is restricted."
    if slug in {"greenhouse", "lever", "ashby"}:
        return "Clean ATS pages with direct apply URLs and less noise than general boards."
    return "Aligned with your target countries and role family."
