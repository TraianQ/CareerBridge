"""Genereaza un plan text de 12 saptamani, distribuind skill-urile lipsa pe
parcursul saptamanilor, cu link-uri reale de cautare pentru cursuri pe mai
multe platforme (Microsoft Learn, Udemy, Coursera) pentru fiecare."""

import taxonomy


def generate_12_week_plan(missing_skill_keys, role_title_ro):
    if not missing_skill_keys:
        weeks_body = (
            "Ai deja competentele principale cerute de acest rol. "
            "Cele 12 saptamani se concentreaza pe pregatirea aplicatiei si a interviurilor."
        )
        return f"# Plan de 12 saptamani -> {role_title_ro}\n\n{weeks_body}\n"

    # Distribuim skill-urile lipsa pe saptamanile 1-9, rezervam 10-12 pentru CV/aplicare/interviu
    n_skills = len(missing_skill_keys)
    weeks_per_skill = max(1, 9 // n_skills)

    lines = [f"# Plan de 12 saptamani -> {role_title_ro}\n"]
    week_num = 1
    for skill_key in missing_skill_keys:
        label = taxonomy.SKILLS_TAXONOMY[skill_key]["label_ro"]
        course_links = taxonomy.course_search_urls(skill_key)
        start_week = week_num
        end_week = min(week_num + weeks_per_skill - 1, 9)
        lines.append(f"**Saptamana {start_week}-{end_week}: {label}**")
        for platform_label, url in course_links:
            lines.append(f"- Cursuri {platform_label}: {url}")
        lines.append(
            "- Exercitiu practic: scrie 3 exemple din experienta ta care arata deja parti din acest skill.\n"
        )
        week_num = end_week + 1
        if week_num > 9:
            break

    lines.append(
        "**Saptamana 10: Actualizare CV**\n"
        "- Foloseste CV-ul generat mai jos ca baza si adapteaza-l pentru fiecare aplicatie.\n"
    )
    lines.append(
        "**Saptamana 11: Aplicare tintita**\n"
        "- Aplica la minimum 5 pozitii pentru rolul ales, folosind vocabularul nou.\n"
    )
    lines.append(
        "**Saptamana 12: Pregatire interviu**\n"
        "- Exerseaza sa povestesti exemplele concrete din saptamanile anterioare, in format STAR "
        "(Situatie, Sarcina, Actiune, Rezultat).\n"
    )
    lines.append(
        "\n_Nota: acest plan arata rolurile cu cerere in zona ta si un traseu posibil de pregatire, "
        "dar nu garanteaza angajarea. Validarea finala a competentelor ramane la angajator._"
    )
    return "\n".join(lines)
