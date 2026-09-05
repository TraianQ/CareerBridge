"""
Wrapper subtire peste Azure OpenAI / OpenAI, cu fallback in mod "mock" daca nu
exista cheie configurata. Asta permite ca aplicatia sa ruleze integral offline
pentru demo, si sa foloseasca LLM real de indata ce ai cheile.

Config prin variabile de mediu (vezi .env.example):
  AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT
  sau, alternativ, OPENAI_API_KEY (OpenAI standard, fara Azure)
"""

import os
import json

AZURE_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

LLM_AVAILABLE = bool(AZURE_KEY and AZURE_ENDPOINT) or bool(OPENAI_KEY)

_client = None


def _get_client():
    """Lazy init, ca sa nu cerem dependenta 'openai' daca nu e nevoie."""
    global _client
    if _client is not None:
        return _client
    if AZURE_KEY and AZURE_ENDPOINT:
        from openai import AzureOpenAI
        _client = AzureOpenAI(
            api_key=AZURE_KEY,
            azure_endpoint=AZURE_ENDPOINT,
            api_version="2024-08-01-preview",
        )
    elif OPENAI_KEY:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_KEY)
    return _client


def _chat(messages, max_tokens=600, temperature=0.4):
    """Apel generic de chat completion. Ridica exceptie daca nu e configurat."""
    if not LLM_AVAILABLE:
        raise RuntimeError("Nicio cheie LLM configurata (mod mock activ).")
    client = _get_client()
    model_name = AZURE_DEPLOYMENT if (AZURE_KEY and AZURE_ENDPOINT) else "gpt-4o-mini"
    resp = client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content


# ---------------------------------------------------------------------------
# 1. Generarea urmatoarei intrebari de interviu (adaptiva)
# ---------------------------------------------------------------------------

INTERVIEW_SYSTEM_PROMPT = """Esti un consilier de cariera empatic, care intervieveaza
un adult de 45+ ani, in reconversie profesionala dintr-un job de productie/fabrica.
Scopul tau este sa afli, prin intrebari simple si concrete, ce face efectiv persoana
la locul de munca -- nu ce diplome are. Vorbeste in romana, ton cald, fara jargon.
Pui o singura intrebare scurta, bazata pe ce a spus persoana pana acum, ca sa scoti
la iveala detalii concrete (ex: cum verifica, ce decizii ia, cum comunica cu echipa).
Nu repeta intrebari deja puse. Raspunde DOAR cu intrebarea, fara alt text."""


def generate_followup_question(conversation_history):
    """conversation_history: lista de dict-uri {role, content}. Returneaza string."""
    if not LLM_AVAILABLE:
        raise RuntimeError("mock mode")
    messages = [{"role": "system", "content": INTERVIEW_SYSTEM_PROMPT}] + conversation_history
    return _chat(messages, max_tokens=120).strip()


# ---------------------------------------------------------------------------
# 2. Extractia de skill-uri implicite din transcript
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM_PROMPT = """Esti un extractor de competente profesionale. Primesti
un transcript al unui interviu cu un muncitor din productie. Identifica skill-urile
implicite mentionate, mapate STRICT pe una din urmatoarele chei posibile:
quality_inspection, shift_coordination, safety_compliance, incident_reporting,
equipment_maintenance, training_new_staff, process_documentation,
problem_solving_production, communication_cross_team, statistical_process_control.

Raspunde DOAR cu JSON valid, fara alt text, in formatul:
{"skills": [{"key": "quality_inspection", "evidence": "citat scurt din ce a spus persoana"}]}
Include doar skill-urile pentru care exista dovada clara in transcript."""


def extract_skills_llm(transcript_text):
    if not LLM_AVAILABLE:
        raise RuntimeError("mock mode")
    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": transcript_text},
    ]
    raw = _chat(messages, max_tokens=500, temperature=0.1)
    cleaned = raw.strip().strip("`").replace("json\n", "", 1)
    return json.loads(cleaned)


# ---------------------------------------------------------------------------
# 3. Simularea raspunsurilor unei persoane (persona), pe baza unui profil text
#    Util pentru testarea interviului (app.py) fara input manual.
# ---------------------------------------------------------------------------

PERSONA_SYSTEM_PROMPT_TEMPLATE = """Interpretezi rolul unei persoane reale, descrisa mai jos.
Raspunzi la intrebarile unui consilier de cariera EXACT asa cum ar raspunde aceasta persoana:
la persoana intai, in romana vorbita, cu propriile ei cuvinte si nivel de vocabular
(fara termeni tehnici de HR/IT pe care persoana nu i-ar folosi), cu exemple concrete
din munca ei descrisa mai jos. Raspunsurile sunt scurte (2-4 fraze), naturale, ca intr-o
conversatie reala, nu ca o lista. Nu iesi din personaj si nu mentiona ca esti un AI.

Profilul persoanei:
---
{persona_text}
---
"""


def answer_as_persona(persona_text, conversation_history):
    """Genereaza raspunsul persoanei la ultima intrebare din conversation_history.

    persona_text: descrierea persoanei (ex: continutul din Profiles/maria.txt)
    conversation_history: lista de dict-uri {role, content}, unde ultimul mesaj
        (role="assistant") e intrebarea la care persoana trebuie sa raspunda.
    """
    if not LLM_AVAILABLE:
        raise RuntimeError("mock mode")
    system_prompt = PERSONA_SYSTEM_PROMPT_TEMPLATE.format(persona_text=persona_text)
    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    return _chat(messages, max_tokens=200, temperature=0.6).strip()
