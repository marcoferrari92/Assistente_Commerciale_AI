import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import io
import json
from datetime import datetime, time, timedelta

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="AI Smart Sales CRM", page_icon="🎙️", layout="centered")

# --- 2. INIZIALIZZAZIONE STATO GLOBALE ---
if 'form_data' not in st.session_state:
    st.session_state.form_data = {
        "cliente": "",
        "id_cliente_crm": None,       
        "indirizzo": "",  
        "tipologia": "telefonata",
        "oggetto": "",
        "contatto": "",
        "vibes": None,  
        "esito": "", 
        "note": "",
        "next_step": "",        
        "promemoria": None,
        "orario_promemoria": time(9, 0),
        "salva_su_calendario": False, 
        "allegati": []  
    }
if 'campi_mancanti' not in st.session_state:
    st.session_state.campi_mancanti = []

if 'audio_summary_done' not in st.session_state:
    st.session_state.audio_summary_done = False

if 'mic_key_counter' not in st.session_state:
    st.session_state.mic_key_counter = 0

# Inizializzazione stati per la nuova tab di condivisione email
if "email_collega" not in st.session_state:
    st.session_state.email_collega = ""
if "oggetto_email" not in st.session_state:
    st.session_state.oggetto_email = ""
if "messaggio_email_personalizzato" not in st.session_state:
    st.session_state.messaggio_email_personalizzato = ""
if "invia_email_attivo" not in st.session_state:
    st.session_state.invia_email_attivo = False
if 'clienti_suggeriti' not in st.session_state:
    st.session_state.clienti_suggeriti = []


# --- 2.5 COLORAZIONE DINAMICA DELLO SFONDO (CSS INJECTION) ---
# Determina il colore di sfondo in base alle Vibes (tonalità pastello molto tenui)
bg_color = "rgba(0, 0, 0, 0)"  # Sfondo standard trasparente/predefinito
if st.session_state.form_data["vibes"] == "Positivo 👍":
    bg_color = "rgba(46, 204, 113, 0.25)"  # Verde pastello delicatissimo
elif st.session_state.form_data["vibes"] == "Negativo 👎":
    bg_color = "rgba(231, 76, 60, 0.25)"   # Rosso pastello delicatissimo

st.markdown(f"""
    <style>
    .stApp {{
        background-color: {bg_color};
        transition: background-color 0.6s ease-in-out;
    }}
    </style>
""", unsafe_allow_html=True)


# --- 3. FUNZIONI DI SINCRO CON MICROSOFT EXCHANGE (FLUSSO APPLICATIVO DIRETTO) ---

def ottieni_account_exchange():
    """Inizializza l'account O365 in modalità applicativa ed esegue l'autenticazione nativa silenziosa"""
    from O365 import Account
    
    if "microsoft_exchange" not in st.secrets:
        st.error("⚠️ Configurazione 'microsoft_exchange' mancante nei Secrets di Streamlit!")
        return None
        
    credentials = (
        st.secrets["microsoft_exchange"]["client_id"], 
        st.secrets["microsoft_exchange"]["client_secret"]
    )
    tenant_id = st.secrets["microsoft_exchange"]["tenant_id"]
    
    # 1. Inizializziamo l'account dichiarando il flusso di credenziali
    account = Account(credentials, auth_flow_type='credentials', tenant_id=tenant_id)
    
    # 2. Richiediamo il token ad Azure tramite il metodo ufficiale
    try:
        if account.authenticate():
            return account
        else:
            st.error("❌ Autenticazione applicativa fallita. Azure ha rifiutato le credenziali.")
            return None
    except Exception as auth_err:
        st.error(f"❌ Errore durante la stretta di mano con Azure: {auth_err}. Controlla i valori inseriti nei Secrets.")
        return None


