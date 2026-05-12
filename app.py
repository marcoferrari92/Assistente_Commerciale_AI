import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import io

st.set_page_config(page_title="AI Sales Assistant", page_icon="🎙️")

# --- CSS per nascondere elementi inutili e migliorare UI ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 20px; height: 3em; background-color: #FF4B4B; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- INIZIALIZZAZIONE ---
if 'step' not in st.session_state:
    st.session_state.step = 0
    st.session_state.form_data = {}
    st.session_state.active = False # L'app parte "ferma"

with st.sidebar:
    api_key = st.text_input("OpenAI API Key", type="password")
    if st.button("🔄 Reset Assistente"):
        st.session_state.step = 0
        st.session_state.form_data = {}
        st.session_state.active = False
        st.rerun()

steps = [
    {"campo": "cliente", "domanda": "Con quale cliente hai parlato?"},
    {"campo": "tipologia", "domanda": "È stata una telefonata, una mail o una visita?"},
    {"campo": "oggetto", "domanda": "Qual era l'oggetto dell'evento?"},
    {"campo": "contatto", "domanda": "Con chi hai parlato?"},
    {"campo": "vibes", "domanda": "Com'è andata? È stata positiva o negativa?"},
    {"campo": "note", "domanda": "Dettagli o note aggiuntive?"}
]

def speak(text):
    client = OpenAI(api_key=api_key)
    response = client.audio.speech.create(model="tts-1", voice="nova", input=text)
    return response.content

def transcribe(audio_bytes):
    client = OpenAI(api_key=api_key)
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.mp3"
    transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return transcript.text

# --- FLUSSO PRINCIPALE ---
st.title("🎙️ Assistente Vocale Commerciali")

if not api_key:
    st.warning("Inserisci l'API Key per iniziare.")
elif not st.session_state.active:
    # PULSANTE DI AVVIO UNICO
    if st.button("🚀 INIZIA PROCEDURA GUIDATA"):
        st.session_state.active = True
        st.rerun()
else:
    if st.session_state.step < len(steps):
        current = steps[st.session_state.step]
        
        # 1. L'AI fa la domanda
        st.subheader(f"Step {st.session_state.step + 1} di {len(steps)}")
        audio_q = speak(current['domanda'])
        st.audio(audio_q, format="audio/mp3", autoplay=True)
        st.info(f"🎤 **AI dice:** {current['domanda']}")

        # 2. Registratore - Qui l'utente parla
        # Il trucco: usiamo il componente mic_recorder. 
        # Appena riceve l'audio, il codice sotto viene eseguito.
        audio_input = mic_recorder(
            start_prompt="Clicca e parla (si ferma da solo)",
            stop_prompt="In elaborazione...",
            key=f"mic_{st.session_state.step}",
            just_once=True, # Importante per evitare loop infiniti
        )

        if audio_input:
            with st.spinner("Trascrizione..."):
                testo = transcribe(audio_input['bytes'])
                # Salvataggio immediato
                st.session_state.form_data[current['campo']] = testo
                # Avanzamento automatico allo step successivo
                st.session_state.step += 1
                st.rerun() 
    else:
        st.balloons()
        st.success("✅ Procedura completata! Ecco i dati raccolti:")
        st.write(st.session_state.form_data)
        
        # Logica di salvataggio finale
        if st.button("💾 Salva definitivamente"):
            # Aggiungi qui la tua logica (DB, CSV, Google Sheets)
            st.write("Dati inviati al database!")
