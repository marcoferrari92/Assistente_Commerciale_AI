import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import io

st.set_page_config(page_title="Voice Sales Assistant", page_icon="🎙️")

# --- BARRA LATERALE E CONFIGURAZIONE ---
with st.sidebar:
    api_key = st.text_input("OpenAI API Key", type="password")
    if st.button("Riavvia Procedura"):
        st.session_state.step = 0
        st.session_state.form_data = {}
        st.rerun()

# --- INIZIALIZZAZIONE STATO ---
if 'step' not in st.session_state:
    st.session_state.step = 0
    st.session_state.form_data = {}

steps = [
    {"campo": "cliente", "domanda": "Con quale cliente hai parlato?"},
    {"campo": "tipologia", "domanda": "Che tipo di evento è stato? Ad esempio telefonata o visita."},
    {"campo": "oggetto", "domanda": "Qual era l'oggetto principale dell'incontro?"},
    {"campo": "contatto", "domanda": "Con chi hai parlato nello specifico?"},
    {"campo": "vibes", "domanda": "Com'è andata? Dammi un feedback positivo o negativo."},
    {"campo": "note", "domanda": "Ci sono note aggiuntive che vuoi registrare?"}
]

# --- FUNZIONI OPENAI ---
def speak_question(text, key):
    client = OpenAI(api_key=key)
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy", # Puoi provare anche 'nova' o 'shimmer' per voci diverse
        input=text
    )
    return response.content

def transcribe_audio(audio_bytes, key):
    client = OpenAI(api_key=key)
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.mp3"
    transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return transcript.text

# --- INTERFACCIA PRINCIPALE ---
st.title("🎙️ Sales Voice Assistant")

if not api_key:
    st.warning("Inserisci l'API Key per iniziare.")
else:
    if st.session_state.step < len(steps):
        current = steps[st.session_state.step]
        
        # 1. L'AI PARLA (Genera e riproduce l'audio della domanda)
        with st.spinner("L'assistente sta parlando..."):
            audio_domanda = speak_question(current['domanda'], api_key)
            st.audio(audio_domanda, format="audio/mp3", autoplay=True)
        
        st.subheader(f"Step {st.session_state.step + 1}: {current['campo'].capitalize()}")
        st.info(current['domanda'])

        # 2. L'UTENTE RISPONDE (Registrazione)
        audio_risposta = mic_recorder(
            start_prompt="Rispondi a voce 🎤",
            stop_prompt="Stop ⏹️",
            key=f"mic_{st.session_state.step}"
        )

        if audio_risposta:
            with st.spinner("Trascrizione in corso..."):
                testo_risposta = transcribe_audio(audio_risposta['bytes'], api_key)
                st.chat_message("user").write(testo_risposta)
                
                if st.button("Conferma e Prosegui ➡️"):
                    st.session_state.form_data[current['campo']] = testo_risposta
                    st.session_state.step += 1
                    st.rerun()
    else:
        st.success("✅ Procedura completata!")
        st.json(st.session_state.form_data)
