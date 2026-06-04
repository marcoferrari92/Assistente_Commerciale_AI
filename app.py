import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import re
import json
import numpy as np

st.set_page_config(layout="wide")

from eventi_panoramica import distribuzione_eventi
from eventi_performance_team import analisi_performance_utenti
from eventi_aziende import coinvolgimento_aziende
from eventi_loading import carica_eventi
from ordini_loading import carica_ordini
from ordini_importi import validazione_importi
from ordini_panaromica import mostra_panoramica_ordini
from ordini_conversioni import analisi_conversione_preventivi

        




def DATA_range(df):
    
    date = df['DATA'].dropna()
    
    if not date.empty:
        d_min, d_max = date.min().date(), date.max().date()
        #st.info(f"📅 Dati disponibili: dal **{d_min.strftime('%d/%m/%Y')}** al **{d_max.strftime('%d/%m/%Y')}**")
        
        return d_min, d_max
        
    return None, None


def DATA_filtering(period, df):
    
    if isinstance(period, tuple) and len(period) == 2:
        #DATA_start, DATA_end = period
        df_filtrato = df[
                (df['DATA'].dt.date >= period[0]) & 
                (df['DATA'].dt.date <= period[1])
                ].copy()
        
    # Un piccolo avviso se manca una delle due date (inizio o fine)
    else:
        df_filtrato = df_events.copy()
        st.warning("Seleziona entrambe le date (inizio e fine) per filtrare.")

    return df_filtrato


def colora_stato(val):
    """Funzione di utilità per colorare il testo nella tabella Streamlit"""
    colori = {
        "AGGIUDICATO (CHIUSO)": "color: #4E944F; font-weight: bold;",
        "AGGIUDICATO (APERTO)": "color: #B4E197; font-weight: bold;",
        "IN SCADENZA": "color: #CCAA00; font-weight: bold;",
        "IN ATTESA": "color: #007BFF;",
        "PERSO": "color: #FF4B4B;"
    }
    return colori.get(val, "color: black;")







