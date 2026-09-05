"""
Career Bridge -- MVP demo
Chat conversational care traduce experienta de munca in skill-uri numite,
mapeaza pe roluri tinta si genereaza un plan de 12 saptamani.

Ruleaza cu: streamlit run app.py
"""

import re

import streamlit as st

import llm_client
import taxonomy
import plan_generator
import simulate_persona_interview as persona_sim

st.set_page_config(page_title="Career Bridge", page_icon="🌉", layout="centered")

FALLBACK_QUESTIONS = [
    "Hai să vorbim despre o zi obișnuită de muncă. Ce faci, pas cu pas, când ajungi la fabrică?",
    "Poți să-mi dai un exemplu concret -- ce anume verifici sau ce decizii iei în timpul zilei?",
    "Cum arată o zi în care apare o problemă sau ceva nu merge bine? Ce faci mai exact?",
    "Lucrezi și cu alți colegi sau alte echipe? Cum comunici cu ei în timpul turei?",
    "Ai instruit vreodată pe cineva nou la job, sau ai fost responsabil de alți oameni la un moment dat?",
]

# Raspuns automat pentru fiecare intrebare de mai sus, cate un set per persoana
# preseteta, scris in stilul propriu al fiecarui profil (Profiles/maria.txt / Profiles/dumitru.txt).
PRESET_PERSONAS = {
    "Maria (fabrică auto, Pitești)": {
        "name": "Maria",
        "years": "22",
        "years_question": "Câți ani ai lucrat în producție / fabrică?",
        "answers": [
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
        ],
    },
    "Dumitru (dispecerat transport, Suceava)": {
        "name": "Dumitru",
        "years": "18",
        "years_question": "Câți ani ai lucrat în dispecerat / transport marfă?",
        "answers": [
            # Dumitru e scurt, practic, vorbeste despre soferi, curse si trasee -- nu despre linii de productie.
            "Vin la birou, mă uit peste cursele din ziua respectivă și pe hartă -- văd unde sunt șoferii, "
            "ce trasee au și dacă e ceva blocaj sau vreme urâtă pe drum.",
            "Verific dacă vreo cursă întârzie și decid dacă schimb ruta unui șofer sau îl trimit pe altul "
            "mai aproape, ca marfa să ajungă la timp la client.",
            "Dacă se strică o mașină sau se blochează un drum, sun imediat șoferul, găsesc alt traseu sau "
            "alt șofer liber și anunț clientul cât întârzie livrarea.",
            "Sigur, vorbesc tot timpul cu șoferii pe telefon și cu cei de la depozit, ca să știm ce se "
            "încarcă și pe unde pleacă fiecare cursă.",
            "Am explicat de multe ori dispecerilor mai noi cum se citește harta traficului și cum alegi "
            "repede un traseu alternativ când unul e blocat.",
        ],
    },
}

TOTAL_QUESTIONS = len(FALLBACK_QUESTIONS)

# Stil vizual pentru fiecare platforma de cursuri -- culori vii si iconite mari,
# ca butoanele sa fie usor de recunoscut pentru cineva mai putin obisnuit cu calculatorul.
COURSE_PLATFORM_STYLE = {
    "Microsoft Learn": {"emoji": "🟦", "color": "#0078D4"},
    "Udemy": {"emoji": "🟣", "color": "#A435F0"},
    "Coursera": {"emoji": "🔵", "color": "#0056D2"},
}


