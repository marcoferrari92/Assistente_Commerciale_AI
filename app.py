import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import io
import json
from datetime import datetime, time

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="AI Smart Sales CRM", page_icon="🎙️", layout="centered")

# --- 2. INIZIALIZZAZIONE STATO GLOBALE ---
if 'form_data' not in st.session_state:
    st.session_state.form_data = {
        "cliente": "",
        "tipologia": "telefonata",
        "oggetto": "",
        "contatto": "",
        "vibes": None,  
        "note": "",
        "next_step": "",        
        "promemoria": None,
        "orario_promemoria": time(9, 0),
        "allegati": []  
    }
if 'campi_mancanti' not in st.session_state:
    st.session_state.campi_mancanti = []

if 'audio_summary_done' not in st.session_state:
    st.session_state.audio_summary_done = False

if 'mic_key_counter' not in st.session_state:
    st.session_state.mic_key_counter = 0


# --- 3. CONTROLLO ACCESSO MULTI-UTENTE (IMPRENDO MORPHEUS) ---
def login_commerciale():
    if "user_data" not in st.session_state:
        st.session_state.user_data = None

    if st.session_state.user_data:
        return st.session_state.user_data

    st.title("🔒 Imprendo Morpheus")
    st.write("### Il tuo Assistente AI")
    st.write(r"""
    *"Pillola blu, fine della storia: domani ti sveglierai in camera tua, e crederai a quello che vorrai. 
    Pillola rossa, resti nel Paese delle Meraviglie, e vedrai quant'è profonda la tana del Bianconiglio. 
    Ti sto offrendo solo la verità. Ricordalo. Niente di più"*""")
    
    username = st.text_input(
        "Username (Nome)", 
        key="login_username", 
        autocomplete="username"
    ).lower().strip()
    
    password = st.text_input(
        "Password", 
        type="password", 
        key="login_password", 
        autocomplete="current-password"
    )
    
    if st.button("Accedi", use_container_width=True):
        if "commerciali" in st.secrets and username in st.secrets["commerciali"]:
            db_user = st.secrets["commerciali"][username]
            if password == db_user["password"]:
                st.session_state.user_data = {"username": username, "email": db_user["email"]}
                st.rerun()
            else:
                st.error("❌ Password errata.")
        else:
            st.error("❌ Utente non trovato.")
    return None

utente_connesso = login_commerciale()

