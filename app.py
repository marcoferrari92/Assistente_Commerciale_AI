import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import io
import json
from datetime import datetime

# Configurazione di pagina (Eseguita una sola volta all'inizio)
st.set_page_config(page_title="AI Smart Sales CRM", page_icon="🎙️", layout="centered")

# --- CONTROLLO ACCESSO MULTI-UTENTE ---
def login_commerciale():
    if "user_data" not in st.session_state:
        st.session_state.user_data = None

    if st.session_state.user_data:
        return st.session_state.user_data

    st.title("Morpheous")
    st.write("Il tuo Assistente AI")
    st.write(r"""
    *"Pillola blu, fine della storia: domani ti sveglierai in camera tua, e crederai a quello che vorrai. 
    Pillola rossa, resti nel Paese delle Meraviglie, e vedrai quant'è profonda la tana del Bianconiglio. 
    Ti sto offrendo solo la verità. Ricordalo. Niente di più"*""")
    username = st.text_input("Username (Nome)", key="login_username").lower().strip()
    password = st.text_input("Password", type="password", key="login_password")
    
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

# Mostriamo il resto dell'applicazione solo se l'utente è connesso
if utente_connesso:
    st.sidebar.write(f"👤 Utente: **{utente_connesso['username'].capitalize()}**")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.user_data = None
        st.rerun()

    # --- INIZIALIZZAZIONE CLIENT OPENAI DA SECRETS ---
    # Gestione sicura nel caso in cui la chiave non sia ancora presente nei secrets di Streamlit
    if "openai_key" in st.secrets:
        client = OpenAI(api_key=st.secrets["openai_key"])
    else:
        st.error("⚠️ Chiave API 'openai_key' non trovata!")
        client = None

    # --- 1. INIZIALIZZAZIONE STATO DEL MODULO ---
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            "cliente": "",
            "tipologia": "telefonata",
            "oggetto": "",
            "contatto": "",
            "vibes": "Positive 👍",
            "note": "",
            "next_step": "",       
            "promemoria": None     
        }
    if 'audio_summary_done' not in st.session_state:
        st.session_state.audio_summary_done = False

    if 'mic_key_counter' not in st.session_state:
        st.session_state.mic_key_counter = 0

    # --- 4. FUNZIONI ---
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
        I campi sono: cliente, tipologia, oggetto, contatto, vibes, note, next_step, promemoria.

        REGOLE PER IL CAMPO "contatto"
        - Inserisce nome e cognome se noti e tra parentesi l'ufficio o l'area aziendale del contatto.

        REGOLE CRITICHE PER IL CAMPO 'tipologia':
        - Indica la tipologia dell'evento.
        - Deve essere SOLO uno di questi tre valori: "telefonata", "email", "visita".
        - Se l'utente dice "ho chiamato" o "ci siamo sentiti", usa "telefonata".
        - Se l'utente dice "ho scritto" o "mi ha risposto alla mail", usa "email".
        - Se l'utente dice "sono andato da loro" o "abbiamo pranzato insieme", usa "visita".
        - Se non è chiaro, scrivi null.

        REGOLE PER IL CAMPO 'oggetto':
        - Inserisci solo il motivo che ha generato l'evento. 
        - Anche se il commerciale si spiega poco o in modo confuso, crea un riassunto professionale di massimo 10 parole.
        - Se non dice nulla di utile per l'oggetto, scrivi null.

        REGOLE PER LE NOTE:
        - Inserisci le impressioni del commerciale sull'oggetto dell'evento.
        - Inserisci tutte le note tecniche in modo esaustivo.
        
        REGOLE PER IL CAMPO 'next_step':
        - Identifica l'azione futura concordata o pianificata (es. "Inviare preventivo", "Richiamare per conferma", "Fissare demo").
        - Se non viene menzionata nessuna azione futura, scrivi null.
        
        REGOLE PER IL CAMPO 'promemoria':
        - Identifica la data in cui il commerciale desidera essere avvisato o in cui è previsto il next step.
        - Sapendo che OGGI è il {current_date_str}, converti espressioni temporali (es. "domani", "prossima settimana", "il 25 maggio") nel formato standard YYYY-MM-DD.
        - Se non viene specificata alcuna data o periodo di tempo, scrivi null.

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

    # --- 5. LOGICA PRINCIPALE ---
    st.title("Assistente Commerciale")

    st.write("### 🎤 Assistente Rapido")
    
    # CORREZIONE: Ora controlliamo se il client OpenAI è attivo, senza usare la vecchia variabile api_key
    if not client:
        st.warning("Assistente vocale non disponibile. Verifica la chiave API nei Secrets.")
    else:
        audio = mic_recorder(
            start_prompt="🎤 Racconta l'evento ", 
            stop_prompt="🤓 Elabora l'audio", 
            key=f"mic_{st.session_state.mic_key_counter}"
        )

        if audio:
            with st.spinner("L'AI sta compilando il modulo per te..."):
                res = analyze_full_report(audio['bytes'])
                if res:
                    for k in st.session_state.form_data.keys():
                        if k in res and res[k]: 
                            if k == "promemoria":
                                try:
                                    st.session_state.form_data[k] = datetime.strptime(res[k], "%Y-%m-%d").date()
                                except:
                                    st.session_state.form_data[k] = None
                            else:
                                st.session_state.form_data[k] = res[k]
                    
                    st.session_state.audio_summary_done = False 
                    st.session_state.mic_key_counter += 1 
                    st.rerun()

    st.divider()

    # --- 5. IL MODULO ---
    st.write("### 📝 Modulo Evento")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.form_data["cliente"] = st.text_input("Cliente", value=st.session_state.form_data["cliente"])
        st.session_state.form_data["contatto"] = st.text_input("Contatto", value=st.session_state.form_data["contatto"])
        
        st.write("**Esito (Vibes):**")
        v_val = st.session_state.form_data["vibes"]
        v_idx = 1 if v_val and "Negative" in v_val else 0
        
        st.session_state.form_data["vibes"] = st.radio(
            "Esito evento", ["Positivo 👍", "Negativo 👎"], 
            index=v_idx, horizontal=True, label_visibility="collapsed"
        )

    with col2:
        t_options = ["telefonata", "email", "visita"]
        t_val = st.session_state.form_data["tipologia"]
        t_idx = t_options.index(t_val) if t_val in t_options else 0
        st.session_state.form_data["tipologia"] = st.selectbox("Tipologia", t_options, index=t_idx)
        
        st.session_state.form_data["oggetto"] = st.text_input("Oggetto", value=st.session_state.form_data["oggetto"])

    st.session_state.form_data["note"] = st.text_area("Note Dettagliate", value=st.session_state.form_data["note"], height=150)

    # --- NUOVA SEZIONE: PIANIFICAZIONE AZIONI FUTURE ---
    st.write("### 🎯 Azioni Future & Scadenze")
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

    # --- 6. RIASSUNTO VOCALE DI CONFERMA ---
    if st.session_state.form_data["note"] != "" and not st.session_state.audio_summary_done:
        d = st.session_state.form_data
        promemoria_str = d['promemoria'].strftime('%d/%m/%Y') if d['promemoria'] else 'non impostato'
        
        testo_riepilogo = (
            f"Ricevuto. Ecco il riepilogo completo dell'evento. "
            f"Cliente: {d['cliente']}. "
            f"Contatto: {d['contatto'] if d['contatto'] else 'non specificato'}. "
            f"Tipologia: {d['tipologia']}. "
            f"Oggetto: {d['oggetto']}. "
            f"Note: {d['note']}. "
            f"Esito dell'incontro: {d['vibes']}. "
            f"Prossimo passo: {d['next_step'] if d['next_step'] else 'nessuno specificato'}. "
            f"Data di promemoria: {promemoria_str}. "
            f"Se è tutto corretto, procedi pure con il salvataggio."
        )
        
        with st.spinner("L'AI sta leggendo il riepilogo finale..."):
            audio_msg = speak(testo_riepilogo)
            if audio_msg:
                st.audio(audio_msg, autoplay=True)
                st.session_state.audio_summary_done = True

    # --- 7. SALVATAGGIO ---
    st.divider()
    if st.button("💾 SALVA EVENTO SUL DATABASE", type="primary", use_container_width=True):
        st.balloons()
        st.success("Evento registrato correttamente!")
        
        final_data = st.session_state.form_data.copy()
        if final_data["promemoria"]:
            final_data["promemoria"] = final_data["promemoria"].strftime("%Y-%m-%d")
            
        st.write("Dati inviati:", final_data)
