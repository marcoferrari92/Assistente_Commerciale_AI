import streamlit as st
import pandas as pd


@st.cache_data
def carica_eventi(file):
    try:
        # 1. Lettura file con gestione separatore
        df = pd.read_csv(file, sep=';', encoding='utf-8-sig')
        if df.shape[1] <= 1:
            file.seek(0)
            df = pd.read_csv(file, sep=',', encoding='utf-8-sig')

        # 2. Pulizia preliminare spazi e caratteri invisibili (BOM)
        df.columns = df.columns.str.strip().str.replace('ï»¿', '', regex=False)
        
        # Rinominiamo 'Data Evento' in 'DATA' per le tue funzioni di filtraggio
        if 'Data Evento' in df.columns:
            df = df.rename(columns={'Data Evento': 'DATA'})
        
        # Trasformiamo TUTTI i nomi delle colonne in maiuscolo
        df.columns = [c.upper() for c in df.columns]

        # 4. Controllo colonne obbligatorie (Tutte tranne CAMPAGNA)
        colonne_necessarie = [
            'TIPO ANAGRAFICA', 'ID CLIENTI', 'RAGIONE SOCIALE', 
            'DATA', 'ORA EVENTO', 'TIPO EVENTO', 'UTENTE', 'NOTE'
        ]
        
        mancanti = [c for c in colonne_necessarie if c not in df.columns]
        
        if mancanti:
            st.error(f"⚠️ Errore: Il file non contiene tutte le colonne necessarie.")
            st.info(f"Colonne mancanti: {mancanti}")
            return None

        # 5. Gestione specifica della DATA e mostruizzazione errori
        # Salviamo le date originali come testo per poterle mostrare in caso di errore
        date_originali = df['DATA'].astype(str)
        
        # Tentiamo la conversione
        df['DATA'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce')
        
        # Creiamo una maschera per trovare dove la conversione è fallita (o era già vuota)
        righe_non_valide_mask = df['DATA'].isna()
        righe_nulle = righe_non_valide_mask.sum()
        
        if righe_nulle > 0:
            # Isoliamo le righe corrotte
            df_errori = df[righe_non_valide_mask].copy()
            # Ripristiniamo la data originale (stringa) solo per il report visivo
            df_errori['DATA'] = date_originali[righe_non_valide_mask]
            
            # Mostriamo l'avviso e la tabella espandibile su Streamlit
            st.warning(f"⚠️ Rimosse {righe_nulle} righe con DATA non valida o vuota.")
            with st.expander("🔍 Clicca qui per vedere le righe scartate"):
                st.dataframe(df_errori, use_container_width=True)
            
            # Procediamo a ripulire il DataFrame principale dalle righe non valide
            df = df.dropna(subset=['DATA'])

        # 6. Pulizia testi (Maiuscolo e rimozione spazi)
        colonne_testo = ['UTENTE', 'TIPO EVENTO', 'TIPO ANAGRAFICA', 'RAGIONE SOCIALE']
        for col in colonne_testo:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip()

        return df

    except Exception as e:
        st.error(f"❌ Errore critico nel caricamento: {e}")
        return None
