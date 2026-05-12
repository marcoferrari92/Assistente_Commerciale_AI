import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import io
import json

st.set_page_config(page_title="AI Smart Sales", page_icon="🎙️")

# --- INIZIALIZZAZIONE ---
if 'data' not in st.session_state:
    st.session_state.data = {}
if 'missing' not in st.session_state:
    st.session_state.missing = []

def get_client():
    return OpenAI(api_key=st.sidebar.text_input("OpenAI API Key", type="password"))

def speak(text):
    client = get_client()
    response = client.audio.speech.create(model="tts-1", voice="nova", input=text)
    return response.content

def analyze_report(audio_bytes):
    client = get_client()
    # 1. Trascrizione
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.mp3"
    transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file, language="it")
    
    # 2. Analisi e Check con GPT-4o
    prompt = """
    Analizza il rapporto commerciale e restituisci un JSON. 
    Campi: cliente, tipologia, oggetto, contatto, vibes, note.
    Se un dato manca, scrivi "null" nel valore del campo.
    Aggiungi un campo 'mancanti' che sia una lista dei nomi dei campi non trovati.
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

# --- INTERFACCIA ---
st.title("🎙️ Assistente Vendite Intelligente")

if not st.session_state.data:
    st.info("💡 **Cosa dire:** Cliente, tipo evento, oggetto, con chi hai parlato, vibes e note.")
    
    audio = mic_recorder(start_prompt="Racconta l'evento 🎤", stop_prompt="Analizza ⚙️", key="main_mic")
    
    if audio:
        res = analyze_report(audio['bytes'])
        st.session_state.data = res
        st.session_state.missing = res.get('mancanti', [])
        st.rerun()

# --- GESTIONE DATI MANCANTI ---
elif st.session_state.missing:
    campo_mancante = st.session_state.missing[0]
    messaggio = f"Ho registrato quasi tutto, ma mi manca il campo: {campo_mancante}. Puoi dirmelo?"
    
    # L'AI ti avvisa a voce di cosa manca
    st.warning(f"⚠️ {messaggio}")
    st.audio(speak(messaggio), autoplay=True)
    
    integrazione = mic_recorder(start_prompt=f"Dimmi: {campo_mancante} 🎤", key=f"fix_{campo_mancante}")
    
    if integrazione:
        # Qui potresti fare un'altra mini-trascrizione semplice
        client = get_client()
        audio_fix = io.BytesIO(integrazione['bytes'])
        audio_fix.name = "fix.mp3"
        testo_fix = client.audio.transcriptions.create(model="whisper-1", file=audio_fix, language="it").text
        
        st.session_state.data[campo_mancante] = testo_fix
        st.session_state.missing.pop(0)
        st.rerun()

# --- RIEPILOGO FINALE ---
else:
    st.success("✅ Ottimo! Ho tutti i dati.")
    for k, v in st.session_state.data.items():
        if k != 'mancanti':
            st.text_input(k.capitalize(), value=v)
    
    if st.button("Conferma e Invia"):
        st.balloons()
        st.session_state.data = {} # Reset per il prossimo evento