def crea_evento_su_exchange(account, user_email, dati_evento):
    """Esegue la creazione dell'evento verificando l'esistenza del calendario con la sintassi corretta O365, timezone e HTML"""
    try:
        schedule = account.schedule(resource=user_email)
        
        try:
            calendars = schedule.list_calendars()
        except Exception as auth_err:
            st.error(f"❌ Errore di autorizzazione Microsoft Graph per {user_email}: {auth_err}. L'app non ha i permessi amministrativi necessari su Azure.")
            return False
            
        if not calendars:
            st.error(f"❌ Errore: Nessun calendario trovato per {user_email}. Verifica che l'utente abbia una licenza Exchange attiva e che i permessi applicativi su Azure abbiano il Consenso dell'Amministratore.")
            return False
            
        calendar = schedule.get_default_calendar()
        
        # 1. CORREZIONE ORARIO (TIMEZONE): Forziamo il fuso orario italiano di Roma
        import zoneinfo
        from datetime import datetime, timedelta
        fuso_locale = zoneinfo.ZoneInfo("Europe/Rome")
        
        start_datetime = datetime.combine(
            dati_evento["promemoria"], 
            dati_evento["orario_promemoria"]
        ).replace(tzinfo=fuso_locale)
        
        end_datetime = start_datetime + timedelta(minutes=30)
        
        # Estraiamo i dati per sicurezza
        cliente = dati_evento.get("cliente", "Cliente non specificato")
        prossimo_step = dati_evento.get("next_step", "Nessun'azione pianificata")
        oggetto = dati_evento.get("oggetto", "Nessun oggetto")
        note_precedenti = dati_evento.get("note", "Nessuna nota inserita")
        
        # Sostituzione degli "a capo" fuori dalla f-string per evitare errori di sintassi
        note_html = note_precedenti.replace("\n", "<br>")
        
        new_event = calendar.new_event()
        
        # TITOLO: Cliente - Prossimo step
        new_event.subject = f"🔔 {cliente} - {prossimo_step}"
        
        # 2. CORREZIONE BODY HTML: Struttura formale completa senza triple virgolette per preservare l'editor
        pezzi_body = [
            "<html>",
            "<body>",
            "<div style='font-family: Arial, sans-serif; font-size: 14px; color: #333333;'>",
            f"🎯 <b>Oggetto:</b> {oggetto}<br><br>",
            f"📝 <b>Note evento precedente:</b><br>{note_html}",
            "</div>",
            "</body>",
            "</html>"
        ]
        corpo_evento_html = "".join(pezzi_body)
        
        # Forziamo il rendering in HTML su Outlook
        new_event.body = corpo_evento_html
        new_event.content_type = 'HTML'
        
        new_event.start = start_datetime
        new_event.end = end_datetime
        
        new_event.save()
        return True
    except IndexError:
        st.error(f"❌ Errore [IndexError]: Il server Microsoft ha risposto con un elenco vuoto. Non ci sono calendari accessibili per {user_email}.")
        return False
    except Exception as e:
        st.error(f"Errore durante l'invio dell'evento a Exchange: {e}")
        return False


def invia_email_collega(account, user_email, user_real_name, email_collega, oggetto_email, dati_evento, messaggio_personalizzato="", file_caricati=None):
    """Invia l'email via Microsoft Graph richiedendo il token in modo nativo e indipendente da O365"""
    import requests
    import base64
    import mimetypes

    try:
        # 1. Recuperiamo le credenziali Azure direttamente dai Secrets di Streamlit
        if "microsoft_exchange" not in st.secrets:
            st.error("⚠️ Configurazione 'microsoft_exchange' mancante nei Secrets!")
            return False
            
        client_id = st.secrets["microsoft_exchange"]["client_id"]
        client_secret = st.secrets["microsoft_exchange"]["client_secret"]
        tenant_id = st.secrets["microsoft_exchange"]["tenant_id"]

        # 2. Richiediamo il Token di accesso direttamente all'endpoint ufficiale di Microsoft
        url_oauth = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        payload_oauth = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default"
        }
        
        risposta_oauth = requests.post(url_oauth, data=payload_oauth)
        if risposta_oauth.status_code != 200:
            st.error(f"❌ Errore autenticazione diretta Azure: {risposta_oauth.text}")
            return False
            
        token_servizio = risposta_oauth.json().get("access_token")

        # 3. Prepariamo l'oggetto dell'e-mail
        subject_finale = oggetto_email if oggetto_email else f"📋 CRM Riepilogo: {dati_evento['cliente']}"

        # 4. Gestione nota commerciale opzionale
        blocco_nota = ""
        if messaggio_personalizzato:
            blocco_nota = (
                "<div style='margin-bottom: 20px; padding: 10px; background-color: #f8f9fa; border-left: 3px solid #7f8c8d;'>"
                f"<p style='margin: 0; font-size: 15px; color: #555555;'><strong>Nota di {user_real_name}:</strong></p>"
                f"<p style='margin: 5px 0 0 0; font-style: italic; color: #2c3e50;'>\"{messaggio_personalizzato}\"</p>"
                "</div>"
                "<hr style='border: 0; border-top: 1px solid #eeeeee; margin: 20px 0;'>"
            )

        # 5. Costruzione del corpo HTML (Senza triple virgolette per l'editor)
        pezzi_html = [
            "<html>",
            "<body>",
            "<div style='font-family: Arial, sans-serif; color: #333333; max-width: 600px; margin: 0 auto; line-height: 1.6;'>",
            f"{blocco_nota}",
            "<p style='margin: 0 0 15px 0; font-size: 15px; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; font-weight: bold;'>Riepilogo Attività</p>",
            f"<p style='margin: 0 0 10px 0; font-size: 16px;'>🏢 <strong>Cliente:</strong> {dati_evento['cliente']}</p>",
            f"<p style='margin: 0 0 20px 0; font-size: 16px;'>🎯 <strong>Oggetto Evento:</strong> {dati_evento['oggetto']}</p>",
            "<div style='margin-top: 20px;'>",
            "<p style='margin: 0 0 8px 0; font-size: 15px; font-weight: bold; color: #2c3e50;'>📝 Note:</p>",
            f"<div style='white-space: pre-line; color: #444444; font-size: 15px;'>{dati_evento['note']}</div>",
            "</div>",
            f"<p style='margin-top: 35px; font-size: 15px; color: #333333;'>Un saluto,<br><strong>{user_real_name}</strong></p>",
            "</div>",
            "</body>",
            "</html>"
        ]
        corpo_html = "".join(pezzi_html)

        # 6. Payload JSON per l'API Microsoft Graph
        email_payload = {
            "message": {
                "subject": subject_finale,
                "body": {
                    "contentType": "HTML",
                    "content": corpo_html
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": email_collega
                        }
                    }
                ],
                "attachments": []
            },
            "saveToSentItems": "true"
        }

        # 7. Elaborazione allegati in Base64
        if file_caricati:
            for file in file_caricati:
                mime_type, _ = mimetypes.guess_type(file.name)
                if not mime_type:
                    mime_type = 'application/octet-stream'

                encoded_content = base64.b64encode(file.getvalue()).decode('utf-8')
                
                allegato_json = {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": file.name,
                    "contentType": mime_type,
                    "contentBytes": encoded_content
                }
                email_payload["message"]["attachments"].append(allegato_json)

        # 8. Spedizione diretta a Microsoft Graph
        url_api = f"https://graph.microsoft.com/v1.0/users/{user_email}/sendMail"
        headers_api = {
            "Authorization": f"Bearer {token_servizio}",
            "Content-Type": "application/json"
        }

        risposta = requests.post(url_api, json=email_payload, headers=headers_api)

        if risposta.status_code == 202:
            return True
        else:
            st.error(f"❌ Errore API Microsoft ({risposta.status_code}): {risposta.text}")
            return False

    except Exception as e:
        st.error(f"Errore durante l'invio dell'email: {e}")
        return False