def analizza_performance_commerciali(df_report):
    
    # 1. PREPARAZIONE DATI
    df_integro = df_report.copy()
    if 'Analisi_Integrita' in df_report.columns:
        df_integro = df_integro[df_integro['Analisi_Integrita'] == "Dato Integro"]

    # 2. CALCOLO AGGREGATO BASE
    gruppo_agente = df_integro.groupby('CODICE GESTIONALE UTENTE')
    
    performance = gruppo_agente.agg(
        Nr_Prev=('ID DOCUMENTO', 'nunique'),
        Vol_Prev=('TOTALE', 'sum'),
        Nr_Vinti=('STATO_FINALE', lambda x: x.str.contains("AGGIUDICATO").sum()),
        Vol_Vinto=('TOTALE ORDINE', 'sum')
    ).reset_index()

    # 3. CALCOLO DETTAGLI CHIUSI/APERTI
    chiusi = df_integro[df_integro['STATO_FINALE'] == "AGGIUDICATO (CHIUSO)"].groupby('CODICE GESTIONALE UTENTE').agg(
        Nr_Chiusi=('ID DOCUMENTO', 'count'), Vol_Chiusi=('TOTALE ORDINE', 'sum')
    ).reset_index()

    aperti = df_integro[df_integro['STATO_FINALE'] == "AGGIUDICATO (APERTO)"].groupby('CODICE GESTIONALE UTENTE').agg(
        Nr_Aperti=('ID DOCUMENTO', 'count'), Vol_Aperti=('TOTALE ORDINE', 'sum')
    ).reset_index()

    performance = performance.merge(chiusi, on='CODICE GESTIONALE UTENTE', how='left').merge(aperti, on='CODICE GESTIONALE UTENTE', how='left').fillna(0)

    # 4. CALCOLO RATE NUMERICI (Per i Grafici)
    performance['Hit_Rate_Nr'] = (performance['Nr_Vinti'] / performance['Nr_Prev'] * 100).fillna(0)

    # 5. FUNZIONI FORMATTAZIONE PARENTESI (Per le Tabelle)
    def fmt_val_pct(val, total):
        pct = (val / total * 100) if total > 0 else 0
        return f"€ {val:,.2f} ({pct:.1f}%)"

    def fmt_nr_pct(val, total):
        pct = (val / total * 100) if total > 0 else 0
        return f"{int(val)} ({pct:.1f}%)"

    performance['Nr. Prev. Vinti (%)'] = performance.apply(lambda r: fmt_nr_pct(r['Nr_Vinti'], r['Nr_Prev']), axis=1)
    performance['Vol. Vinto (%)'] = performance.apply(lambda r: fmt_val_pct(r['Vol_Vinto'], r['Vol_Prev']), axis=1)
    performance['Nr. Ord. (Chiusi)'] = performance.apply(lambda r: fmt_nr_pct(r['Nr_Chiusi'], r['Nr_Vinti']), axis=1)
    performance['Vol. Ord. (Chiusi)'] = performance.apply(lambda r: fmt_val_pct(r['Vol_Chiusi'], r['Vol_Vinto']), axis=1)
    performance['Nr. Ord. (Aperti)'] = performance.apply(lambda r: fmt_nr_pct(r['Nr_Aperti'], r['Nr_Vinti']), axis=1)
    performance['Vol. Ord. (Aperti)'] = performance.apply(lambda r: fmt_val_pct(r['Vol_Aperti'], r['Vol_Vinto']), axis=1)

    # 6. VISUALIZZAZIONE TABELLA GENERALE
    st.write("")
    st.subheader("📈 Comparativa")
    st.write("")
    df_gen = performance[['CODICE GESTIONALE UTENTE', 'Nr_Prev', 'Nr. Prev. Vinti (%)', 'Vol_Prev', 'Vol. Vinto (%)', 
                          'Nr. Ord. (Chiusi)', 'Vol. Ord. (Chiusi)', 'Nr. Ord. (Aperti)', 'Vol. Ord. (Aperti)']].copy()
    df_gen.columns = ['Utente', 'Nr. Prev.', 'Nr. Prev. Vinti (%)', 'Vol. Prev.', 'Vol. Vinto (%)', 
                      'Nr. Ord. (Chiusi)', 'Vol. Ord. (Chiusi)', 'Nr. Ord. (Aperti)', 'Vol. Ord. (Aperti)']
    
    st.dataframe(df_gen.style.format({'Nr. Prev.': '{:,.0f}', 'Vol. Prev.': '€ {:,.2f}'}), use_container_width=True, hide_index=True)

    # --- 📊 SEZIONE GRAFICI COMPARATIVI (Side-by-Side) ---
    st.write("")
    col1, col2 = st.columns(2)

    with col1:
        # Grafico a Barre: Offerto vs Vinto
        fig_bar = px.bar(
            performance, 
            x='CODICE GESTIONALE UTENTE', 
            y=['Vol_Prev', 'Vol_Vinto'],
            barmode='group',
            title="Volume Preventivato vs Vinto",
            labels={'value': 'Euro (€)', 'variable': 'Tipo Volume', 'CODICE GESTIONALE UTENTE': 'Utente'},
            color_discrete_map={'Vol_Prev': '#A2D2FF', 'Vol_Vinto': '#4E944F'}
        )
        fig_bar.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        # Scatter Plot: Efficienza
        fig_scatter = px.scatter(
            performance, 
            x='Nr_Prev', 
            y='Hit_Rate_Nr',
            size='Vol_Vinto', 
            color='CODICE GESTIONALE UTENTE',
            title="Efficienza: N. Prev vs Tasso Conversione (%)",
            labels={'Nr_Prev': 'N. Preventivi', 'Hit_Rate_Nr': 'Tasso Conversione (%)', 'Vol_Vinto': 'Volume (€)'},
            template="plotly_white"
        )
        fig_scatter.update_layout(showlegend=False) # Legenda già presente nel grafico a fianco o implicita
        st.plotly_chart(fig_scatter, use_container_width=True)


    # --- 7. SEZIONE DETTAGLIO SINGOLO UTENTE ---
    st.divider()
    st.subheader("👤 Analisi Dettagliata per Utente")
    st.write("")
    
    utenti = df_report['CODICE GESTIONALE UTENTE'].unique()
    agente_sel = st.selectbox("Seleziona un Utente per approfondire:", utenti)
    
    if agente_sel:
        # Riepilogo KPI (Riga singola)
        perf_agente = performance[performance['CODICE GESTIONALE UTENTE'] == agente_sel].copy()
        df_kpi_agente = perf_agente[['Nr_Prev', 'Nr. Prev. Vinti (%)', 'Vol_Prev', 'Vol. Vinto (%)', 
                                    'Nr. Ord. (Chiusi)', 'Vol. Ord. (Chiusi)', 'Nr. Ord. (Aperti)', 'Vol. Ord. (Aperti)']].copy()
        df_kpi_agente.columns = ['Nr. Prev.', 'Nr. Prev. Vinti (%)', 'Vol. Prev.', 'Vol. Vinto (%)', 
                                 'Nr. Ord. (Chiusi)', 'Vol. Ord. (Chiusi)', 'Nr. Ord. (Aperti)', 'Vol. Ord. (Aperti)']

        st.write("")
        st.write(f"**Riepilogo Performance**")
        st.write("")
        st.dataframe(df_kpi_agente.style.format({'Nr. Prev.': '{:,.0f}', 'Vol. Prev.': '€ {:,.2f}'}), use_container_width=True, hide_index=True)

        # Registro Documenti (Analitico)
        st.write("")
        st.write(f"**Registro**")
        st.write("")
        df_agente_full = df_report[df_report['CODICE GESTIONALE UTENTE'] == agente_sel].copy()
        df_display_agente = df_agente_full[[
            'DATA', 'DATA ORDINE', 'DURATA', 'STATO_FINALE', 'INFO', 
            'CLIENTE', 'CODICE GESTIONALE UTENTE', 'QT', 'NUM ART ORD', 'TOTALE', 'TOTALE ORDINE',
            'ID DOCUMENTO', 'ID ORDINE'
        ]].copy()

        df_display_agente.columns = [
            'Data Prev.', 'Data Ord.', 'Durata', 'Stato', 'Info', 
            'Cliente', 'Utente', 'Q.tà Prev.', 'Q.tà Ord.', 'Tot. Prev.', 'Tot. Ord.', 
            'ID Prev.', 'ID Ord.'
        ]

        st.dataframe(
            df_display_agente.sort_values(by=['Data Prev.'], ascending=False)
            .style.format({
                'Data Prev.': lambda x: pd.to_datetime(x).strftime('%d/%m/%Y'),
                'Data Ord.': lambda x: pd.to_datetime(x).strftime('%d/%m/%Y') if pd.notnull(x) else "-",
                'Tot. Prev.': '{:,.2f} €',
                'Tot. Ord.': '{:,.2f} €',
                'Durata': lambda x: f"{int(x)} gg" if pd.notnull(x) else "-",
                'Q.tà Prev.': '{:,.0f}', 
                'Q.tà Ord.': '{:,.0f}'   
            }).map(colora_stato, subset=['Stato']),
            use_container_width=True, hide_index=True
        )

    return performance




