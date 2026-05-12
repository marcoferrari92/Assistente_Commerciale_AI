import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import io
import json

st.set_page_config(page_title="AI Smart Sales", page_icon="🎙️")

# --- 1. INIZIALIZZAZIONE STATO ---
if 'data' not in st.session_state:
    st.session_state.data = {}
if 'missing' not in st.session_state:
    st.session_state.missing = []

# --- 2. SIDEBAR (Widget dichiarati UNA SOLA VOLTA) ---
with st.sidebar:
    st.header("Configurazione")
    # Definiamo la chiave API qui e la usiamo ovunque tramite variabile
    api_key = st.text_input("OpenAI API Key", type="password", key="main_api_key")
    
    if st.button("🔄 Reset Totale"):
        st.session_state.data = {}
        st.session_state.missing = []
        st.rerun()

# --- 3. CREAZIONE CLIENT ---
client = None
if api_key:
    client = OpenAI(api_key=api_key)

# --- 4. FUNZIONI (Senza widget interni) ---
def speak(text):
    if not client: return None
    try:
        response = client.audio.speech.create(model="tts-1", voice="nova", input=text)
        return response.content
    except Exception as e:
        st.error(f"Errore TTS: {e}")
        return None

def analyze_report(audio_bytes):
    if not client: return None
    
    # Trascrizione Whisper
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.mp3"
    transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file, language="it")
    
    # Analisi JSON con vincolo sulla tipologia
    prompt = """
    Sei l'assistente di un commerciale che si è appena interfacciato con un cliente tramite una telefonata, una visita o un'email.
    Analizza il suo rapporto e restituisci un JSON.
    I campi sono: cliente, tipologia, oggetto, contatto, vibes, note.

    REGOLE CRITICHE PER IL CAMPO 'tipologia':
    - Indica la tipologia dell'evento.
    - Deve essere SOLO uno di questi tre valori: "telefonata", "email", "visita".
    - Se l'utente dice "ho chiamato" o "ci siamo sentiti", usa "telefonata".
    - Se l'utente dice "ho scritto" o "mi ha risposto alla mail", usa "email".
    - Se l'utente dice "sono andato da loro" o "abbiamo pranzato insieme", usa "visita".
    - Se non è chiaro, scrivi null.

    REGOLE PER IL CAMPO 'oggetto':
    - Inserisci solo il motivo che ha generato l'evento. 
    - Anche se il commerciale si spiega poco o in modo confuso, crea un riassunto professionale di circa 10 parole.
    - Se non dice nulla di utile per l'oggetto, scrivi null.

    REGOLE PER LE NOTE
    - Inserisci le impressioni del commerciale sull'oggetto dell'evento o su altre questioni sorte durante l'evento.
    - Fai un riassunto di circa 40 parole. 
    

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

if not api_key:
    st.warning("⚠️ Inserisci la tua OpenAI API Key nella barra laterale.")
else:
    # FASE 1: RACCONTO INIZIALE
    if not st.session_state.data:
        st.info("💡 Racconta l'evento (Cliente, tipo, oggetto, contatto, vibes, note).")
        audio = mic_recorder(start_prompt="Inizia a raccontare 🎤", stop_prompt="Analizza ⚙️", key="main_mic")
        
        if audio:
            with st.spinner("Analisi in corso..."):
                res = analyze_report(audio['bytes'])
                if res:
                    st.session_state.data = res
                    st.session_state.missing = res.get('mancanti', [])
                    st.rerun()

    # FASE 2: RECUPERO DATI MANCANTI
    elif st.session_state.missing:
        campo_mancante = st.session_state.missing[0]
        messaggio = f"Mi manca il campo: {campo_mancante}. Puoi dirmelo?"
        
        st.warning(f"🔎 {messaggio}")
        
        # Audio di avviso (solo una volta per step)
        audio_msg = speak(messaggio)
        if audio_msg:
            st.audio(audio_msg, autoplay=True)
        
        integrazione = mic_recorder(start_prompt=f"Rispondi per: {campo_mancante} 🎤", key=f"fix_{campo_mancante}")
        
        if integrazione:
            with st.spinner("Aggiornamento..."):
                audio_fix = io.BytesIO(integrazione['bytes'])
                audio_fix.name = "fix.mp3"
                testo_fix = client.audio.transcriptions.create(model="whisper-1", file=audio_fix, language="it").text
                
                # Aggiorna dati e rimuovi dai mancanti
                st.session_state.data[campo_mancante] = testo_fix
                st.session_state.missing.pop(0)
                st.rerun()

    # FASE 3: RIEPILOGO E SALVATAGGIO
    else:
        st.success("✅ Dati completati! Controlla il riepilogo.")
        
        # --- UI DISPLAY DATI ---
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.data["cliente"] = st.text_input("Cliente", value=st.session_state.data.get("cliente", ""))
            st.session_state.data["contatto"] = st.text_input("Contatto", value=st.session_state.data.get("contatto", ""))
            st.session_state.data["vibes"] = st.text_input("Vibes", value=st.session_state.data.get("vibes", ""))
        with col2:
            opzioni = ["telefonata", "email", "visita"]
            valore_estratto = st.session_state.data.get("tipologia", "telefonata")
            idx = opzioni.index(valore_estratto) if valore_estratto in opzioni else 0
            st.session_state.data["tipologia"] = st.selectbox("Tipologia", opzioni, index=idx)
            st.session_state.data["oggetto"] = st.text_input("Oggetto", value=st.session_state.data.get("oggetto", ""))

        # Campo NOTE grande
        st.session_state.data["note"] = st.text_area("Note Dettagliate", value=st.session_state.data.get("note", ""), height=250)

        # --- LOGICA AUTOPLAY RIASSUNTO ---
        if 'riassunto_fatto' not in st.session_state:
            d = st.session_state.data
            testo_conferma = (
                f"Ottimo lavoro. Ho preparato il riepilogo: "
                f"si tratta di una {d['tipologia']} con il cliente {d['cliente']}. "
                f"L'oggetto è: {d['oggetto']}. "
                f"Nelle note ho inserito che: {d['note']}. "
                f"Se è tutto corretto, premi il tasto per salvare."
            )
            
            with st.spinner("Generazione riassunto vocale..."):
                audio_conferma = speak(testo_conferma)
                if audio_conferma:
                    # L'autoplay=True lo farà partire appena finisce il caricamento
                    st.audio(audio_conferma, format="audio/mp3", autoplay=True)
                    # Segniamo che è stato riprodotto per non farlo ripartire al prossimo refresh
                    st.session_state.riassunto_fatto = True

        st.divider()
        
        # --- PULSANTE DATABASE ---
        if st.button("💾 CARICA EVENTO SUL DATABASE", type="primary"):
            # Qui inseriremo il codice per il tuo DB specifico
            st.balloons()
            st.success("Evento inviato con successo al Database!")
            
            if st.button("Inserisci un altro evento"):
                # Reset completo per ricominciare
                for key in ['data', 'missing', 'riassunto_fatto']:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()