def render_course_link_row(platform_label, url):
    """Randeaza o linie clara: text cu numele platformei + buton mare, colorat,
    care deschide link-ul de cautare intr-o fila noua."""
    style = COURSE_PLATFORM_STYLE.get(platform_label, {"emoji": "🔗", "color": "#555555"})
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:16px; margin:10px 0;
                    padding:10px 14px; border-radius:10px; background-color:#f5f5f7;">
            <span style="font-size:1.15rem; min-width:220px;">
                {style['emoji']} <b>Cursuri {platform_label}</b>
            </span>
            <a href="{url}" target="_blank" rel="noopener noreferrer"
               style="background-color:{style['color']}; color:#ffffff; font-weight:bold;
                      font-size:1.05rem; padding:12px 26px; border-radius:8px;
                      text-decoration:none; display:inline-block;">
                Deschide cursurile ➜
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def run_auto_demo(persona_key):
    """Raspunde automat la fiecare intrebare de interviu cu textul preseteat pentru
    persona aleasa si populeaza starea aplicatiei ca si cum utilizatorul ar fi
    raspuns manual, direct pana la ecranul final."""
    persona = PRESET_PERSONAS[persona_key]
    interview_qas = list(zip(FALLBACK_QUESTIONS, persona["answers"]))

    st.session_state.name = persona["name"]
    st.session_state.years_experience = persona["years"]
    st.session_state.interview_qas = interview_qas
    st.session_state.question_index = TOTAL_QUESTIONS

    add_message("user", persona["name"])
    add_message("assistant", f"Mă bucur, {persona['name']}! {persona['years_question']}")
    add_message("user", persona["years"])
    for q, a in interview_qas:
        add_message("assistant", q)
        add_message("user", a)

    skills = taxonomy.extract_skills_from_transcript(full_transcript_text())
    st.session_state.extracted_skills = skills
    st.session_state.confirmed_skill_keys = [s["key"] for s in skills]

    if skills:
        lines = ["(Demo automat) Uite ce am înțeles din răspunsurile simulate:\n"]
        for s in skills:
            lines.append(f"- **{s['label_ro']}** -- ai spus: \"{s['evidence']}\"")
        summary = "\n".join(lines)
    else:
        summary = "(Demo automat) Nu am identificat competențe clare din răspunsurile simulate."
    add_message("assistant", summary)

    role = persona_sim.pick_best_role(st.session_state.confirmed_skill_keys)
    st.session_state.selected_role_id = role["id"]
    add_message(
        "assistant",
        f"(Demo automat) Am confirmat competențele de mai sus și am ales automat rolul "
        f"**{role['title_ro']} ({role['title_en']})**, cel mai apropiat de ce ai povestit.",
    )

    st.session_state.stage = "output"


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

        st.markdown("---")
        st.markdown("### Demo automat")
        st.caption(
            "Alege un profil preseteat -- fie răspunzi întrebare cu întrebare folosind butonul "
            "„Introdu răspunsul lui...” din chat, fie rulezi tot interviul dintr-o dată."
        )
        st.selectbox("Utilizator preseteat", options=list(PRESET_PERSONAS.keys()), key="demo_persona_key")
        if st.button("🤖 Rulează tot interviul automat"):
            persona_key = st.session_state.demo_persona_key
            for key in list(st.session_state.keys()):
                if key != "demo_persona_key":
                    del st.session_state[key]
            init_state()
            run_auto_demo(persona_key)
            st.rerun()


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

    active_persona = PRESET_PERSONAS[st.session_state.demo_persona_key]

    # --- STAGE: nume ---
    if stage == "name":
        user_input = st.chat_input("Scrie aici...")
        if st.button(f"✍️ Introdu răspunsul lui {active_persona['name']}"):
            user_input = active_persona["name"]
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
        if st.button(f"✍️ Introdu răspunsul lui {active_persona['name']}"):
            user_input = active_persona["years"]
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
        idx = st.session_state.question_index
        if idx < len(active_persona["answers"]) and st.button(f"✍️ Introdu răspunsul lui {active_persona['name']}"):
            user_input = active_persona["answers"][idx]
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

        missing_labels_included = bool(missing)
        plan_text = plan_generator.generate_12_week_plan(missing, role["title_ro"])
        st.markdown("---")
        st.markdown(f"## Plan de 12 săptămâni -> {role['title_ro']}")

        if missing_labels_included:
            for section in plan_generator.build_plan_sections(missing):
                st.markdown(f"**Săptămâna {section['start_week']}-{section['end_week']}: {section['label']}**")
                for platform_label, url in section["course_links"]:
                    render_course_link_row(platform_label, url)
                st.markdown(
                    "Exercițiu practic: scrie 3 exemple din experiența ta care arată deja părți din acest skill."
                )
        else:
            st.markdown(
                "Ai deja competențele principale cerute de acest rol. "
                "Cele 12 săptămâni se concentrează pe pregătirea aplicației și a interviurilor."
            )

        for title, body in plan_generator.FINAL_WEEKS:
            st.markdown(f"**{title}**")
            st.markdown(body)

        st.markdown(
            "_Notă: acest plan arată rolurile cu cerere în zona ta și un traseu posibil de pregătire, "
            "dar nu garantează angajarea. Validarea finală a competențelor rămâne la angajator._"
        )

        st.download_button("⬇️ Descarcă planul (.md)", plan_text, file_name="plan_12_saptamani.md")

        if st.button("🔄 Ia-o de la capăt"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


if __name__ == "__main__":
    main()
