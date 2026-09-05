# Career Bridge -- MVP

Chat conversațional care traduce experiența reală de muncă (nu diplomele) în
competențe numite, mapate pe roluri țintă din producție, cu plan de 12
săptămâni și CV rescris în limbajul angajatorului.

## Rulare rapidă (fără chei API -- mod offline)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Aplicația funcționează complet **fără nicio cheie API**, folosind
keyword-matching local pentru extracția de skill-uri (fallback din
`taxonomy.py`). E modul recomandat pentru demo, ca să nu depinzi de o
conexiune sau de un API extern în timpul prezentării.

## Rulare cu LLM real (interviu adaptiv + extracție mai flexibilă)

1. Copiază `.env.example` în `.env` și completează fie:
   - `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` (+ opțional `AZURE_OPENAI_DEPLOYMENT`), fie
   - `OPENAI_API_KEY`
2. Încarcă variabilele de mediu înainte de a rula (`export $(cat .env | xargs)`
   pe Mac/Linux, sau folosește `python-dotenv` dacă preferi).
3. `streamlit run app.py`

Cu LLM activ, întrebările de interviu devin adaptive (generate pe baza
răspunsului anterior) și extracția de skill-uri e mai flexibilă decât
keyword-matching-ul simplu.

## Structura proiectului

```
app.py                          # UI Streamlit + logica de stare (chat flow)
llm_client.py                   # wrapper Azure OpenAI / OpenAI, cu fallback
taxonomy.py                     # extractie skill-uri + mapare pe roluri
plan_generator.py               # genereaza planul de 12 saptamani
cv_writer.py                    # genereaza CV-ul rescris
fallback_data/
  roles_manufacturing.json      # 3 roluri tinta + taxonomia de skill-uri
```

## Ce testezi înainte de pitch

- [ ] Rulează întregul flow (nume → ani → 5 întrebări → confirmare skill-uri
      → alegere rol → plan + CV) în mod offline, ca să ai un fallback sigur.
- [ ] Testul de fairness: rulează același transcript o dată cu "20 de ani
      experiență" și o dată cu "2 ani experiență" -- verifică că rolurile
      recomandate și competențele extrase nu depind arbitrar de asta, doar
      de conținutul răspunsurilor.
- [ ] Verifică linkurile Microsoft Learn generate (`taxonomy.learn_search_url`)
      -- sunt linkuri reale de căutare pe learn.microsoft.com.

## Limitări cunoscute (MVP, nu produs final)

- Extracția offline e keyword-matching simplu -- funcționează robust pentru
  cele 3 roluri predefinite, dar nu generalizează la alte industrii fără
  extindere manuală a `roles_manufacturing.json`.
- Fără persistență -- fiecare sesiune Streamlit pornește de la zero (intenționat,
  vezi nota de confidențialitate din sidebar).
- Modulele Microsoft Learn sunt linkuri de căutare, nu module specifice
  verificate individual -- pentru un produs final, ar trebui integrat
  Microsoft Learn Catalog API pentru module exacte.
