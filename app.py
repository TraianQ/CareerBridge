"""
Career Bridge -- MVP demo
Chat conversational care traduce experienta de munca in skill-uri numite,
mapeaza pe roluri tinta si genereaza un plan de 12 saptamani + CV rescris.

Ruleaza cu: streamlit run app.py
"""

import re

import streamlit as st

import llm_client
import taxonomy
import plan_generator
import cv_writer

st.set_page_config(page_title="Career Bridge", page_icon="🌉", layout="centered")

FALLBACK_QUESTIONS = [
    "Hai să vorbim despre o zi obișnuită de muncă. Ce faci, pas cu pas, când ajungi la fabrică?",
    "Poți să-mi dai un exemplu concret -- ce anume verifici sau ce decizii iei în timpul zilei?",
    "Cum arată o zi în care apare o problemă sau ceva nu merge bine? Ce faci mai exact?",
    "Lucrezi și cu alți colegi sau alte echipe? Cum comunici cu ei în timpul turei?",
    "Ai instruit vreodată pe cineva nou la job, sau ai fost responsabil de alți oameni la un moment dat?",
]

TOTAL_QUESTIONS = len(FALLBACK_QUESTIONS)


# ---------------------------------------------------------------------------
# Initializare state
# ---------------------------------------------------------------------------

def init_state():
    if "stage" not in st.session_state:
        st.session_state.stage = "name"
        st.session_state.messages = []
        st.session_state.name = ""
        st.session_state.years_experience = ""
        st.session_state.question_index = 0
        st.session_state.interview_qas = []  # list of (question, answer)
        st.session_state.extracted_skills = []
        st.session_state.confirmed_skill_keys = []
        st.session_state.selected_role_id = None

        st.session_state.messages.append({
            "role": "assistant",
            "content": "Bună! Sunt aici să te ajut să vezi, în cuvinte clare, ce știi deja să faci. "
                       "Nu te întreb despre diplome -- te întreb despre munca ta de zi cu zi.\n\n"
                       "Cum te numești?",
        })


def add_message(role, content):
    st.session_state.messages.append({"role": role, "content": content})


def full_transcript_text():
    return "\n".join(f"Întrebare: {q}\nRăspuns: {a}" for q, a in st.session_state.interview_qas)


def next_interview_question(history_for_llm):
    """Alege urmatoarea intrebare: LLM adaptiv daca e disponibil, altfel lista fixa."""
    idx = st.session_state.question_index
    if llm_client.LLM_AVAILABLE:
        try:
            return llm_client.generate_followup_question(history_for_llm)
        except Exception:
            pass
    return FALLBACK_QUESTIONS[idx]


# ---------------------------------------------------------------------------
# UI -- sidebar cu note de transparenta (Responsible AI, vizibil, nu ascuns)
# ---------------------------------------------------------------------------

