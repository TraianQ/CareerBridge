"""Genereaza un CV text simplu, care traduce skill-urile confirmate in
limbaj de angajator, pentru rolul tinta ales."""

import taxonomy


def generate_cv(name, years_experience, confirmed_skills, role_id):
    role = taxonomy.get_role_by_id(role_id)
    role_title_en = role["title_en"] if role else ""
    role_title_ro = role["title_ro"] if role else ""

    bullets = []
    for s in confirmed_skills:
        bullets.append(f"- {s['label_en']} -- demonstrat prin: \"{s['evidence']}\"")

    bullets_text = "\n".join(bullets) if bullets else "- (nicio competenta confirmata inca)"

    cv = f"""# {name}

## Obiectiv profesional
Candidat pentru rolul de **{role_title_ro} / {role_title_en}**, cu {years_experience} ani
de experienta practica in productie industriala.

## Competente relevante
{bullets_text}

## Experienta profesionala
{years_experience} ani in operatii de productie / fabrica, cu responsabilitati care includ
competentele de mai sus, dezvoltate direct la locul de munca.

## Nota
Acest CV traduce experienta practica in limbajul folosit de angajatori pentru rolul tinta.
Detaliile de angajator (nume companie, perioade exacte) trebuie completate de candidat.
"""
    return cv
