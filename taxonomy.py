"""
Mapeaza textul liber din interviu pe taxonomia de skill-uri definita in
fallback_data/roles_manufacturing.json. Incearca extractie via LLM; daca nu
e disponibil (sau da eroare), foloseste keyword-matching local -- asta
garanteaza ca demo-ul functioneaza fara nicio cheie API.
"""

import json
import os
import unicodedata

import llm_client

DATA_PATH = os.path.join(os.path.dirname(__file__), "fallback_data", "roles_manufacturing.json")

with open(DATA_PATH, "r", encoding="utf-8") as f:
    DATA = json.load(f)

SKILLS_TAXONOMY = DATA["skills_taxonomy"]
ROLES = DATA["roles"]


def _normalize(text):
    """Scoate diacritice si pune lowercase, ca matching-ul de keyword-uri sa fie robust."""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text


def extract_skills_from_transcript(full_transcript_text):
    """
    Returneaza o lista de dict-uri: {key, label_ro, label_en, evidence}
    Incearca intai LLM; daca esueaza, foloseste keyword matching.
    """
    if llm_client.LLM_AVAILABLE:
        try:
            result = llm_client.extract_skills_llm(full_transcript_text)
            found = []
            for item in result.get("skills", []):
                key = item.get("key")
                if key in SKILLS_TAXONOMY:
                    found.append({
                        "key": key,
                        "label_ro": SKILLS_TAXONOMY[key]["label_ro"],
                        "label_en": SKILLS_TAXONOMY[key]["label_en"],
                        "evidence": item.get("evidence", ""),
                    })
            if found:
                return found
            # daca LLM nu a gasit nimic, cade pe fallback ca sa nu iasa gol
        except Exception:
            pass  # cade pe fallback de mai jos

    return _extract_skills_keywords(full_transcript_text)


def _extract_skills_keywords(full_transcript_text):
    normalized_text = _normalize(full_transcript_text)
    found = []
    for key, info in SKILLS_TAXONOMY.items():
        for kw in info["keywords_ro"]:
            if _normalize(kw) in normalized_text:
                found.append({
                    "key": key,
                    "label_ro": info["label_ro"],
                    "label_en": info["label_en"],
                    "evidence": kw,
                })
                break  # un singur match e suficient per skill
    return found


def get_role_by_id(role_id):
    for r in ROLES:
        if r["id"] == role_id:
            return r
    return None


def compute_gap(confirmed_skill_keys, role_id):
    """Returneaza (skills_detinute, skills_lipsa) pentru un rol tinta."""
    role = get_role_by_id(role_id)
    if not role:
        return [], []
    required = role["required_skills"]
    have = [k for k in required if k in confirmed_skill_keys]
    missing = [k for k in required if k not in confirmed_skill_keys]
    return have, missing


def learn_search_url(skill_key):
    """Link real catre cautarea Microsoft Learn pentru termenul asociat skill-ului."""
    terms = SKILLS_TAXONOMY[skill_key]["learn_search_terms"]
    query = terms.replace(" ", "%20")
    return f"https://learn.microsoft.com/en-us/training/browse/?terms={query}"
