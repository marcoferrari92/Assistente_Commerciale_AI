import streamlit as st
import pandas as pd
import re

def validazione_importi(df):
    if df is None or df.empty:
        st.error("DataFrame assente o vuoto!")
        return None, None

    df = df.copy()

    # Convertiamo i valori stringa del JSON (es. 900,00) in float Python standard
    def converti_valore(val):
        try:
            if pd.isna(val): return 0.0
            val_str = str(val).strip().replace(' ', '')
            if '.' in val_str and ',' in val_str:
                val_str = val_str.replace('.', '').replace(',', '.')
            elif ',' in val_str:
                val_str = val_str.replace(',', '.')
            pulito = re.sub(r'[^0-9.-]', '', val_str)
            return float(pulito) if pulito else 0.0
        except:
            return 0.0

    # Puliamo e convertiamo QT e PREZZO per calcolare il totale di riga
    df['QT_pulito'] = df['QT'].apply(converti_valore)
    df['PREZZO_pulito'] = df['PREZZO'].apply(converti_valore)
    
    # Calcolo totale della riga corrente
    df['TOTALE_RIGA'] = df['PREZZO_pulito'] * df['QT_pulito']

    # Raggruppiamo immediatamente per ID DOCUMENTO
    df_doc = df.groupby('ID DOCUMENTO').agg({
        'ID DOCUMENTO PADRE': 'first',
        'DATA': 'first',
        'CODICE GESTIONALE UTENTE': 'first',
        'CLIENTE': 'first',
        'TIPOLOGIA DOC.': 'first',
        'TITOLO': 'first',
        'QT_pulito': 'sum',
        'TOTALE_RIGA': 'sum'
    }).reset_index()

    df_doc.rename(columns={'QT_pulito': 'QT', 'TOTALE_RIGA': 'TOTALE'}, inplace=True)

    # --- OTTIMIZZAZIONE: Standardizziamo la colonna in MAIUSCOLO per tutto il resto dell'app ---
    df_doc['TIPOLOGIA DOC.'] = df_doc['TIPOLOGIA DOC.'].astype(str).str.upper().str.strip()

    # Validazione del Tipo Documento
    tipi_ammessi = ["PREVENTIVO", "ORDINE APERTO", "ORDINE"]
    mask_tipo_errato = ~df_doc['TIPOLOGIA DOC.'].isin(tipi_ammessi)

    # Maschera errori sul totale documento
    mask_errori = (df_doc['TOTALE'] <= 0) | (df_doc['TOTALE'].isna()) | mask_tipo_errato

    df_errori = df_doc[mask_errori].copy()
    df_pulito = df_doc[~mask_errori].copy()

    st.write(f"✅ File elaborato: {len(df_doc)} documenti univoci rilevati.")
    if len(df_errori) > 0:
        with st.expander("⚠️ ERRORI RILEVATI SUI DOCUMENTI", expanded=False):
            st.error(f"Trovati {len(df_errori)} documenti scartati (Importo non valido o Tipo non ammesso)!")
            st.dataframe(df_errori)

    return df_pulito, df_errori