def render_sidebar():
    with st.sidebar:
        st.markdown("### Despre acest instrument")
        st.caption(
            "Nu stocăm nimic -- conversația trăiește doar în sesiunea curentă și "
            "dispare la refresh."
        )
        st.caption(
            "Acest instrument numește competențe pe baza descrierii tale. "
            "Validarea finală a competențelor rămâne la angajator."
        )
        st.caption(
            "Recomandările de roluri nu se bazează pe vârstă sau alte date demografice -- "
            "doar pe ce ne-ai povestit despre munca ta."
        )
        mode = "LLM activ (Azure OpenAI / OpenAI)" if llm_client.LLM_AVAILABLE else "Mod offline (fallback local)"
        st.info(f"Mod curent: {mode}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.title("🌉 Career Bridge")
    st.caption("Traducem experiența ta reală în limbajul angajatorilor.")

    init_state()
    render_sidebar()

    # afiseaza istoricul de chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    stage = st.session_state.stage

    # --- STAGE: nume ---
    if stage == "name":
        user_input = st.chat_input("Scrie aici...")
        if user_input:
            add_message("user", user_input)
            st.session_state.name = user_input.strip()
            st.session_state.stage = "years"
            add_message("assistant", f"Mă bucur, {st.session_state.name}! "
                                      "Câți ani ai lucrat în producție / fabrică?")
            st.rerun()

    # --- STAGE: ani experienta ---
    elif stage == "years":
        user_input = st.chat_input("Scrie aici...")
        if user_input:
            add_message("user", user_input)
            match = re.search(r"\d+", user_input)
            st.session_state.years_experience = match.group(0) if match else user_input.strip()
            st.session_state.stage = "interview"
            first_q = FALLBACK_QUESTIONS[0]
            st.session_state.current_question = first_q
            add_message("assistant", first_q)
            st.rerun()

    # --- STAGE: interviu narativ ---
    elif stage == "interview":
        user_input = st.chat_input("Scrie aici...")
        if user_input:
            add_message("user", user_input)
            current_q = st.session_state.current_question
            st.session_state.interview_qas.append((current_q, user_input))
            st.session_state.question_index += 1

            if st.session_state.question_index >= TOTAL_QUESTIONS:
                # gata interviul -> extractie skill-uri
                st.session_state.stage = "confirm_skills"
                skills = taxonomy.extract_skills_from_transcript(full_transcript_text())
                st.session_state.extracted_skills = skills
                st.session_state.confirmed_skill_keys = [s["key"] for s in skills]

                if skills:
                    lines = ["Uite ce am înțeles din ce mi-ai povestit -- spune-mi dacă e corect:\n"]
                    for s in skills:
                        lines.append(f"- **{s['label_ro']}** -- ai spus: \"{s['evidence']}\"")
                    summary = "\n".join(lines)
                else:
                    summary = ("Nu am reușit să identific competențe clare din răspunsurile tale -- "
                               "poți bifa manual mai jos ce ți se potrivește.")
                add_message("assistant", summary)
            else:
                history_for_llm = []
                for q, a in st.session_state.interview_qas:
                    history_for_llm.append({"role": "assistant", "content": q})
                    history_for_llm.append({"role": "user", "content": a})
                next_q = next_interview_question(history_for_llm)
                st.session_state.current_question = next_q
                add_message("assistant", next_q)
            st.rerun()

    # --- STAGE: confirmare skill-uri ---
    elif stage == "confirm_skills":
        st.markdown("#### Confirmă competențele identificate")
        all_keys = list(taxonomy.SKILLS_TAXONOMY.keys())
        default_selected = st.session_state.confirmed_skill_keys

        selected = st.multiselect(
            "Bifează ce ți se potrivește (poți adăuga sau elimina):",
            options=all_keys,
            default=default_selected,
            format_func=lambda k: taxonomy.SKILLS_TAXONOMY[k]["label_ro"],
        )

        if st.button("Confirmă și continuă"):
            st.session_state.confirmed_skill_keys = selected
            st.session_state.stage = "role_selection"
            add_message("assistant", "Perfect. Acum hai să vedem pentru ce rol te pregătim.")
            st.rerun()

    # --- STAGE: alegere rol tinta ---
    elif stage == "role_selection":
        st.markdown("#### Alege rolul țintă")
        role_options = {r["id"]: f"{r['title_ro']} ({r['title_en']})" for r in taxonomy.ROLES}
        chosen = st.radio(
            "Pe care rol vrei să te concentrezi?",
            options=list(role_options.keys()),
            format_func=lambda rid: role_options[rid],
        )
        if st.button("Vezi planul meu"):
            st.session_state.selected_role_id = chosen
            st.session_state.stage = "output"
            st.rerun()

    # --- STAGE: output final ---
    elif stage == "output":
        role_id = st.session_state.selected_role_id
        role = taxonomy.get_role_by_id(role_id)
        have, missing = taxonomy.compute_gap(st.session_state.confirmed_skill_keys, role_id)

        st.markdown(f"### Rezultatul tău pentru: {role['title_ro']}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Ce ai deja:**")
            if have:
                for k in have:
                    st.markdown(f"✅ {taxonomy.SKILLS_TAXONOMY[k]['label_ro']}")
            else:
                st.markdown("_Niciun skill confirmat încă din cele cerute._")
        with col2:
            st.markdown("**Ce mai lipsește:**")
            if missing:
                for k in missing:
                    st.markdown(f"⬜ {taxonomy.SKILLS_TAXONOMY[k]['label_ro']}")
            else:
                st.markdown("_Nimic -- ai deja tot ce e cerut!_")

        plan_text = plan_generator.generate_12_week_plan(missing, role["title_ro"])
        st.markdown("---")
        st.markdown(plan_text)

        confirmed_skill_objs = [
            s for s in st.session_state.extracted_skills
            if s["key"] in st.session_state.confirmed_skill_keys
        ]
        cv_text = cv_writer.generate_cv(
            st.session_state.name,
            st.session_state.years_experience,
            confirmed_skill_objs,
            role_id,
        )

        st.markdown("---")
        st.markdown("### CV rescris")
        st.markdown(cv_text)

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button("⬇️ Descarcă planul (.md)", plan_text, file_name="plan_12_saptamani.md")
        with dl_col2:
            st.download_button("⬇️ Descarcă CV-ul (.md)", cv_text, file_name="cv.md")

        if st.button("🔄 Ia-o de la capăt"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


if __name__ == "__main__":
    main()
