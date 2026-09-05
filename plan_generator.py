"""Genereaza un plan text de 12 saptamani, distribuind skill-urile lipsa pe
parcursul saptamanilor, cu link-uri reale de cautare pentru cursuri pe mai
multe platforme (Microsoft Learn, Udemy, Coursera) pentru fiecare."""

import taxonomy

FINAL_WEEKS = [
    ("Saptamana 10: Actualizare profil profesional",
     "Rescrie-ti experienta folosind vocabularul competentelor confirmate mai sus."),
    ("Saptamana 11: Aplicare tintita",
     "Aplica la minimum 5 pozitii pentru rolul ales, folosind vocabularul nou."),
    ("Saptamana 12: Pregatire interviu",
     "Exerseaza sa povestesti exemplele concrete din saptamanile anterioare, in format STAR "
     "(Situatie, Sarcina, Actiune, Rezultat)."),
]


def build_plan_sections(missing_skill_keys):
    """Distribuie skill-urile lipsa pe saptamanile 1-9 si returneaza o lista de
    dict-uri {start_week, end_week, label, course_links}, folosita atat pentru
    randarea in UI (butoane), cat si pentru exportul text."""
    n_skills = len(missing_skill_keys)
    weeks_per_skill = max(1, 9 // n_skills)

    sections = []
    week_num = 1
    for skill_key in missing_skill_keys:
        start_week = week_num
        end_week = min(week_num + weeks_per_skill - 1, 9)
        sections.append({
            "start_week": start_week,
            "end_week": end_week,
            "label": taxonomy.SKILLS_TAXONOMY[skill_key]["label_ro"],
            "course_links": taxonomy.course_search_urls(skill_key),
        })
        week_num = end_week + 1
        if week_num > 9:
            break
    return sections


def generate_12_week_plan(missing_skill_keys, role_title_ro):
    if not missing_skill_keys:
        weeks_body = (
            "Ai deja competentele principale cerute de acest rol. "
            "Cele 12 saptamani se concentreaza pe pregatirea aplicatiei si a interviurilor."
        )
        return f"# Plan de 12 saptamani -> {role_title_ro}\n\n{weeks_body}\n"

    lines = [f"# Plan de 12 saptamani -> {role_title_ro}\n"]
    for s in build_plan_sections(missing_skill_keys):
        lines.append(f"**Saptamana {s['start_week']}-{s['end_week']}: {s['label']}**")
        for platform_label, url in s["course_links"]:
            lines.append(f"- [Cursuri {platform_label}]({url})")
        lines.append(
            "- Exercitiu practic: scrie 3 exemple din experienta ta care arata deja parti din acest skill.\n"
        )

    for title, body in FINAL_WEEKS:
        lines.append(f"**{title}**\n- {body}\n")

    lines.append(
        "\n_Nota: acest plan arata rolurile cu cerere in zona ta si un traseu posibil de pregatire, "
        "dar nu garanteaza angajarea. Validarea finala a competentelor ramane la angajator._"
    )
    return "\n".join(lines)