def trova_clienti_simili_avanzato(nome_dettato, nota_dettata):
    """
    Scarica l'anagrafica completa dall'API ufficiale Imprendo e calcola
    il match ottimale in base a Ragione Sociale e dati geografici.
    """
    import requests
    import difflib
    
    if not nome_dettato:
        return []
        
    # --- CONFIGURAZIONE API UFFICIALE NET-IMPRENDO ---
    url_api = "https://nethimprendo.imprendosrl.com/imprendo/api/imprendo/clienti/lista"
    
    # Recuperiamo il token in modo sicuro dai Secrets di Streamlit
    if "api_imprendo_token" not in st.secrets:
        st.error("⚠️ Token 'api_imprendo_token' mancante nei Secrets di Streamlit!")
        return []
        
    headers = {
        "Authorization": f"Bearer {st.secrets['api_imprendo_token']}"
    }
    
    try:
        # Chiamata GET formale
        risposta = requests.get(url_api, headers=headers, timeout=15)
        
        if risposta.status_code == 200:
            json_risposta = risposta.json()
            
            # Controllo formale dello Status indicato dal tecnico
            if json_risposta.get("Status") == "OK":
                # Estraiamo la lista reale racchiusa nel campo 'Data'
                lista_clienti_db = json_risposta.get("Data", [])
            else:
                st.error(f"❌ L'API ha risposto con Status KO: {json_risposta.get('Data')}")
                return []
        else:
            st.error(f"❌ Errore di connessione API Imprendo (Codice {risposta.status_code})")
            return []
            
        match_con_punteggio = []
        nota_lower = nota_dettata.lower() if nota_dettata else ""

        # --- ALGORITMO DI MATCHING MULTI-CAMPO ---
        for cliente in lista_clienti_db:
            ragione_sociale = cliente.get("ragione_sociale", "")
            indirizzo = cliente.get("indirizzo", "")
            citta = cliente.get("citta", "")
            
            if not ragione_sociale:
                continue
                
            # Calcolo somiglianza testuale sul nome dell'azienda (Valore da 0.0 a 1.0)
            punteggio_nome = difflib.SequenceMatcher(None, nome_dettato.lower(), ragione_sociale.lower()).ratio()
            
            # Algoritmo Geografico basato sull'indirizzo dettato dall'utente
            punteggio_indirizzo = 0.0
            if citta and citta.lower() in nota_lower:
                punteggio_indirizzo += 0.35  # Incremento se l'utente ha nominato la città
            if indirizzo and indirizzo.lower() in nota_lower:
                punteggio_indirizzo += 0.55  # Incremento se l'utente ha nominato la via/indirizzo
                
            punteggio_totale = punteggio_nome + punteggio_indirizzo
            
            # Filtriamo i risultati poco coerenti per tenere solo le corrispondenze reali
            if punteggio_totale > 0.35:
                match_con_punteggio.append({
                    "cliente_info": cliente,
                    "punteggio": punteggio_totale
                })
                
        # Ordina per punteggio decrescente (i più probabili in alto)
        match_con_punteggio.sort(key=lambda x: x["punteggio"], reverse=True)
        
        # Restituiamo i primi 5 match ideali trovati
        return [item["cliente_info"] for item in match_con_punteggio[:5]]

    except Exception as e:
        st.error(f"Errore durante l'elaborazione dell'anagrafica clienti: {e}")
        return []



