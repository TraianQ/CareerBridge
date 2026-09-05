"""
Simuleaza interviul din app.py, dar in locul unui om care raspunde manual la
chat, raspunsurile sunt generate de un "actor" AI care interpreteaza persoana
descrisa intr-un fisier de profil (implicit: Profiles/maria.txt).

Util pentru testare rapida a intregului flux (intrebari -> extractie skill-uri
-> gap -> plan 12 saptamani -> CV), fara sa fie nevoie sa scrii manual
raspunsuri in interfata Streamlit.

Ruleaza cu:
    python simulate_persona_interview.py
    python simulate_persona_interview.py --profile Profiles/dumitru.txt --role shift_coordinator
"""

import argparse
import os
import re

import llm_client
import taxonomy
import plan_generator
import cv_writer

FALLBACK_QUESTIONS = [
    "Hai să vorbim despre o zi obișnuită de muncă. Ce faci, pas cu pas, când ajungi la fabrică?",
    "Poți să-mi dai un exemplu concret -- ce anume verifici sau ce decizii iei în timpul zilei?",
    "Cum arată o zi în care apare o problemă sau ceva nu merge bine? Ce faci mai exact?",
    "Lucrezi și cu alți colegi sau alte echipe? Cum comunici cu ei în timpul turei?",
    "Ai instruit vreodată pe cineva nou la job, sau ai fost responsabil de alți oameni la un moment dat?",
]

# Raspunsuri "offline" folosite cand nu exista o cheie LLM configurata --
# scrise pe baza descrierii Mariei din maria.txt, ca demo-ul sa mearga oricum.
FALLBACK_ANSWERS = [
    "Ajung la fabrică, îmi iau echipamentul de protecție și mă duc direct pe linie. "
    "Verific piesele care ies de pe bandă, una câte una, și semnez fișele de control.",
    "Mă uit dacă piesa are vreun defect vizibil sau nu se încadrează la dimensiuni -- "
    "dacă găsesc o rebut, o pun deoparte și decid dacă opresc linia sau doar marchez lotul.",
    "Dacă apare o problemă, opresc banda, chem șeful de tură și completez un raport de incident "
    "ca să rămână scris ce s-a întâmplat și ce am făcut.",
    "Da, vorbesc și cu cei de la mentenanță când utilajul face probleme, și cu șeful de tură "
    "în fiecare zi ca să-i spun ce am găsit.",
    "Am arătat de multe ori colegilor noi cum se verifică piesele corect, mai ales celor "
    "care abia veneau pe linie.",
]


def load_profile_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_persona_answer(profile_text, history_for_llm):
    """Foloseste LLM daca e disponibil, altfel un raspuns fallback scris manual."""
    idx = len(history_for_llm) // 2  # cate intrebari s-au pus deja
    if llm_client.LLM_AVAILABLE:
        try:
            return llm_client.answer_as_persona(profile_text, history_for_llm)
        except Exception:
            pass
    return FALLBACK_ANSWERS[min(idx, len(FALLBACK_ANSWERS) - 1)]


def get_next_question(history_for_llm, question_index):
    if llm_client.LLM_AVAILABLE:
        try:
            return llm_client.generate_followup_question(history_for_llm)
        except Exception:
            pass
    return FALLBACK_QUESTIONS[question_index]


def run_interview(profile_text, num_questions):
    history_for_llm = []
    interview_qas = []

    question = FALLBACK_QUESTIONS[0]
    for i in range(num_questions):
        print(f"\n🤖 Consilier: {question}")
        history_for_llm.append({"role": "assistant", "content": question})

        answer = get_persona_answer(profile_text, history_for_llm)
        print(f"🙋 Persoana : {answer}")
        history_for_llm.append({"role": "user", "content": answer})

        interview_qas.append((question, answer))

        if i < num_questions - 1:
            question = get_next_question(history_for_llm, i + 1)

    return interview_qas


def transcript_text(interview_qas):
    return "\n".join(f"Întrebare: {q}\nRăspuns: {a}" for q, a in interview_qas)


def pick_best_role(confirmed_skill_keys):
    """Alege rolul cu cele mai putine skill-uri lipsa (cel mai apropiat de profil)."""
    best_role, best_missing = None, None
    for role in taxonomy.ROLES:
        _, missing = taxonomy.compute_gap(confirmed_skill_keys, role["id"])
        if best_missing is None or len(missing) < len(best_missing):
            best_role, best_missing = role, missing
    return best_role


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=os.path.join("Profiles", "maria.txt"), help="Fisier text cu profilul persoanei")
    parser.add_argument("--role", default=None, help="ID de rol tinta (vezi fallback_data/roles_manufacturing.json)")
    parser.add_argument("--name", default="Maria", help="Numele afisat in CV")
    parser.add_argument("--years", default="22", help="Anii de experienta afisati in CV")
    args = parser.parse_args()

    profile_path = args.profile if os.path.isabs(args.profile) else os.path.join(
        os.path.dirname(__file__), args.profile
    )
    profile_text = load_profile_text(profile_path)

    mode = "LLM activ" if llm_client.LLM_AVAILABLE else "mod offline (fallback local)"
    print(f"=== Simulare interviu pentru profilul din '{args.profile}' ({mode}) ===")

    interview_qas = run_interview(profile_text, len(FALLBACK_QUESTIONS))

    print("\n=== Extractie competente din transcript ===")
    skills = taxonomy.extract_skills_from_transcript(transcript_text(interview_qas))
    if skills:
        for s in skills:
            print(f"- {s['label_ro']} (dovada: \"{s['evidence']}\")")
    else:
        print("(nicio competenta identificata)")
    confirmed_skill_keys = [s["key"] for s in skills]

    role = taxonomy.get_role_by_id(args.role) if args.role else pick_best_role(confirmed_skill_keys)
    if role is None:
        role = taxonomy.ROLES[0]

    have, missing = taxonomy.compute_gap(confirmed_skill_keys, role["id"])
    print(f"\n=== Rol țintă ales: {role['title_ro']} ({role['title_en']}) ===")
    print("Are deja: " + (", ".join(have) if have else "-"))
    print("Îi lipsește: " + (", ".join(missing) if missing else "-"))

    plan_text = plan_generator.generate_12_week_plan(missing, role["title_ro"])
    cv_text = cv_writer.generate_cv(args.name, args.years, skills, role["id"])

    print("\n" + "=" * 60)
    print(plan_text)
    print("=" * 60)
    print(cv_text)


if __name__ == "__main__":
    main()
