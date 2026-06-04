import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def analisi_performance_utenti(df_events):

    colonna_utente = 'UTENTE'
    colonna_evento = 'TIPO EVENTO'
    colonna_anagrafica = 'TIPO ANAGRAFICA'
    
    # Verifichiamo che le colonne necessarie esistano nel dataset
    if colonna_utente not in df_events.columns or colonna_evento not in df_events.columns:
        st.error(f"Colonne richieste non trovate. Assicurati che nel file ci siano '{colonna_utente}' e '{colonna_evento}'.")
        return
        
    df_temp = df_events.copy()
    if colonna_anagrafica in df_temp.columns:
        df_temp[colonna_anagrafica] = df_temp[colonna_anagrafica].astype(str).str.upper().str.strip()
    
    # Rimuoviamo i valori nulli o spuri
    df_temp = df_temp[~df_temp[colonna_evento].astype(str).isin(['nan', 'None', '', 'NaN'])]
    df_temp = df_temp[~df_temp[colonna_utente].astype(str).isin(['nan', 'None', '', 'NaN'])]
    df_temp[colonna_utente] = df_temp[colonna_utente].str.strip().str.title()
    df_temp[colonna_evento] = df_temp[colonna_evento].str.upper().str.strip()
    
    # ---------------------------------------------------------
    # FILTRO: Selezione Target Anagrafica e Attività (CON MEMORIA)
    # ---------------------------------------------------------
    st.write(f"#### Filtri analisi")
    st.write("")

    col0, col1, col2, col3, col4 = st.columns([0.1, 1.2, 0.2, 1.2, 0.1])

    # Calcoliamo la lista di TUTTI gli utenti unici presenti nel file PRIMA di qualsiasi filtro.
    # Questo serve a mantenere i default coerenti nello st.session_state.
    elenco_utenti_totale = sorted(df_events[colonna_utente].dropna().astype(str).str.strip().str.title().unique())

    # Inizializziamo lo stato della memoria per i commerciali se non esiste ancora
    if "commerciali_salvati" not in st.session_state:
        st.session_state.commerciali_salvati = elenco_utenti_totale

    with col1:
        scelta_anagrafica = st.selectbox(
            "Seleziona il target di anagrafica da analizzare:",
            ["Tutte le anagrafiche", "Clienti", "Lead", "Prospect"],
            key="sel_anagrafica_utenti"
        )
        
        if scelta_anagrafica == "Clienti":
            df_temp = df_temp[df_temp[colonna_anagrafica] == 'CLIENTE']
        elif scelta_anagrafica == "Lead":
            df_temp = df_temp[df_temp[colonna_anagrafica] == 'LEAD']
        elif scelta_anagrafica == "Prospect":
            df_temp = df_temp[df_temp[colonna_anagrafica] == 'PROSPECT']
        
        mostra_solo_principali = st.checkbox(
            "Solo attività principali (Telefonato, Visitato, Inviata e-mail)", 
            value=True,
            key="utenti_filtro_attivita"
        )
        attivita_da_considerare = ['TELEFONATO', 'VISITATO', 'INVIATA MAIL']
        if mostra_solo_principali:
            df_temp = df_temp[df_temp[colonna_evento].isin(attivita_da_considerare)]
    
    with col3:
        # L'elenco delle opzioni disponibili mostrate nel menu a tendina 
        # riflette l'anagrafica scelta per non mostrare commerciali "vuoti"
        elenco_utenti_disponibili = sorted(df_temp[colonna_utente].unique())
        
        # Sincronizziamo la vecchia selezione memorizzata con le opzioni effettivamente disponibili nel filtro corrente
        default_utenti = [u for u in st.session_state.commerciali_salvati if u in elenco_utenti_disponibili]
        
        # Se il cambio anagrafica rende la lista dei default completamente vuota, facciamo il fallback su tutti i disponibili
        if not default_utenti:
            default_utenti = elenco_utenti_disponibili

        utenti_selezionati = st.multiselect(
            "Filtra o isola utenti specifici:",
            options=elenco_utenti_disponibili,
            default=default_utenti,
            key="utenti_filtro_nomi"
        )
        
        # Salviamo immediatamente nello stato la scelta attuale dell'utente prima che la pagina ricarichi
        st.session_state.commerciali_salvati = utenti_selezionati
        
        df_filtered = df_temp[df_temp[colonna_utente].isin(utenti_selezionati)]

    # ---------------------------------------------------------
    # CREAZIONE MATRICE PIVOT BASE SINCRO
    # ---------------------------------------------------------
    pivot_df = pd.crosstab(df_filtered[colonna_utente], df_filtered[colonna_evento])
    pivot_df = pivot_df.reindex(index=utenti_selezionati, fill_value=0)
    
    # Ordinamento decrescente basato sul volume totale per utente
    totale_per_utente = pivot_df.sum(axis=1).sort_values(ascending=False)
    ordine_commerciali = list(totale_per_utente.index)
    pivot_df = pivot_df.reindex(index=ordine_commerciali)
    
    # Palette Colori Eventi Fisso
    color_mapping_eventi = {
        'VISITARE': '#ffff00', 'VISITATO': '#ffcc00',       
        'TELEFONARE': '#ff66ff', 'TELEFONATO': '#af7ac5',     
        'INVIARE EMAIL': '#66ff66', 'INVIATA MAIL': '#009900', 'INVIO E-MAIL SFC': '#009900', 
        'PARTECIPAZIONE WEBINAR': '#3498db', 'SOLLECITARE OFFERTA COMMERCIALE': '#2c3e50' 
    }
    
    # Palette ufficiale Plotly per i commerciali (Colori Accesi)
    palette_commerciali = px.colors.qualitative.Plotly
    colori_commerciali_accesi = {comm: palette_commerciali[i % len(palette_commerciali)] for i, comm in enumerate(ordine_commerciali)}

    # Generazione dei corrispettivi Colori Soft (Trasparenza 20% / RGBA) per lo sfondo delle colonne
    # Questa funzione converte l'esadecimale della palette in un canale RGBA soft
    def hex_to_rgba_soft(hex_str, alpha=0.20):
        hex_str = hex_str.lstrip('#')
        rgb = tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
        return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"

    # RIGA CORRETTA:
    colori_commerciali_soft = {comm: hex_to_rgba_soft(colori_commerciali_accesi[comm]) for comm in ordine_commerciali}

    # Mappa dei colori soft per le attività (per la seconda tabella)
    colori_attivita_soft = {
        'VISITATO': 'rgba(255, 204, 0, 0.20)',
        'VISITARE': 'rgba(255, 255, 0, 0.20)',
        'TELEFONATO': 'rgba(175, 122, 197, 0.20)',
        'TELEFONARE': 'rgba(255, 102, 255, 0.20)',
        'INVIATA MAIL': 'rgba(0, 153, 0, 0.20)',
        'INVIARE EMAIL': 'rgba(102, 255, 102, 0.20)',
        'INVIO E-MAIL SFC': 'rgba(0, 153, 0, 0.20)',
        'PARTECIPAZIONE WEBINAR': 'rgba(52, 152, 219, 0.20)',
        'SOLLECITARE OFFERTA COMMERCIALE': 'rgba(44, 62, 80, 0.15)'
    }

    # ***********************************************************
    # SEZ. 1 - SELETTORE MODALITÀ DI ANALISI
    # ***********************************************************

    st.divider()
    st.write("")
    st.write("")
    col1, col2, col3 = st.columns([1.8, 1.9, 0.6])
    with col1:
        st.write(f"#### 1. Panoramica sulle performance commerciali")
        st.write("Analisi comparativa dei volumi di attività e delle quote di ripartizione interne al team.")
    with col3:
        st.success("✅ Codice Validato")
        
    st.write("")
    col_sel1, col_sel2 = st.columns([1.5, 2])
    with col_sel1:
        tipo_visualizzazione = st.radio(
            "Seleziona la modalità di analisi dati:",
            ["Quote Commerciali per Attività", "Volume Attività per Commerciale"],
            horizontal=True,
            key="radio_visualizzazione_speculare"
        )

    st.write("")
    totali_globali_attivita = pivot_df.sum(axis=0).to_dict()
    ordine_grafico_visuale = ordine_commerciali[::-1]

    # =========================================================================
    # CASE 1: QUOTE COMMERCIALI PER ATTIVITÀ (Sincro Tabella 1)
    # =========================================================================
    if tipo_visualizzazione == "Quote Commerciali per Attività":
        st.write(f"**Quote Commerciali per Attività**")
        st.caption("Ripartizione percentuale dei singoli commerciali all'interno del volume totale di ogni attività.")
        
        df_assoluto = pivot_df.T.reset_index().melt(id_vars=colonna_evento, var_name=colonna_utente, value_name='Conteggio')
        
        pivot_perc = pivot_df.div(pivot_df.sum(axis=0), axis=1) * 100
        df_long = pivot_perc.T.reset_index().melt(id_vars=colonna_evento, var_name=colonna_utente, value_name='Percentuale')
        df_long['Conteggio'] = df_assoluto['Conteggio']
        df_long['Totale_Attivita_Team'] = df_long[colonna_evento].map(totali_globali_attivita)
        df_long['Etichetta_Perc'] = df_long['Percentuale'].apply(lambda x: f"<b>{x:.1f}%</b>" if x > 0 else "")

        fig_bar = px.bar(
            df_long, y=colonna_evento, x='Percentuale', color=colonna_utente,
            text='Etichetta_Perc', barmode='group', orientation='h',
            color_discrete_map=colori_commerciali_accesi,
            custom_data=[colonna_utente, 'Conteggio', 'Totale_Attivita_Team']
        )
        fig_bar.update_traces(
            hovertemplate="<b>Attività: %{y}</b><br>Commerciale: %{customdata[0]}<br>Eventi Commerciale: %{customdata[1]}<br>Totale Team: %{customdata[2]}<br>Quota: %{x:.1f}%<extra></extra>",
            textposition="outside", cliponaxis=False, outsidetextfont=dict(color="#2c3e50", size=12)
        )
        fig_bar.update_layout(xaxis_title="Quota (%)", xaxis=dict(ticksuffix="%"))
        massimo_x = df_long['Percentuale'].max()
        fig_bar.update_layout(xaxis=dict(range=[0, massimo_x * 1.15] if massimo_x > 0 else [0, 100]), height=400)
        st.plotly_chart(fig_bar, use_container_width=True)

        # --- TABELLA RIASSUNTIVA 1 SINCRO ---
        df_totali_attivita = pivot_df.sum(axis=0)
        righe_tabella = []
        for attivita in pivot_df.columns[::-1]:
            totale_att = df_totali_attivita[attivita]
            riga = {"Attività": attivita, "Totale Eventi": totale_att}
            for comm in ordine_commerciali:
                conteggio = pivot_df.loc[comm, attivita]
                quota = (conteggio / totale_att * 100) if totale_att > 0 else 0.0
                riga[f"{comm} (Ev.)"] = conteggio
                riga[f"{comm} (%)"] = f"{quota:.1f}%"
            righe_tabella.append(riga)
            
        df_riepilogo_tabella = pd.DataFrame(righe_tabella).set_index("Attività")
        
        # STYLING TABELLA 1: Totale Eventi acceso, colonne dei commerciali colorate col rispettivo SOFT color
        def stile_tabella_1(row):
            styles = [''] * len(row)
            attivita_corrente = row.name.upper()
            for i, col in enumerate(row.index):
                if col == "Totale Eventi":
                    colore_vivido = color_mapping_eventi.get(attivita_corrente, 'rgba(200,200,200,0.25)')
                    styles[i] = f"background-color: {colore_vivido}; color: black; font-weight: bold;"
                else:
                    # Estraiamo dinamicamente il nome del commerciale dall'intestazione della colonna
                    nome_commerciale = col.replace(" (Ev.)", "").replace(" (%)", "")
                    colore_soft = colori_commerciali_soft.get(nome_commerciale, 'rgba(200,200,200,0.15)')
                    styles[i] = f"background-color: {colore_soft}; color: black;"
            return styles

        def stile_indice_tabella_1(index_series):
            return [f"background-color: {color_mapping_eventi.get(idx.upper(), '#rgba(200,200,200,0.25)')}; color: black; font-weight: bold;" for idx in index_series]

        df_styled_1 = df_riepilogo_tabella.style.apply(stile_tabella_1, axis=1).apply_index(stile_indice_tabella_1, axis=0)
        config_colonne_1 = {"Totale Eventi": st.column_config.NumberColumn(format="%d")}
        for comm in ordine_commerciali:
            config_colonne_1[f"{comm} (Ev.)"] = st.column_config.NumberColumn(format="%d")
            
        st.dataframe(df_styled_1, use_container_width=True, column_config=config_colonne_1)

    # =========================================================================
    # CASE 2: VOLUME ATTIVITÀ PER COMMERCIALE (Sincro Tabella 2)
    # =========================================================================
    else:
        st.write(f"**Volume Attività per Commerciale**")
        st.caption("Volume complessivo di attività svolte, evidenziando la composizione interna del mix di lavoro di ogni utente.")
        
        df_long = pivot_df.reset_index().melt(id_vars=colonna_utente, var_name=colonna_evento, value_name='Conteggio')
        df_long.columns = ['Commerciale', 'Tipo Evento', 'Conteggio']
        
        pivot_perc_orizzontale = pivot_df.div(pivot_df.sum(axis=1), axis=0) * 100
        df_perc_long = pivot_perc_orizzontale.reset_index().melt(id_vars=colonna_utente, var_name=colonna_evento, value_name='Percentuale')
        df_long['Percentuale'] = df_perc_long['Percentuale']
        df_long['Totale_Attivita_Team'] = df_long['Tipo Evento'].map(totali_globali_attivita)

        fig_bar = px.bar(
            df_long, y='Commerciale', x='Conteggio', color='Tipo Evento',
            text='Conteggio', barmode='relative', orientation='h',
            color_discrete_map=color_mapping_eventi,
            category_orders={'Commerciale': ordine_grafico_visuale},
            custom_data=['Tipo Evento', 'Percentuale', 'Totale_Attivita_Team']
        )
        fig_bar.update_traces(
            hovertemplate="<b>Commerciale: %{y}</b><br>Attività: %{customdata[0]}<br>Eventi: %{x}<br>Quota su suo totale: %{customdata[1]:.1f}%<extra></extra>",
            textposition="inside", insidetextanchor="middle"
        )
        
        totali_commerciale = pivot_df.sum(axis=1)
        for comm, totale in totali_commerciale.items():
            if totale > 0:
                fig_bar.add_annotation(
                    y=comm, x=totale, text=f"<b>{totale:.0f}</b>", 
                    showarrow=False, xshift=10, yanchor="middle", xanchor="left",
                    font=dict(color="#2c3e50", size=12)
                )
                
        fig_bar.update_layout(
            xaxis_title="Numero di Eventi", yaxis_title="",
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450
        )
        massimo_conteggio = totali_commerciale.max()
        fig_bar.update_xaxes(range=[0, massimo_conteggio * 1.15] if massimo_conteggio > 0 else [0, 10], showgrid=True, gridcolor='rgba(200,200,200,0.2)')
        st.plotly_chart(fig_bar, use_container_width=True)

        # --- TABELLA RIASSUNTIVA 2 SINCRO ---
        righe_tabella_invertita = []
        for comm in ordine_commerciali:
            totale_comm = totali_commerciale[comm]
            riga_dati = {"Commerciale": comm, "Totale Attività": totale_comm}
            for attivita in pivot_df.columns:
                conteggio_evento = pivot_df.loc[comm, attivita]
                quota_evento = (conteggio_evento / totale_comm * 100) if totale_comm > 0 else 0.0
                riga_dati[f"{attivita.strip().capitalize()} (Ev.)"] = conteggio_evento
                riga_dati[f"{attivita.strip().capitalize()} (%)"] = f"{quota_evento:.1f}%"
            righe_tabella_invertita.append(riga_dati)
            
        df_riepilogo_invertito = pd.DataFrame(righe_tabella_invertita).set_index("Commerciale")
        
        # STYLING TABELLA 2: Totale Attività acceso col colore del commerciale, colonne delle attività a destra soft
        def stile_tabella_2(row):
            styles = [''] * len(row)
            commerciale_corrente = row.name 
            for i, col in enumerate(row.index):
                if col == "Totale Attività":
                    colore_vivido = colori_commerciali_accesi.get(commerciale_corrente, '')
                    styles[i] = f"background-color: {colore_vivido}; color: black; font-weight: bold;"
                else:
                    # Identifichiamo l'attività per assegnare il rispettivo colore soft
                    col_upper = col.upper().replace(" (EV.)", "").replace(" (%)", "").strip()
                    colore_soft = 'rgba(200,200,200,0.15)' # Fallback
                    for att_chiave, colore_rgb in colori_attivita_soft.items():
                        if att_chiave in col_upper:
                            colore_soft = colore_rgb
                            break
                    styles[i] = f"background-color: {colore_soft}; color: black;"
            return styles

        def stile_indice_tabella_2(index_series):
            return [f"background-color: {colori_commerciali_accesi.get(idx, '')}; color: black; font-weight: bold;" for idx in index_series]

        df_styled_2 = df_riepilogo_invertito.style.apply(stile_tabella_2, axis=1).apply_index(stile_indice_tabella_2, axis=0)
        config_colonne_dinamiche = {"Totale Attività": st.column_config.NumberColumn(format="%d")}
        for attivita in pivot_df.columns:
            config_colonne_dinamiche[f"{attivita.strip().capitalize()} (Ev.)"] = st.column_config.NumberColumn(format="%d")

        st.dataframe(df_styled_2, use_container_width=True, column_config=config_colonne_dinamiche)


    # ***********************************************************
    # SEZ. 2 - PROFILI STRATEGICI (GRAFICO RADAR SINCRO SPECULARE)
    # ***********************************************************
    st.divider()
    st.write("")
    st.write("")
    col1, col2, col3 = st.columns([1.8, 1.9, 0.6])
    with col1:
        st.write("#### 2. Profili strategici dei commerciali")
        st.write("Radar del bilanciamento operativo. Il grafico risponde dinamicamente alla modalità di analisi scelta sopra.")
    with col3:
        st.success("✅ Codice Validato")
    st.write("")
    
    attivita_radar_default = ['TELEFONATO', 'VISITATO', 'INVIATA MAIL']
    attivita_radar_target = [att for att in attivita_radar_default if att in pivot_df.columns]

    if len(attivita_radar_target) >= 3:
        pivot_radar = pivot_df[attivita_radar_target].copy()
        
        col_radar, col_controlli = st.columns([3.2, 0.8])
        with col_controlli:
            st.write("")
            normalizza_radar = st.toggle("Normalizzazione dati", value=True, key="toggle_normalizza_radar_utenti")

        fig_radar = go.Figure()
        suffisso_unita = "%" if normalizza_radar else ""

        # -----------------------------------------------------------------
        # RADAR SINCRO 1: Quote Commerciali per Attività
        # -----------------------------------------------------------------
        if tipo_visualizzazione == "Quote Commerciali per Attività":
            totali_per_attivita = pivot_radar.sum(axis=0)
            pivot_radar_perc = (pivot_radar.div(totali_per_attivita, axis=1) * 100).fillna(0)
            pivot_radar_plot = pivot_radar_perc.copy() if normalizza_radar else pivot_radar.copy()
            
            categorie_radar = list(pivot_radar_plot.index)
            categorie_radar_chiuso = categorie_radar + [categorie_radar[0]]
            colori_pallini = [colori_commerciali_accesi.get(cat, '#000000') for cat in categorie_radar] + [colori_commerciali_accesi.get(categorie_radar[0], '#000000')]

            for attivita in pivot_radar_plot.columns:
                valori_r = list(pivot_radar_plot[attivita])
                valori_r_chiuso = valori_r + [valori_r[0]]
                
                fig_radar.add_trace(go.Scatterpolar(
                    r=valori_r_chiuso, theta=categorie_radar_chiuso, mode='lines+markers',
                    marker=dict(size=9, symbol='circle', color=colori_pallini, line=dict(width=1, color='white')),
                    name=attivita.capitalize(), fill='toself',
                    line=dict(color=color_mapping_eventi.get(attivita), width=2.5),
                    hovertemplate=f"<b>Attività: {attivita.capitalize()}</b><br>Commerciale: %{{theta}}<br>Valore: %{{r:.1f}}{suffisso_unita}<extra></extra>"
                ))

        # -----------------------------------------------------------------
        # RADAR SINCRO 2: Volume Attività per Commerciale
        # -----------------------------------------------------------------
        else:
            totali_per_profilo = pivot_radar.sum(axis=1)
            pivot_radar_perc = (pivot_radar.div(totali_per_profilo, axis=0) * 100).fillna(0)
            pivot_radar_plot = pivot_radar_perc.copy() if normalizza_radar else pivot_radar.copy()
            
            categorie_radar = [cat.capitalize() for cat in pivot_radar_plot.columns]
            categorie_radar_chiuso = categorie_radar + [categorie_radar[0]]
            colori_pallini = [color_mapping_eventi.get(cat.upper(), '#000000') for cat in pivot_radar_plot.columns] + [color_mapping_eventi.get(pivot_radar_plot.columns[0].upper(), '#000000')]

            for comm in pivot_radar_plot.index:
                valori_r = list(pivot_radar_plot.loc[comm])
                valori_r_chiuso = valori_r + [valori_r[0]]
                
                fig_radar.add_trace(go.Scatterpolar(
                    r=valori_r_chiuso, theta=categorie_radar_chiuso, mode='lines+markers',
                    marker=dict(size=9, symbol='circle', color=colori_pallini, line=dict(width=1, color='white')),
                    name=comm, fill='toself',
                    line=dict(color=colori_commerciali_accesi.get(comm), width=2.5),
                    hovertemplate=f"<b>Profilo: {comm}</b><br>Attività: %{{theta}}<br>Valore: %{{r:.1f}}{suffisso_unita}<extra></extra>"
                ))

        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=True, gridcolor='rgba(200,200,200,0.4)', ticksuffix=suffisso_unita),
                angularaxis=dict(gridcolor='rgba(200,200,200,0.4)', tickfont=dict(size=12, weight='bold')),
                bgcolor='rgba(0,0,0,0)'
            ),
            paper_bgcolor='rgba(0,0,0,0)', height=520, margin=dict(l=40, r=40, t=25, b=25),
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.1)
        )
        st.plotly_chart(fig_radar, use_container_width=True)
    else:
        st.info("Nessun dato sufficiente sulle 3 attività principali per generare il Radar.")


    # ***********************************************************
    # SEZ. 3 - CUSTOMER JOURNEY
    # ***********************************************************
    st.divider()
    st.write("")
    st.write("")
    col1, col2, col3 = st.columns([1.8, 1.9, 0.6])
    with col1:
        st.write("#### 3. Panoramica delle transizioni delle attività per Commerciale")
        st.write("Questa mappa mostra quale attività segue più frequentemente un'altra sullo storico della stessa azienda, divisa per commerciale.")
    with col3:
        st.warning("⚠️ In validazione")
    st.write("")
    
    
    colonna_azienda = next((c for c in df_events.columns if c in ['RAGIONE SOCIALE', 'NOME AZIENDA', 'CLIENTE', 'AZIENDA']), None)
    colonna_data = next((c for c in df_events.columns if c in ['DATA', 'DATA EVENTO', 'DATA_EVENTO']), None)

    if colonna_azienda and colonna_data:
        df_journey_base = df_filtered.copy()
        df_journey_base[colonna_data] = pd.to_datetime(df_journey_base[colonna_data], errors='coerce')
        df_journey_base = df_journey_base.dropna(subset=[colonna_data, colonna_evento, colonna_azienda, colonna_utente])
        
        col_f1, col_f2 = st.columns([1.5, 2])
        with col_f1:
            solo_principali_journey = st.checkbox(
                "Filtra solo attività principali nel journey", value=True, key="checkbox_journey_comm_fixed"
            )
            attivita_target_journey = ['TELEFONATO', 'VISITATO', 'INVIATA MAIL']
        with col_f2:
            modalita_heatmap = st.radio(
                "Mostra dati heatmap come:",
                ["Numero di Transizioni (Valori Assoluti)", "Probabilità di Passaggio (% sulla riga)"],
                horizontal=True, key="radio_heatmap_comm_fixed"
            )

        st.write("")
        
        utenti_attivi_journey = [u for u in ordine_commerciali if u in df_journey_base[colonna_utente].unique()]
        
        if utenti_attivi_journey:
            chunk_size = 3
            for chunk in [utenti_attivi_journey[i:i + chunk_size] for i in range(0, len(utenti_attivi_journey), chunk_size)]:
                st_cols = st.columns(len(chunk))
                
                for idx_ut, utente in enumerate(chunk):
                    with st_cols[idx_ut]:
                        st.markdown(f"<h4 style='text-align: center; color:#2c3e50;'>{utente}</h4>", unsafe_allow_html=True)
                        df_journey = df_journey_base[df_journey_base[colonna_utente] == utente].copy()
                        
                        if solo_principali_journey:
                            df_journey = df_journey[df_journey[colonna_evento].isin(attivita_target_journey)]
                            
                        df_journey = df_journey.sort_values(by=[colonna_azienda, colonna_data])
                        df_journey['ATTIVITA_SUCCESSIVA'] = df_journey.groupby(colonna_azienda)[colonna_evento].shift(-1)
                        
                        if solo_principali_journey:
                            df_journey = df_journey[df_journey['ATTIVITA_SUCCESSIVA'].isin(attivita_target_journey)]
                            
                        df_transizioni = df_journey.dropna(subset=['ATTIVITA_SUCCESSIVA']).copy()
                        
                        if not df_transizioni.empty:
                            matrice_transizione = pd.crosstab(df_transizioni[colonna_evento], df_transizioni['ATTIVITA_SUCCESSIVA'])
                            indici_assi = attivita_target_journey if solo_principali_journey else sorted(list(set(df_journey_base[colonna_evento])))
                            matrice_transizione = matrice_transizione.reindex(index=indici_assi, columns=indici_assi, fill_value=0)
                            
                            matrice_transizione.index = [idx.capitalize() for idx in matrice_transizione.index]
                            matrice_transizione.columns = [col.capitalize() for col in matrice_transizione.columns]
                            
                            if "Probabilità" in modalita_heatmap:
                                matrice_plot = (matrice_transizione.div(matrice_transizione.sum(axis=1), axis=0) * 100).fillna(0)
                                testo_celle = matrice_plot.map(lambda x: f"{x:.1f}%" if x > 0 else "0.0%")
                                hovertemplate_heat = "<b>Commerciale: " + utente + "</b><br>Da: %{y}<br>A: %{x}<br>Probabilità: %{z:.1f}%<extra></extra>"
                            else:
                                matrice_plot = matrice_transizione.copy()
                                testo_celle = matrice_plot.map(lambda x: f"{x:.0f}")
                                hovertemplate_heat = "<b>Commerciale: " + utente + "</b><br>Da: %{y}<br>A: %{x}<br>Conteggio: %{z:.0f} volte<extra></extra>"
                            
                            fig_heat = px.imshow(
                                matrice_plot, text_auto=False, color_continuous_scale="Purples",
                                labels=dict(x="Attività Successiva ➡️", y="⬅️ Attività Corrente")
                            )
                            fig_heat.update_traces(text=testo_celle, texttemplate="%{text}", selector=dict(type='heatmap'), hovertemplate=hovertemplate_heat)
                            fig_heat.update_layout(
                                xaxis=dict(side="bottom", tickangle=-20 if not solo_principali_journey else 0, tickfont=dict(size=10, weight='bold')),
                                yaxis=dict(tickfont=dict(size=10, weight='bold')),
                                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                coloraxis_showscale=False, height=330, margin=dict(l=40, r=20, t=10, b=30)
                            )
                            st.plotly_chart(fig_heat, use_container_width=True)
                        else:
                            st.info(f"Nessun pattern sequenziale per {utente}.")
        else:
            st.warning("Seleziona almeno un utente attivo nei filtri.")
    else:
        st.caption("ℹ️ *Nota: Per visualizzare le matrici del Customer Journey, assicurati che il file contenga le colonne temporale ed identificativa dell'azienda.*")