# --- 4. CONTROLLO ACCESSO MULTI-UTENTE (IMPRENDO MORPHEUS) ---
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
                # CORREZIONE ROBUSTA: se nei secrets manca del tutto il campo "nome", usiamo lo username formattato
                real_name = db_user.get("nome", username.capitalize())
                st.session_state.user_data = {
                    "username": username, 
                    "email": db_user["email"], 
                    "nome": real_name
                }
                st.rerun()
            else:
                st.error("❌ Password errata! Oppure prova a clickare sul campo (a volte si bugga 🫠)")
        else:
            st.error("❌ Utente non trovato!")
    return None

utente_connesso = login_commerciale()

# --- 5. CORE DELL'APPLICAZIONE (Eseguito solo se loggato) ---
if utente_connesso:
    # CORREZIONE AGGIUNTIVA: Fallback di sicurezza anche in fase di rendering sidebar
    nome_visualizzato = utente_connesso.get("nome", utente_connesso.get("username", "Utente").capitalize())
    st.sidebar.write(f"👤 Utente: **{nome_visualizzato}**")
    
    if st.sidebar.button("🚪 Logout"):
        st.session_state.user_data = None
        st.rerun()

    # --- INIZIALIZZAZIONE CLIENT OPENAI ---
    if "openai_key" in st.secrets:
        client = OpenAI(api_key=st.secrets["openai_key"])
    else:
        st.error("⚠️ Chiave API 'openai_key' non trovato nei Secrets!")
        client = None

    # --- FUNZIONI AI ---
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
        
        lista_colleghi_secrets = st.secrets.get("colleghi", [])
        contesto_colleghi = ""
        for index, c in enumerate(lista_colleghi_secrets):
            contesto_colleghi += f"ID: {index} - Nome Completo: {c.get('nome')} (Ufficio: {c.get('ufficio')})\n"
        
        prompt = f"""
        Sei l'assistente di un commerciale che si è appena interfacciato con un cliente tramite una telefonata, una visita o un'email.
        Analizza il suo rapporto e restituisci un JSON.
        I campi sono: cliente, tipologia, oggetto, contatto, vibes, esito, note, next_step, promemoria, orario_promemoria, nota_collega, id_collega_selezionato, oggetto_email.

        REGOLE PER IL CAMPO "cliente"
        - Inserisci il nome del cliente. 
        - Il cliente è diverso dal campo "contatto". Se, ad esempio, dico: "Sono stato da Imprendo e ho parlato con Raffaella", il cliente è "Imprendo". 
        
        REGOLE PER IL CAMPO "contatto"
        - Inserisce nome e cognome e tra parentesi l'ufficio o l'area aziendale del contatto.

        REGOLE CRITICHE PER IL CAMPO 'tipologia':
        - Indica la tipologia dell'evento.
        - Deve essere SOLO uno di questi tre valori: "telefonata", "email", "visita".
        - Se l'utente dice "ho chiamato", "ho fatto una videocall" o "ci siamo sentiti", usa "telefonata".
        - Se l'utente dice "ho scritto" o "mi ha risposto alla mail", usa "email".
        - Se l'utente dice "sono andato", "sono stato" o "abbiamo pranzato insieme" usa "visita".
        - CRITICO: Se non è chiaro, scrivi null.

        REGOLE PER IL CAMPO 'oggetto':
        - Inserisci solo il motivo che ha generato l'evento. 
        - Anche se il commerciale si spiega poco o in modo confuso, crea un riassunto professionale di maximum 10 parole.
        - CRITICO: Se non dice nulla di utile per l'oggetto, scrivi null.

        REGOLE PER IL CAMPO 'vibes':
        - Analizza il tono di voce e le parole del commerciale per capire l'esito dell'evento.
        - Se l'evento è gone bene, c'è interesse, o l'accordo è positivo, scrivi ESATTAMENTE "Positivo 👍".
        - Se ci sono stati problemi, lamentele, esito negativo o chiusura, scrivi ESATTAMENTE "Negativo 👎".
        - CRITICO: Se l'utente non esprime un'opinione chiara, se il tono è neutro o se non riesci a capire l'esito dal racconto, scrivi null. Non inventare o ipotizzare.

        REGOLE PER IL CAMPO "esito"
        - Estrai l'esito finale o lo stato della trattativa emerso dall'evento (es. "preventivo approvato", "interessati", "non interessati a procedere", "da ricontattare per prezzo", "trattativa avviata").
        - Se non è specificato un esito chiaro, scrivi null.

        REGOLE PER LE NOTE:
        - Riassumi l'evento in modo tecnico, preciso ed esaustivo con almeno 20 parole.
        - Inserisci anche le impressioni del commerciale sull'evento.
        
        REGOLE PER IL CAMPO 'next_step':
        - Identifica l'azione futura concordata o pianificata.
        - CRITICO: Se l'utente menziona una data o un orario per questa azione (es. "il 25 Giugno alle 17"), formattali esplicitamente all'interno della stringa stessa del next_step usando la struttura: "[Azione] ([DD/MM/YYYY] ore [HH:MM])" (es. "consegna preventivo al cliente (25/06/2026 ore 17:00)"). 
        - Mantieni come anno di riferimento il 2026 se l'anno è implicito.
        - Se non viene menzionata nessuna azione futura, scrivi null.
        
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

        REGOLE PER IL CAMPO "nota_collega":
        - Se nel testo l'utente dice qualcosa destinato a un collega (es: "scrivi al collega che...", "lascia una nota per il mio collega", "comunica a X che..."), estrai questa informazione e usala per creare un'email formale e gentile per il collega.
        - Non firmare l'email.
        - Se non viene rilevato alcun messaggio esplicito per un collega, scrivi null.

        REGOLE PER IL CAMPO "oggetto_email":
        - Se viene rilevata una nota, una comunicazione o un messaggio per un collega, scrivi un oggetto e-mail formale, chiaro e professionale riassumendo il contenuto.
        - Deve obbligatoriamente includere il nome del cliente (es. "Supporto Amministrativo - [Nome Cliente]" oppure "Segnalazione Tecnica - [Nome Cliente]").
        - Se non c'è nessuna nota per un collega, scrivi null.

        REGOLE PER I CAMPI "id_collega_selezionato":
        - Se l'utente esprime la volontà di contattare, notificare o lasciare una nota a un collega, identifica chi sia incrociando nome e ufficio.
        - Confronta la richiesta con questo elenco ufficiale di colleghi aziendali:
        {contesto_colleghi}
        - Identifica quale ID corrisponde al collega corretto (es: se l'utente dice "Davide dell'ufficio tecnico", assegna l'ID associato a Davide De Meo).
        - Se non trovi un match o non viene menzionato alcun collega, scrivi null.
        - Restituisci SOLO il valore numerico dell'ID (es: 0, 1, 2) o null. Non scrivere stringhe di testo qui.

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
    # Definiamo la funzione per il popup (st.dialog)
    @st.dialog("Scollegati dal Sistema")
    def mostra_popup_matrix():
        st.write(r"""
        *"Matrix è un sistema, Neo. E quel sistema è nostro nemico. Ma quando ci sei dentro ti guardi intorno e cosa vedi? 
        Uomini d'affari, insegnanti, avvocati, falegnami.... le proiezioni mentali della gente che vogliamo salvare. 
        Ma finché non le avremo salvate, queste persone faranno parte di quel sistema, e questo le rende nostre nemiche. 
        Devi capire che la maggior parte di loro non è pronta per essere scollegata. Tanti di loro sono così assuefatti, 
        così disperatamente dipendenti dal sistema, che combatterebbero per difenderlo."*

        Usa le AI con coscienza. La tua creatività è lo strumento più potente.
        """)
        if st.button("Chiudi", use_container_width=True):
            st.rerun()

    # Layout a due colonne per affiancare il Titolo e il Pulsante
    col_pulsante, col_titolo  = st.columns((4, 1), gap="small", vertical_alignment="center")

    with col_pulsante:
        if st.button("🔴", use_container_width=True):
            mostra_popup_matrix()
            
    with col_titolo:
        st.title("Imprendo Morpheus")
        
    st.divider()
    st.write("### Assistente Vocale")
    st.write("")

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
                    
                    # Gestione nota dettata per il collega
                    if "nota_collega" in res and res["nota_collega"]:
                        st.session_state.messaggio_email_personalizzato = res["nota_collega"]
                        st.session_state.invia_email_attivo = True
                        
                    # POPOLAMENTO AUTOMATICO OGGETTO EMAIL
                    if "oggetto_email" in res and res["oggetto_email"]:
                        st.session_state.oggetto_email = res["oggetto_email"]
                    
                    # ASSEGNAZIONE EMAIL USANDO L'ID IDENTIFICATO DALL'AI
                    if "id_collega_selezionato" in res and res["id_collega_selezionato"] is not None:
                        try:
                            idx = int(res["id_collega_selezionato"])
                            lista_colleghi_secrets = st.secrets.get("colleghi", [])
                            if 0 <= idx < len(lista_colleghi_secrets):
                                st.session_state.email_collega = lista_colleghi_secrets[idx].get("email", "")
                        except ValueError:
                            pass

                    # --- CHIAMATA API DI NET-IMPRENDO POST-AUDIO ---
                    cliente_dettato = res.get("cliente", "")
                    note_dettate = res.get("note", "")
                    if cliente_dettato:
                        with st.spinner("Scansione anagrafiche su Net-Imprendo e incrocio indirizzi..."):
                            suggeriti = trova_clienti_simili_avanzato(cliente_dettato, note_dettate)
                            st.session_state.clienti_suggeriti = suggeriti
                            
                            # Se l'API restituisce match, pre-seleziona il primo e salva l'indirizzo
                            if suggeriti:
                                primo_match = suggeriti[0]
                                st.session_state.form_data["cliente"] = primo_match.get("ragione_sociale", "")
                                st.session_state.form_data["id_cliente_crm"] = primo_match.get("id_clienti")
                                
                                ind = primo_match.get("indirizzo", "")
                                cit = primo_match.get("citta", "")
                                prv = primo_match.get("provincia", "")
                                cap = primo_match.get("cap", "")
                                st.session_state.form_data["indirizzo"] = f"{ind} – {cap} {cit} ({prv})".strip(" – ()")
                            else:
                                st.session_state.form_data["indirizzo"] = ""
                    else:
                        st.session_state.clienti_suggeriti = []
                        st.session_state.form_data["indirizzo"] = ""
                    else:
                        st.session_state.clienti_suggeriti = []
                        st.session_state.form_data["indirizzo_completo_crm"] = ""
                    
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
                                        st.session_state.form_data["salva_su_calendario"] = True
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
        nomi_puliti = [
            c.replace("_", " ").capitalize() 
            for c in st.session_state.campi_mancanti 
            if c.lower().strip() != "mancanti" and c != "orario_promemoria" and c != "nota_collega" and c != "id_collega_selezionato" and c != "oggetto_email" and c != "esito"
        ]
        if nomi_puliti:
            st.warning(f"⚠️ **Informazioni incomplete:** L'AI non ha rilevato i seguenti dettagli dal tuo audio: {', '.join(nomi_puliti)}. Per favore, integrali a mano nel modulo sottostante.")

    # Inizializziamo globalmente la variabile per gli allegati in modo che sia accessibile ovunque
    uploaded_files = None

    # --- CREAZIONE DELLE TAB ---
    tab_dati, tab_allegati, tab_condividi = st.tabs(["📝 Evento", "📸 Allegati", "✉️ Condividi"])

    # --- TAB 1: DATI DEL FORM EVENTO ---
    with tab_dati:
        st.write("")
        st.write("### Evento")

        col_r1_1, col_r1_2 = st.columns(2)
        with col_r1_1:
            
            # --- INTERFACCIA SELEZIONE AVANZATA CLIENTE CRM ---
            suggeriti = st.session_state.get("clienti_suggeriti", [])
            cliente_corrente = st.session_state.form_data.get("cliente", "")

            if suggeriti:
                st.warning(f"🔍 Verifica Anagrafica per: **'{cliente_corrente}'**")
                
                elenco_opzioni = []
                for c in suggeriti:
                    label = f"🏢 {c.get('ragione_sociale')} ({c.get('tipo_azienda')})"
                    elenco_opzioni.append(label)
                
                elenco_opzioni.append(f"✨ Forza inserimento come Nuovo: '{cliente_corrente}'")
                elenco_opzioni.append("✍️ Inserisci manualmente un altro nome...")
                
                # Calcoliamo l'indice per mantenere la selezione fissa se l'utente cambia tab
                current_index = 0
                for idx, c in enumerate(suggeriti):
                    if c.get("ragione_sociale") == cliente_corrente:
                        current_index = idx
                        break
                
                scelta = st.selectbox("Corrispondenza rilevata nel CRM Net-Imprendo:", elenco_opzioni, index=current_index)
                
                if scelta == "✍️ Inserisci manualmente un altro nome...":
                    st.session_state.form_data["cliente"] = st.text_input("Ragione Sociale", value="")
                    st.session_state.form_data["indirizzo"] = ""
                elif scelta == f"✨ Forza inserimento come Nuovo: '{cliente_corrente}'":
                    st.session_state.form_data["cliente"] = cliente_corrente
                    st.session_state.form_data["indirizzo"] = ""
                else:
                    idx_sel = elenco_opzioni.index(scelta)
                    cliente_scelto = suggeriti[idx_sel]
                    st.session_state.form_data["cliente"] = cliente_scelto.get("ragione_sociale")
                    st.session_state.form_data["id_cliente_crm"] = cliente_scelto.get("id_clienti")
                    
                    # Salviamo stabilmente l'indirizzo nello stato globale
                    ind = cliente_scelto.get("indirizzo", "")
                    cit = cliente_scelto.get("citta", "")
                    prv = cliente_scelto.get("provincia", "")
                    cap = cliente_scelto.get("cap", "")
                    st.session_state.form_data["indirizzo"] = f"{ind} – {cap} {cit} ({prv})".strip(" – ()")
            else:
                st.session_state.form_data["cliente"] = st.text_input("Cliente", value=cliente_corrente)

            # --- NUOVO CAMPO: INDIRIZZO FISSO E SEMPRE ATTIVO ---
            # Questo campo è visibile fin dall'avvio della pagina e mostra stabilmente l'indirizzo del CRM
            st.text_input(
                "Indirizzo Sede Rilevato", 
                value=st.session_state.form_data.get("indirizzo", ""), 
                disabled=True,
                placeholder="In attesa della selezione del cliente..."
            )

            if suggeriti:
                if st.button("🔄 Disassocia e inserisci a mano", size="small"):
                    st.session_state.clienti_suggeriti = []
                    st.session_state.form_data["indirizzo"] = ""
                    st.session_state.form_data["id_cliente_crm"] = None
                    st.rerun()
            # -----------------------------------------------------------------
            st.session_state.form_data["tipologia"] = st.selectbox("Tipologia", ["telefonata", "email", "visita"], index=["telefonata", "email", "visita"].index(st.session_state.form_data["tipologia"]) if st.session_state.form_data["tipologia"] in ["telefonata", "email", "visita"] else 0)
            st.session_state.form_data["oggetto"] = st.text_input("Oggetto", value=st.session_state.form_data["oggetto"])
            st.session_state.form_data["contatto"] = st.text_input("Contatto", value=st.session_state.form_data["contatto"])
            
            # Sezione Vibes
            st.write("**Vibes (Esito generico):**")
            v_val = st.session_state.form_data["vibes"]
            v_idx = 0 if v_val == "Positivo 👍" else (1 if v_val == "Negativo 👎" else None)
            v_scelta = st.radio(
                "Esito evento", ["Positivo 👍", "Negativo 👎"], 
                index=v_idx, horizontal=True, label_visibility="collapsed"
            )
            st.session_state.form_data["vibes"] = v_scelta
            
            # Nuovo campo Esito posizionato esattamente sotto a Vibes nella prima colonna
            st.session_state.form_data["esito"] = st.text_input(
                "Esito Concreto Trattativa", 
                value=st.session_state.form_data["esito"],
                placeholder="Es. preventivo approvato, non interessati, ecc."
            )

        with col_r1_2:
            st.session_state.form_data["note"] = st.text_area("Note Dettagliate", value=st.session_state.form_data["note"], height=315)

        st.write("")
        st.write("")
        st.write("### Azioni Future & Scadenze")
        
        st.session_state.form_data["next_step"] = st.text_input(
            "Prossimo Step (Data e Ora)", 
            value=st.session_state.form_data["next_step"],
            placeholder="Es. Inviare quotazione economica"
        )
        
        is_calendar_enabled = st.toggle(
            "📅 Attiva Promemoria su Calendario", 
            value=st.session_state.form_data.get("salva_su_calendario", False)
        )
        st.session_state.form_data["salva_su_calendario"] = is_calendar_enabled

        if is_calendar_enabled:
            col_date, col_time = st.columns(2)
            
            with col_date:
                current_date_val = st.session_state.form_data["promemoria"]
                chosen_date = st.date_input(
                    "Data Promemoria", 
                    value=current_date_val if current_date_val else datetime.now().date()
                )
                st.session_state.form_data["promemoria"] = chosen_date
                
            with col_time:
                current_time_val = st.session_state.form_data.get("orario_promemoria", time(9, 0))
                if current_time_val is None:
                    current_time_val = time(9, 0)
                    
                chosen_time = st.time_input("Orario Promemoria", value=current_time_val)
                st.session_state.form_data["orario_promemoria"] = chosen_time

    # --- TAB 2: ALLEGATI ---
    with tab_allegati:
        st.write("")
        st.write("### Allegati")
        st.write("")
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
        st.write("")
        st.write("")

    # --- TAB 3: CONDIVISIONE EMAIL ---
    with tab_condividi:
        st.write("")
        st.write("### Condividi Evento via Email")
        st.caption("Inoltra l'evento a un collega per richiedere valutazione tecniche o informazioni commerciali.")
        
        st.session_state.email_collega = st.text_input(
            "Email", 
            value=st.session_state.email_collega,
            placeholder="esempio@azienda.com"
        )
        
        # BOX DI INPUT AUTOPRECOMPILATO PER L'OGGETTO EMAIL
        st.session_state.oggetto_email = st.text_input(
            "Oggetto Email",
            value=st.session_state.oggetto_email,
            placeholder="Es. Segnalazione attività commerciale"
        )
        
        st.session_state.messaggio_email_personalizzato = st.text_area(
            "Aggiungi un messaggio (Opzionale)",
            value=st.session_state.messaggio_email_personalizzato,
            placeholder="Es. Ciao, ti giro questo report perché il cliente ha chiesto informazioni sulla tua area di competenza...",
            height=300
        )
        
        st.session_state.invia_email_attivo = st.toggle(
            "✉️ Invia email automaticamente quando premi 'SALVA EVENTO'", 
            value=st.session_state.invia_email_attivo
        )
        st.write("")
        st.write("")

    # --- 6. RIASSUNTO VOCALE DI CONFERMA ---
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
            - Esito Concreto: {d['esito'] if d['esito'] else 'non specificato'}
            - Note e dettagli rilevanti: {d['note']}
            - Prossimo Step: {d['next_step'] if d['next_step'] else 'nessuno'}
            - Data Promemoria: {promemoria_str}
            - Orario Rilevato per Calendario: {orario_str}
            - Nota rilevata da inviare al collega: {st.session_state.messaggio_email_personalizzato if st.session_state.messaggio_email_personalizzato else 'nessuna'}
            
            REGOLE DI TONO E STRUTTURA:
            - Non fare un elenco della spesa. Il discorso deve essere fluido e continuo.
            - Specifica subito la tipologia di evento e con chi hai parlato.
            - Se l'esito è "Positivo 👍", usa un tono soddisfatto. Se è "Negativo 👎", usa un tono pragmatico.
            - Riassumi brevemente il fulcro delle note e l'esito concreto della trattativa.
            - COMUNICA L'ORARIO: Nel riassunto, specifica l'orario esatto che hai assegnato per il calendario (es. "...e ho impostato il promemoria per il {promemoria_str} alle ore {orario_str}"). Rendi la frase naturale.
            - SE C'È UNA NOTA PER IL COLLEGA: Includi nel discorso che hai rilevato e salvato anche il messaggio specifico da inviare via mail al collega (es. "...e ho preparato la nota per il tuo collega").
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
        
        calendario_ok = False
        email_ok = False
        
        # Inizializzazione istantanea dell'account token tramite credenziali dei Secrets
        account_aziendale = ottieni_account_exchange()
        
        if account_aziendale:
            # --- BLOCCO DI SINCRO CON MICROSOFT EXCHANGE ---
            if st.session_state.form_data["salva_su_calendario"]:
                with st.spinner("Sincronizzazione appuntamento su Outlook in corso..."):
                    calendario_ok = crea_evento_su_exchange(
                        account=account_aziendale,
                        user_email=utente_connesso["email"],
                        dati_evento=st.session_state.form_data
                    )
                    
            # --- BLOCCO INVIO EMAIL DI CONDIVISIONE ---
            if st.session_state.get("invia_email_attivo", False) and st.session_state.get("email_collega", ""):
                destinatario_notifica = st.session_state.email_collega
                with st.spinner(f"Invio riepilogo email a {destinatario_notifica}..."):
                    email_ok = invia_email_collega(
                        account=account_aziendale,
                        user_email=utente_connesso["email"],
                        user_real_name=utente_connesso["nome"], 
                        email_collega=st.session_state.email_collega,
                        oggetto_email=st.session_state.oggetto_email, 
                        dati_evento=st.session_state.form_data,
                        messaggio_personalizzato=st.session_state.messaggio_email_personalizzato,
                        file_caricati=uploaded_files
                    )
        else:
            st.error("❌ Impossibile stabilire una connessione sicura con l'infrastruttura Microsoft Exchange.")

        # --- ELABORAZIONE DATI FINALI ---
        final_data = st.session_state.form_data.copy()
        if final_data["promemoria"]:
            final_data["promemoria"] = final_data["promemoria"].strftime("%Y-%m-%d")
            
        if final_data["orario_promemoria"]:
            final_data["orario_promemoria"] = final_data["orario_promemoria"].strftime("%H:%M")
            
        st.session_state.campi_mancanti = []
        
        # --- BANNER DI CONFERMA STABILI ---
        st.success("✅ Evento registrato correttamente nel database aziendale!")
        
        if st.session_state.form_data["salva_su_calendario"]:
            if calendario_ok:
                st.success("📅 Appuntamento inserito nel tuo calendario di Outlook!")
            else:
                st.error("❌ Sincronizzazione calendario fallita per un problema di autorizzazione.")
            
        if st.session_state.get("invia_email_attivo", False) and st.session_state.get("email_collega", ""):
            if email_ok:
                st.success(f"📧 Email inviata con successo a {destinatario_notifica} e registrata nella posta inviata!")
            else:
                st.error("❌ Spedizione e-mail fallita. Verifica le restrizioni sul Tenant di Azure.")
            
        st.write("Dati inviati:", final_data)
