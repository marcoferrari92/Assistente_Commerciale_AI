import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import io
import json

st.set_page_config(page_title="AI Smart Sales CRM", page_icon="🎙️", layout="centered")

# --- 1. INIZIALIZZAZIONE STATO ---
# Inizializziamo i campi se non esistono, così sono pronti per la compilazione manuale
if 'form_data' not in st.session_state:
    st.session_state.form_data = {
        "cliente": "",
        "tipologia": "telefonata",
        "oggetto": "",
        "contatto": "",
        "vibes": "Positive 👍",
        "note": ""
    }
if 'audio_summary_done' not in st.session_state:
    st.session_state.audio_summary_done = False

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("Configurazione")
    api_key = st.text_input("OpenAI API Key", type="password", key="main_api_key")
    if st.button("🗑️ Svuota Modulo"):
        st.session_state.form_data = {k: "" if k != "tipologia" else "telefonata" for k in st.session_state.form_data}
        st.session_state.form_data["vibes"] = "Positive 👍"
        st.session_state.audio_summary_done = False
        st.rerun()

client = OpenAI(api_key=api_key) if api_key else None

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

# SEZIONE ASSISTENTE VOCALE (Sempre disponibile in alto)
st.write("### 🎤 Assistente Rapido")
if not api_key:
    st.warning("Inserisci l'API Key per usare la voce.")
else:
    audio = mic_recorder(start_prompt="Racconta l'evento per compilare il modulo 🎤", 
                         stop_prompt="Elabora racconto ✨", key="main_mic")
    if audio:
        with st.spinner("L'AI sta compilando il modulo per te..."):
            res = analyze_full_report(audio['bytes'])
            if res:
                # Aggiorniamo lo stato con i dati dell'AI
                for k in st.session_state.form_data.keys():
                    if k in res and res[k]: st.session_state.form_data[k] = res[k]
                st.session_state.audio_summary_done = False # Resetta per far parlare l'AI col nuovo riassunto
                st.rerun()

st.divider()

# --- 5. IL MODULO (Sempre presente e modificabile a mano) ---
st.write("### 📝 Modulo Evento")

col1, col2 = st.columns(2)
with col1:
    st.session_state.form_data["cliente"] = st.text_input("Cliente", value=st.session_state.form_data["cliente"])
    st.session_state.form_data["contatto"] = st.text_input("Contatto", value=st.session_state.form_data["contatto"])
    
    st.write("**Esito (Vibes):**")
    v_idx = 0 if "Positive" in st.session_state.form_data["vibes"] else 1
    st.session_state.form_data["vibes"] = st.radio("Vibes", ["Positive 👍", "Negative 👎"], 
                                                  index=v_idx, horizontal=True, label_visibility="collapsed")

with col2:
    t_options = ["telefonata", "email", "visita"]
    t_val = st.session_state.form_data["tipologia"]
    t_idx = t_options.index(t_val) if t_val in t_options else 0
    st.session_state.form_data["tipologia"] = st.selectbox("Tipologia", t_options, index=t_idx)
    
    st.session_state.form_data["oggetto"] = st.text_input("Oggetto", value=st.session_state.form_data["oggetto"])

st.session_state.form_data["note"] = st.text_area("Note Dettagliate", value=st.session_state.form_data["note"], height=200)

# --- 6. RIASSUNTO VOCALE DI CONFERMA (Solo se compilato tramite AI o su richiesta) ---
if st.session_state.form_data["note"] != "" and not st.session_state.audio_summary_done:
    d = st.session_state.form_data
    testo = f"Ho compilato il modulo. Cliente: {d['cliente']}, Oggetto: {d['oggetto']}. Vibes: {d['vibes']}. Confermi il caricamento?"
    audio_msg = speak(testo)
    if audio_msg:
        st.audio(audio_msg, autoplay=True)
        st.session_state.audio_summary_done = True

# --- 7. SALVATAGGIO ---
st.divider()
if st.button("💾 SALVA EVENTO SUL DATABASE", type="primary", use_container_width=True):
    # QUI inserisci il codice per il database
    st.balloons()
    st.success("Evento registrato correttamente!")
    st.write("Dati inviati:", st.session_state.form_data)