# ***********************************************************************
#                                 MAIN APP
# ***********************************************************************


st.header("Analisi Commerciali")
st.divider()

# Inizializzazione
df_events = None
df_orders = None
# date calendario
date_min = None
date_max = None


# *****************
# CARICAMENTO FILE 
# *****************

# Inizializzazione variabili all'inizio dello script per evitare NameError
df_events = None
df_orders = None
date_min = None
date_max = None

st.subheader("Caricamento File")
col1, col2, col3 = st.columns(3)

with col1:
    st.write("#### Eventi")
    uploaded_file_events = st.file_uploader("Carica file eventi (formato CSV)", type="csv")
    if uploaded_file_events:
        df_events = carica_eventi(uploaded_file_events) 
        if df_events is not None:
            d_min_ev, d_max_ev = DATA_range(df_events)
            date_min, date_max = d_min_ev, d_max_ev

with col2:
    st.write("#### Ordini")
    uploaded_file_orders = st.file_uploader("Carica file ordini (formato JSON)", type="json")
    if uploaded_file_orders:
        df_orders = carica_ordini(uploaded_file_orders) 
        if df_orders is not None:
            d_min_or, d_max_or = DATA_range(df_orders)
            date_min, date_max = d_min_or, d_max_or


# --- SEZIONE FILTRO PERIODO ---
# Attiviamo i filtri solo se almeno uno dei due DF è stato creato
if date_min is not None and date_max is not None:
    with col3:
        st.write("#### Periodo Analisi")
        period = st.date_input(
            "Seleziona date:",
            value=(date_min, date_max),
            min_value=date_min,
            max_value=date_max
        )

    # Applichiamo il filtraggio solo se l'utente ha selezionato un range completo (inizio e fine)
    if isinstance(period, tuple) and len(period) == 2:
        if df_events is not None:
            df_events = DATA_filtering(period, df_events)
        
        if df_orders is not None:
            df_orders = DATA_filtering(period, df_orders)
    else:
        st.warning("Completa la selezione del periodo (Data inizio e Data fine).")
else:
    st.info("Carica almeno un file per attivare i filtri temporali.")



# ***********************************************************************
#                             ANALISI ORDINI 
# ***********************************************************************

st.divider()
st.subheader("Analisi Ordini e Preventivi")
st.write("")

