import streamlit as st
import pandas as pd
import json

@st.cache_data
def carica_ordini(file):
    try:
        # 1. Lettura del file JSON
        # Carica il file come dizionario Python
        dati_json = json.load(file)
        
        righe_appiattite = []
        
        # 2. Parsing e appiattimento della struttura annidata
        for id_doc, doc in dati_json.items():
            info_principali = {
                'ID DOCUMENTO': doc.get('id_documenti'),
                'ID DOCUMENTO PADRE': doc.get('id_documento_padre'),
                'DATA': doc.get('data'),
                'CODICE GESTIONALE UTENTE': doc.get('id_utenti'),
                'CLIENTE': doc.get('ragione_sociale'),
                'TIPOLOGIA DOC.': doc.get('tipo_documento'),
                'TITOLO': doc.get('titolo') # Evita KeyError nel boxplot customdata
            }
            
            # Estrazione delle righe degli articoli all'interno del documento
            righe_doc = doc.get('righe', {})
            if isinstance(righe_doc, dict) and righe_doc:
                for id_riga, riga in righe_doc.items():
                    # Unisce i dati del documento con quelli della singola riga
                    dati_riga = info_principali.copy()
                    dati_riga.update({
                        'CODICE ARTICOLO': riga.get('codice'),
                        'PREZZO': riga.get('prezzo'),
                        'QT': riga.get('quantita')
                    })
                    righe_appiattite.append(dati_riga)
            else:
                # Se un documento non ha righe inserisce comunque le info principali
                dati_riga = info_principali.copy()
                dati_riga.update({
                    'CODICE ARTICOLO': None,
                    'PREZZO': None,
                    'QT': None
                })
                righe_appiattite.append(dati_riga)

        # Creazione del DataFrame
        df = pd.DataFrame(righe_appiattite)

        # 3. Controllo colonne obbligatorie (adattato alla nuova logica)
        colonne_necessarie = ['DATA', 'ID DOCUMENTO', 'CODICE GESTIONALE UTENTE', 'CLIENTE', 'TIPOLOGIA DOC.', 'CODICE ARTICOLO', 'PREZZO', 'QT']
        mancanti = [c for c in colonne_necessarie if c not in df.columns]
        if mancanti:
            st.error(f"Mancano colonne fondamentali nella conversione: {mancanti}")
            return None

        # 4. Gestione specifica della DATA
        # Il formato nel JSON è "GG/MM/AAAA" (es. 20/05/2026), pd.to_datetime con dayfirst=True lo gestisce correttamente
        df['DATA'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce')
        righe_nulle = df['DATA'].isna().sum()
        df = df.dropna(subset=['DATA'])
        
        if righe_nulle > 0:
            st.warning(f"⚠️ Rimosse {righe_nulle} righe con DATA non valida.")

        # 5. Pulizia e conversione opzionale dei dati numerici (Prezzo e Quantità nel JSON sono stringhe con la virgola)
        if 'PREZZO' in df.columns:
            df['PREZZO'] = df['PREZZO'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df['PREZZO'] = pd.to_numeric(df['PREZZO'], errors='coerce')
            
        if 'QT' in df.columns:
            df['QT'] = pd.to_numeric(df['QT'], errors='coerce')

        return df

    except Exception as e:
        st.error(f"Errore critico caricamento JSON: {e}")
        return None
