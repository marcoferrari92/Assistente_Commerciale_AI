import streamlit as st
import pandas as pd
import plotly.express as px

def colora_stato(val):
    """Funzione di utilità interna per colorare il testo nella tabella Streamlit"""
    colori = {
        "AGGIUDICATO (CHIUSO)": "color: #4E944F; font-weight: bold;",
        "AGGIUDICATO (APERTO)": "color: #B4E197; font-weight: bold;",
        "IN SCADENZA": "color: #CCAA00; font-weight: bold;",
        "IN ATTESA": "color: #007BFF;",
        "PERSO": "color: #FF4B4B;"
    }
    return colori.get(val, "color: black;")

def analisi_conversione_preventivi(df, finestra, giorni_scadenza=7):
    # --- 1. SEPARAZIONE DATAFRAME ---
    # Gestiamo il case-insensitive convertendo preventivamente in maiuscolo
    df_upper = df.copy()
    df_upper['TIPOLOGIA DOC.'] = df_upper['TIPOLOGIA DOC.'].astype(str).str.upper()

    preventivi = df_upper[df_upper['TIPOLOGIA DOC.'] == "PREVENTIVO"].copy()
    ordini     = df_upper[df_upper['TIPOLOGIA DOC.'].isin(["ORDINE", "ORDINE APERTO"])].copy()

    if preventivi.empty:
        st.warning("⚠️ Nessun PREVENTIVO trovato!")
        return None

    DATA_riferimento = pd.Timestamp.now().normalize()

    # Raggruppamento per calcolare i totali complessivi di ogni documento
    totali_database = df.groupby(['ID DOCUMENTO', 'TIPOLOGIA DOC.']).agg({
        'TOTALE': 'sum',
        'QT': 'sum'
    }).reset_index()

    # --- 2. MATCHING BASATO SU ID PADRE (JSON-FRIENDLY) ---
    # Uniamo l'ID DOCUMENTO del preventivo con l'ID DOCUMENTO PADRE dell'ordine collegato
    merged = pd.merge(
        preventivi,
        ordini[['ID DOCUMENTO PADRE', 'ID DOCUMENTO', 'DATA', 'TIPOLOGIA DOC.', 'QT', 'TOTALE']], 
        left_on='ID DOCUMENTO',
        right_on='ID DOCUMENTO PADRE',
        how='left',
        suffixes=('_prev', '_ord')
    )
    
    merged['diff_giorni'] = (pd.to_datetime(merged['DATA_ord']) - pd.to_datetime(merged['DATA_prev'])).dt.days

    # --- 3. DEFINIZIONE STATO E LOGICA "INFO" ---
    def definisci_stato_documento(group):
        
        ordini_collegati     = group.dropna(subset=['ID DOCUMENTO_ord'])
        valore_prev_totale   = group['TOTALE_prev'].iloc[0]
        qta_prev_totale      = group['QT_prev'].iloc[0]

        if not ordini_collegati.empty:
            id_ordini_collegati = ordini_collegati['ID DOCUMENTO_ord'].unique()
            
            info_ordini = totali_database[totali_database['ID DOCUMENTO'].isin(id_ordini_collegati)]
            totale_economico_ord = info_ordini['TOTALE'].sum()
            qta_totale_ord = info_ordini['QT'].sum()

            note = []
            if totale_economico_ord < (valore_prev_totale - 0.01):
                note.append("RIDOTTO")
            elif totale_economico_ord > (valore_prev_totale + 0.01):
                note.append("EXTRA")
            
            if len(id_ordini_collegati) > 1:
                note.append("MULTI-TRANCHE")

            info_text = " + ".join(note) if note else "INTEGRALE"
            
            id_ordine_display = ", ".join(id_ordini_collegati.astype(str))
            ultimo_match = ordini_collegati.sort_values('DATA_ord', ascending=False).iloc[0]
            stato = "AGGIUDICATO (CHIUSO)" if str(ultimo_match['TIPOLOGIA DOC._ord']).upper() == "ORDINE" else "AGGIUDICATO (APERTO)"
            
            return pd.Series([
                stato, ultimo_match['diff_giorni'], id_ordine_display,
                totale_economico_ord, qta_totale_ord, ultimo_match['DATA_ord'], info_text
            ])
        
        return pd.Series([None, None, None, 0.0, 0, pd.NaT, "NESSUN ORDINE"])

    risultati = merged.groupby('ID DOCUMENTO_prev', group_keys=False).apply(definisci_stato_documento).reset_index()
    risultati.columns = ['ID PREVENTIVO_KEY', 'STATO_DETTAGLIO', 'DURATA', 'ID ORDINE', 'TOTALE ORDINE', 'NUM ART ORD', 'DATA ORDINE', 'INFO']

    # --- 4. CREAZIONE REPORT FINALE ---
    report_prev = preventivi.copy()
    report_prev = pd.merge(report_prev, risultati, left_on='ID DOCUMENTO', right_on='ID PREVENTIVO_KEY', how='left')

    # --- 5. ASSEGNAZIONE STATI TEMPORALI ---
    def elabora_dati_finali(row):
        giorni_passati = (DATA_riferimento - pd.to_datetime(row['DATA'])).days
        
        if pd.notna(row['ID ORDINE']):
            return pd.Series([row['STATO_DETTAGLIO'], row['DURATA'], row['INFO']])
        
        if giorni_passati > finestra:
            return pd.Series(["PERSO", giorni_passati, "SCADUTO"])
        elif (finestra - giorni_passati) <= giorni_scadenza:
            return pd.Series(["IN SCADENZA", giorni_passati, "SOLLECITARE"])
        else:
            return pd.Series(["IN ATTESA", giorni_passati, "IN CORSO"])

    report_prev[['STATO_FINALE', 'DURATA', 'INFO']] = report_prev.apply(elabora_dati_finali, axis=1)

    # --- VISUALIZZAZIONE GRAFICI ---   
    color_map_stato = {
        "AGGIUDICATO (CHIUSO)": "#4E944F",
        "AGGIUDICATO (APERTO)": "#B4E197",
        "IN SCADENZA": "#FFD700",
        "IN ATTESA": "#A2D2FF",
        "PERSO": "#FF9999"
    }

    r1_c1, r1_c2 = st.columns(2)
    with r1_c1:
        stats_n = report_prev['STATO_FINALE'].value_counts().reset_index()
        fig_pie_n = px.pie(stats_n, values='count', names='STATO_FINALE', 
                           title="Esito per Numero Documenti", hole=0.4, 
                           color='STATO_FINALE', color_discrete_map=color_map_stato)
        fig_pie_n.update_traces(textinfo='value+percent', texttemplate='%{value}<br><b>%{percent}<b>')
        fig_pie_n.update_layout(
            title={'text': "Esito per Numero Documenti", 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'},
            legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig_pie_n, use_container_width=True)
        
    with r1_c2:
        stats_val = report_prev.groupby('STATO_FINALE')['TOTALE'].sum().reset_index()
        fig_pie_val = px.pie(stats_val, values='TOTALE', names='STATO_FINALE', 
                             title="Esito per Valore Economico (€)", hole=0.4, 
                             color='STATO_FINALE', color_discrete_map=color_map_stato)
        fig_pie_val.update_traces(textinfo='value+percent', texttemplate='€%{value:,.2f}<br><b>%{percent}<b>')
        fig_pie_val.update_layout(
            title={'text': "Esito per Valore Economico (€)", 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'},
            legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig_pie_val, use_container_width=True)

    # --- REGISTRO FINALE ---
    st.write("")
    st.write("")
    
    df_display = report_prev[[
        'DATA', 'DATA ORDINE', 'DURATA', 'STATO_FINALE', 'INFO', 
        'CLIENTE', 'CODICE GESTIONALE UTENTE', 'QT', 'NUM ART ORD', 'TOTALE', 'TOTALE ORDINE',
        'ID DOCUMENTO', 'ID ORDINE'
    ]].copy()

    df_display.columns = [
        'Data Prev.', 'Data Ord.', 'Durata', 'Stato', 'Info', 
        'Cliente', 'Utente', 'Q.tà Prev.', 'Q.tà Ord.', 'Tot. Prev.', 'Tot. Ord.', 
        'ID Prev.', 'ID Ord.'
    ]

    ordine_stati = ["IN SCADENZA", "IN ATTESA", "AGGIUDICATO (APERTO)", "AGGIUDICATO (CHIUSO)", "PERSO"]
    df_display['Stato'] = pd.Categorical(df_display['Stato'], categories=ordine_stati, ordered=True)

    st.dataframe(
        df_display.sort_values(by=['Stato', 'Data Prev.'], ascending=[True, False]).style.format({
            'Data Prev.': lambda x: pd.to_datetime(x).strftime('%d/%m/%Y'),
            'Data Ord.': lambda x: pd.to_datetime(x).strftime('%d/%m/%Y') if pd.notnull(x) else "-",
            'Tot. Prev.': '{:,.2f} €',
            'Tot. Ord.': '{:,.2f} €',
            'Durata': lambda x: f"{int(x)} gg" if pd.notnull(x) else "-",
            'Q.tà Prev.': '{:,.0f}', 
            'Q.tà Ord.': '{:,.0f}'   
        }).map(colora_stato, subset=['Stato']),
        use_container_width=True, 
        hide_index=True
    )

    st.write("")
    st.write("")
    return report_prev