if df_orders is not None: 
    
    # 1. CHIAMATA ALLA FUNZIONE DI VALIDAZIONE (ESTERNA)
    # df_orders_pulito restituisce record già unici per 'ID DOCUMENTO' con la colonna 'TOTALE' inclusa
    df_orders_pulito, df_orders_errori = validazione_importi(df_orders)
    
    if df_orders_pulito is not None and not df_orders_pulito.empty:
        
        # ********************************
        #  PANORAMICA ORDINI E PREVENTIVI
        # ********************************
        st.write("")
        mostra_panoramica_ordini(df_orders_pulito)
            
        # **********************************
        #  CONVERSIONE PREVENTIVI - GLOBALE
        # **********************************
        st.write("")
        st.write("")
        with st.expander("🎯 Analisi Conversione Preventivi Globale"):
            if isinstance(period, tuple) and len(period) == 2:
                max_slider = max(1, (period[1] - period[0]).days)
            else:
                max_slider = 180
                
            c1, c2, c3, c4, c5 = st.columns([0.2, 1, 0.3, 1, 0.2])
            with c2:
                finestra = st.slider("Validità preventivi (giorni):", min_value=1, max_value=max_slider, value=30)
            with c4:
                scadenza = st.number_input("Pre-avviso 'In Scadenza' (giorni):", min_value=1, max_value=30, value=7)
            
            st.write("")
            df_report = analisi_conversione_preventivi(df_orders_pulito, finestra, scadenza)

            
        # ******************************************
        #  CONVERSIONE PREVENTIVI - PER COMMERCIALE
        # ******************************************
        st.write("")
        st.write("")
        with st.expander("🏆 Analisi Conversione Preventivi per Commerciale"):
                if df_report is not None:
                        df_performance = analizza_performance_commerciali(df_report)
                        
    else:
        st.warning("⚠️ Nessun dato valido da analizzare dopo la pulizia del file JSON.")
        
    


# ***********************************************************************
#                             ANALISI EVENTI
# ***********************************************************************

if df_events is not None:
    

    st.divider()
    st.write("")
    st.subheader("Analisi Eventi")


    # FILTRO CAMPAGNE MARKETING

    # Controlliamo se la colonna CAMPAGNA esiste nel DataFrame
    if 'CAMPAGNA' in df_events.columns:

        # Pulizia preliminare della colonna per evitare duplicati causati da spazi o minuscole
        df_events['CAMPAGNA'] = df_events['CAMPAGNA'].astype(str).str.strip().str.upper()
        
        # Estraiamo le campagne uniche escludendo valori vuoti o 'NAN'
        campagne_uniche = df_events['CAMPAGNA'].unique()
        campagne_pulite = [c for c in campagne_uniche if c not in ['NAN', 'NONE', '', 'NAT']]
        campagne_pulite.sort()
        
        # Creiamo la lista delle opzioni per il filtro inserendo "Tutte le campagne" all'inizio
        opzioni_campagna = ["TUTTE LE CAMPAGNE"] + campagne_pulite
        
        # Render del selettore
        st.write("")
        campagna_selezionata = st.selectbox(
            "🎯 **Filtra l'analisi per Campagna Marketing:**",
            options=opzioni_campagna,
            index=0  # Di default mostra "Tutte le campagne"
        )
        
        # Applichiamo il filtro al DataFrame solo se l'utente non ha scelto "Tutte le campagne"
        if campagna_selezionata != "TUTTE LE CAMPAGNE":
            df_events = df_events[df_events['CAMPAGNA'] == campagna_selezionata]
            
            # Controllo di sicurezza se il filtro svuota il dataframe
            if df_events.empty:
                st.warning("⚠️ Nessun dato disponibile per la campagna selezionata.")
                st.stop()
    else:
        st.info("ℹ️ Colonna 'CAMPAGNA' non trovata nel file. L'analisi mostrerà tutti i dati disponibili.")


    # PULIZIA STRINGHE
    df_events['TIPO EVENTO'] = df_events['TIPO EVENTO'].astype(str).str.strip()
    df_events['TIPO EVENTO'] = df_events['TIPO EVENTO'].str.replace('TELEFONATO -', 'TELEFONATO', regex=False)
    df_events = df_events[~df_events['TIPO EVENTO'].isin(['nan', 'None', '', 'NaN'])]

    # PANORAMICA EVENTI
    st.write("")
    st.write("")
    with st.expander("👁️ Panoramica Eventi"):
        distribuzione_eventi(df_events)


    # PERFORMANCE TEAM ---
    st.write("")
    st.write("")
    with st.expander("⚡️ Performance Team"):
        analisi_performance_utenti(df_events)

    
    # --- SEZIONE AZIENDE PIÙ COINVOLTE ---
    st.write("")
    st.write("")
    with st.expander("🏢 Analisi Coinvolgimento Aziende"):
        coinvolgimento_aziende(df_events)
        