# --- 4. CORE DELL'APPLICAZIONE (Eseguito solo se loggato) ---
if utente_connesso:
    st.sidebar.write(f"👤 Utente: **{utente_connesso['username'].capitalize()}**")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.user_data = None
        st.rerun()

    # --- INIZIALIZZAZIONE CLIENT OPENAI ---
    if "openai_key" in st.secrets:
        client = OpenAI(api_key=st.secrets["openai_key"])
    else:
        st.error("⚠️ Chiave API 'openai_key' non trovato nei Secrets!")
        client = None

    # --- FUNZIONI ---
    def speak(text):
        if not client: return None
        try:
            response = client.audio.speech.create(model="tts-1", voice="nova", input=text)
            return response.content
        except Exception as e:
            st.error(f"Errore TTS: {e}")
            return None

    def analyze_full_report(audio_bytes):
        if not client: return None
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.mp3"
        transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file, language="it")
        
        current_date_str = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""
        Sei l'assistente di un commerciale che si è appena interfacciato con un cliente tramite una telefonata, una visita o un'email.
        Analizza il suo rapporto e restituisci un JSON.
        I campi sono: cliente, tipologia, oggetto, contatto, vibes, note, next_step, promemoria, orario_promemoria.

        REGOLE PER IL CAMPO "contatto"
        - Inserisce nome e cognome se noti e tra parentesi l'ufficio o l'area aziendale del contatto.

        REGOLE CRITICHE PER IL CAMPO 'tipologia':
        - Indica la tipologia dell'evento.
        - Deve essere SOLO uno di questi tre valori: "telefonata", "email", "visita".
        - Se l'utente dice "ho chiamato" o "ci siamo sentiti", usa "telefonata".
        - Se l'utente dice "ho scritto" o "mi ha risposto alla mail", usa "email".
        - Se l'utente dice "sono andato da loro" o "abbiamo pranzato insieme", usa "visita".
        - CRITICO: Se non è chiaro, scrivi null.

        REGOLE PER IL CAMPO 'oggetto':
        - Inserisci solo il motivo che ha generato l'evento. 
        - Anche se il commerciale si spiega poco o in modo confuso, crea un riassunto professionale di massimo 10 parole.
        - CRITICO: Se non dice nulla di utile per l'oggetto, scrivi null.

        REGOLE PER IL CAMPO 'vibes':
        - Analizza il tono di voce e le parole del commerciale per capire l'esito dell'incontro o della telefonata.
        - Se l'incontro è andato bene, c'è interesse, o l'accordo è positivo, scrivi ESATTAMENTE "Positivo 👍".
        - Se ci sono stati problemi, lamentele, esito negativo o chiusura, scrivi ESATTAMENTE "Negativo 👎".
        - CRITICO: Se l'utente non esprime un'opinione chiara, se il tono è neutro o se non riesci a capire l'esito dal racconto, scrivi null. Non inventare o ipotizzare.

        REGOLE PER LE NOTE:
        - Inserisci le impressioni del commerciale sull'oggetto dell'evento.
        - Inserisci tutte le note tecniche in modo esaustivo.
        
        REGOLE PER IL CAMPO 'next_step':
        - Identifica l'azione futura concordata o pianificata (es. "Inviare preventivo", "Richiamare per conferma", "Fissare demo").
        - CRITICO: Se non viene menzionata nessuna azione futura, scrivi null.
        
        REGOLE PER IL CAMPO 'promemoria':
        - Identifica la data in cui il commerciale desidera essere avvisato o in cui è previsto il next step.
        - Sapendo che OGGI è il {current_date_str}, converti espressioni temporali (es. "domani", "prossima settimana", "il 25 maggio") nel formato standard YYYY-MM-DD.
        - CRITICO: Se non viene specificata alcuna data o periodo di tempo, scrivi null.

        REGOLE PER IL CAMPO 'orario_promemoria':
        - Identifica se l'utente specifica un momento della giornata o un orario per il promemoria e convertilo nel formato standard HH:MM:
          * "mattina" o "in mattinata" -> "09:00"
          * "pranzo" o "ora di pranzo" -> "13:00"
          * "pomeriggio" -> "15:30"
          * "sera" o "tardo pomeriggio" -> "18:00"
          * Se dice un orario specifico (es. "alle 11", "alle 14:30"), usa esattamente quell'orario ("11:00", "14:30").
        - CRITICO: Se l'utente specifica una data per il promemoria ma NON dice nessun orario o momento della giornata, assegna il valore predefinito "09:00". Se non c'è nemmeno il promemoria, scrivi null.

        Se un dato manca, usa null.
        Aggiungi il campo 'mancanti' con la lista dei campi null.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": transcript.text}
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    
    # --- LOGICA INTERFACCIA PRINCIPALE ---
    st.title("🎙️ Imprendo Morpheus")
    st.divider()
    st.write("### Assistente Rapido")

    if not client:
        st.warning("Assistente vocale non disponibile. Verifica la chiave API nei Secrets.")
    else:
        audio = mic_recorder(
            start_prompt="🎤 RACCONTA L'EVENTO", 
            stop_prompt="⏹️ ELABORA REPORT", 
            key=f"mic_{st.session_state.mic_key_counter}"
        )

        if audio:
            with st.spinner("Morpheus sta scrivendo i dati..."):
                res = analyze_full_report(audio['bytes'])
                if res:
                    st.session_state.campi_mancanti = res.get("mancanti", [])
                    
                    for k in st.session_state.form_data.keys():
                        if k in res:
                            if res[k] is None:
                                if k == "promemoria" or k == "vibes":
                                    st.session_state.form_data[k] = None
                                elif k == "orario_promemoria":
                                    st.session_state.form_data[k] = time(9, 0)
                                else:
                                    st.session_state.form_data[k] = ""
                            else:
                                if k == "promemoria":
                                    try:
                                        st.session_state.form_data[k] = datetime.strptime(res[k], "%Y-%m-%d").date()
                                    except:
                                        st.session_state.form_data[k] = None
                                elif k == "orario_promemoria":
                                    try:
                                        st.session_state.form_data[k] = datetime.strptime(res[k], "%H:%M").time()
                                    except:
                                        st.session_state.form_data[k] = time(9, 0)
                                else:
                                    st.session_state.form_data[k] = res[k]
                    
                    st.session_state.audio_summary_done = False 
                    st.session_state.mic_key_counter += 1 
                    st.rerun()

    st.write("")
    st.write("")

    # --- FEEDBACK DEI CAMPI MANCANTI ---
    if st.session_state.campi_mancanti:
        nomi_puliti = [c.replace("_", " ").capitalize() for c in st.session_state.campi_mancanti if c != "orario_promemoria"]
        if nomi_puliti:
            st.warning(f"⚠️ **Informazioni incomplete:** L'AI non ha rilevato i seguenti dettagli dal tuo audio: {', '.join(nomi_puliti)}. Per favore, integrali a mano nel modulo sottostante.")

    # --- CREAZIONE DELLE TAB PER ORGANIZZARE IL LAYOUT ---
    tab_dati, tab_allegati = st.tabs(["📝 Evento", "📸 Allegati"])

    # --- TAB 1: DATI DEL FORM EVENTO ---
    with tab_dati:
        st.write("### Evento")

        # Riga 1: Cliente e Tipologia
        col_r1_1, col_r1_2 = st.columns(2)
        with col_r1_1:
            st.session_state.form_data["cliente"] = st.text_input("Cliente", value=st.session_state.form_data["cliente"])
        with col_r1_2:
            t_options = ["telefonata", "email", "visita"]
            t_val = st.session_state.form_data["tipologia"]
            t_idx = t_options.index(t_val) if t_val in t_options else 0
            st.session_state.form_data["tipologia"] = st.selectbox("Tipologia", t_options, index=t_idx)

        # Riga 2: Esito (Vibes) e Oggetto
        col_r2_1, col_r2_2 = st.columns(2)
        with col_r2_1:
            st.write("**Esito (Vibes):**")
            v_val = st.session_state.form_data["vibes"]
            if v_val == "Positivo 👍":
                v_idx = 0
            elif v_val == "Negativo 👎":
                v_idx = 1
            else:
                v_idx = None
            
            v_scelta = st.radio(
                "Esito evento", ["Positivo 👍", "Negativo 👎"], 
                index=v_idx, horizontal=True, label_visibility="collapsed"
            )
            st.session_state.form_data["vibes"] = v_scelta
        with col_r2_2:
            st.session_state.form_data["oggetto"] = st.text_input("Oggetto", value=st.session_state.form_data["oggetto"])

        # Riga 3: Contatto
        st.session_state.form_data["contatto"] = st.text_input("Contatto", value=st.session_state.form_data["contatto"])

        # Riga 4: Note Dettagliate
        st.session_state.form_data["note"] = st.text_area("Note Dettagliate", value=st.session_state.form_data["note"], height=150)

        # --- PIANIFICAZIONE AZIONI FUTURE ---
        st.write("")
        st.write("")
        st.write("### Azioni Future & Scadenze")
        col_next, col_date = st.columns([2, 1])

        with col_next:
            st.session_state.form_data["next_step"] = st.text_input(
                "Prossimo Step (Cosa fare dopo)", 
                value=st.session_state.form_data["next_step"],
                placeholder="Es. Inviare quotazione economica"
            )

        with col_date:
            current_date_val = st.session_state.form_data["promemoria"]
            chosen_date = st.date_input(
                "Data Promemoria", 
                value=current_date_val if current_date_val else datetime.now().date()
            )
            st.session_state.form_data["promemoria"] = chosen_date
            
            current_time_val = st.session_state.form_data.get("orario_promemoria", time(9, 0))
            if current_time_val is None:
                current_time_val = time(9, 0)
                
            chosen_time = st.time_input("Orario Specifico", value=current_time_val)
            st.session_state.form_data["orario_promemoria"] = chosen_time

    # --- TAB 2: ALLEGATI (FOTO E FILE SEPARATI) ---
    with tab_allegati:
        #st.write("### 📸 Documenti & Foto Allegati")
        uploaded_files = st.file_uploader(
            "Trascina qui i file o tocca per scattare una foto/selezionare un allegato",
            type=["png", "jpg", "jpeg", "pdf", "docx", "xlsx"],
            accept_multiple_files=True
        )
        
        st.session_state.form_data["allegati"] = []
        if uploaded_files:
            for file in uploaded_files:
                st.session_state.form_data["allegati"].append({
                    "nome_file": file.name,
                    "tipo_file": file.type,
                    "dimensione": file.size
                })
            st.success(f"📎 {len(uploaded_files)} file pronti per essere salvati con questo evento.")

    # --- 6. RIASSUNTO VOCALE DI CONFERMA GENERATO DA AI ---
    if st.session_state.form_data["note"] != "" and not st.session_state.audio_summary_done:
        d = st.session_state.form_data
        promemoria_str = d['promemoria'].strftime('%d/%m/%Y') if d['promemoria'] else 'non impostato'
        orario_str = d['orario_promemoria'].strftime('%H:%M') if d['orario_promemoria'] else '09:00'
        
        with st.spinner("Morpheus sta preparando il riepilogo vocale..."):
            prompt_riepilogo = f"""
            Sei Morpheus, l'assistente virtuale del commerciale. 
            Genera un breve discorso di conferma (massimo 3-4 frasi) in modo naturale, fluido e colloquiale ma professionale.
            Usa questi dati reali per formulare il discorso:
            - Cliente (Azienda): {d['cliente']}
            - Tipologia evento (es. telefonata, visita, email): {d['tipologia']}
            - Contatto dell'azienda (con eventuale ruolo/ufficio): {d['contatto'] if d['contatto'] else 'non specificato'}
            - Oggetto: {d['oggetto'] if d['oggetto'] else 'non specificato'}
            - Esito dell'incontro (Vibes): {d['vibes'] if d['vibes'] else 'non specificato'}
            - Note e dettagli rilevanti: {d['note']}
            - Prossimo Step: {d['next_step'] if d['next_step'] else 'nessuno'}
            - Data Promemoria: {promemoria_str}
            - Orario Rilevato per Calendario: {orario_str}
            
            REGOLE DI TONO E STRUTTURA:
            - Non fare un elenco della spesa. Il discorso deve essere fluido e continuo.
            - Specifica subito la tipologia di evento e con chi hai parlato.
            - Se l'esito è "Positivo 👍", usa un tono soddisfatto. Se è "Negativo 👎", usa un tono pragmatico.
            - Riassumi brevemente il fulcro delle note.
            - COMUNICA L'ORARIO: Nel riassunto, specifica l'orario esatto che hai assegnato per il calendario (es. "...e ho impostato il promemoria per il {promemoria_str} alle ore {orario_str}"). Rendi la frase naturale.
            - Chiudi dicendo che se è tutto corretto si può procedere con il salvataggio.
            - Non usare elenchi puntati, numeri o asterischi, scrivi solo testo liscio da leggere direttamente.
            """
            
            try:
                response_testo = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt_riepilogo}]
                )
                testo_fluido = response_testo.choices[0].message.content
                
                audio_msg = speak(testo_fluido)
                if audio_msg:
                    st.audio(audio_msg, autoplay=True)
                    st.session_state.audio_summary_done = True
            except Exception as e:
                st.error(f"Errore nella generazione del riepilogo AI: {e}")

    # --- 7. SALVATAGGIO ---
    st.divider()
    if st.button("💾 SALVA EVENTO SUL DATABASE", type="primary", use_container_width=True):
        st.balloons()
        st.success("Evento registrato correttamente!")
        
        final_data = st.session_state.form_data.copy()
        if final_data["promemoria"]:
            final_data["promemoria"] = final_data["promemoria"].strftime("%Y-%m-%d")
            
        if final_data["orario_promemoria"]:
            final_data["orario_promemoria"] = final_data["orario_promemoria"].strftime("%H:%M")
            
        st.write("Dati inviati:", final_data)
        st.session_state.campi_mancanti = []
