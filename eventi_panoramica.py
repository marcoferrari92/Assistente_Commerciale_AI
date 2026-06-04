import streamlit as st
import pandas as pd
import plotly.express as px

def distribuzione_eventi(df_events):
    
    # Verifichiamo la colonna anagrafica esista (cliente, lead e prospect)
    if 'TIPO ANAGRAFICA' in df_events.columns:
        
        st.write("")
        
        col1, col2, col3 = st.columns([1.5, 2, 0.6])
        with col1:
            st.write(f"#### 1. Panoramica sul portafoglio aziende")
            st.write("Di seguito una panoramica sul numero di attività svolte per le tre anagrafiche (clienti, lead, prospect) e le relative quote sul totale di eventi.")
        with col3:
            st.success("✅ Codice Validato")

    
        # *****************************************
        # SEZ. 1 - CONTEGGIO EVENTI PER ANAGRAFICA
        # *****************************************

        df_temp                         = df_events.copy()
        counts                          = df_temp['TIPO ANAGRAFICA'].value_counts()                         # Num. di eventi per ogni anafagrafica
        target_categories               = ['CLIENTE', 'LEAD', 'PROSPECT']                                   # Tre categorie d'interesse

        # Check categorie extra
        categorie_rilevate              = set(counts.index)
        categorie_attese                = set(target_categories)
        categorie_extra                 = categorie_rilevate - categorie_attese
        if categorie_extra:
            print(f"⚠️ ATTENZIONE: Trovate categorie non previste in 'TIPO ANAGRAFICA': {categorie_extra}")

        filtered_counts                 = counts.reindex(target_categories, fill_value=0).reset_index()     # Filtra counts per le tre categorie (se vuote assegna il fill value 0) e crea un dataframe
        filtered_counts.columns         = ['TIPO ANAGRAFICA', 'CONTEGGIO']                                  # Colonne del nuovo dataframe (TIPO ANAGRAFICA, CONTEGGIO)
        filtered_counts['Anagrafica']   = filtered_counts['TIPO ANAGRAFICA'].str.capitalize()               # Rinomina TIPO ANAGRAFICA -> Anagrafica (per i grafici)
        totale_eventi                   = filtered_counts['CONTEGGIO'].sum()                                # Somma tutti i valori della colonna CONTEGGIO

        # Se il numero totali di eventi non è nullo, calcola le quote per ogni anagrafica
        if totale_eventi > 0:
            filtered_counts['QUOTA'] = (filtered_counts['CONTEGGIO'] / totale_eventi) * 100
        else:
            filtered_counts['QUOTA'] = 0.0
        

        # Layout Streamlit: Colonne per la prima riga (Tabella + Torta Interattiva)
        col0, col1, col2, col3, col4 = st.columns([0.1, 0.8, 0.1, 1.1, 0.2])
        
        with col1:
            
            st.write("")
            st.write("")
            st.write("")
            st.write("")
            df_da_mostrare = filtered_counts.set_index('Anagrafica')[['CONTEGGIO', 'QUOTA']]
            st.dataframe(
                df_da_mostrare,
                column_config={
                    "CONTEGGIO": st.column_config.NumberColumn("Eventi", format="%d"),
                    "QUOTA": st.column_config.NumberColumn("Quota (%)", format="%.1f%%")
                },
                use_container_width=True
            )
        
        with col3:
            fig_pie = px.pie(
                filtered_counts, 
                values='CONTEGGIO', 
                names='Anagrafica',
                color='Anagrafica',
                color_discrete_map={'Cliente': '#5dade2', 'Lead': '#58d68d', 'Prospect': '#ec7063'},
                hole=0.3
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label', hovertemplate="<b>%{label}</b><br>Eventi: %{value}<br>Quota: %{percent}")
            fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300, showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        

        # ***********************************
        # SEZ. 2 - DETTAGLI TIPOLOGIA EVENTI
        # ***********************************

        if 'TIPO EVENTO' in df_events.columns:

            st.divider()
            st.write("")
            col1, col2, col3 = st.columns([1.8, 1.9, 0.6])
            with col1:
                st.write(f"#### 2. Panoramica sulla tipologia di attività svolte")
                st.write("Di seguito una panoramica sulle diverse tipologie di eventi svolti")
            with col3:
                st.success("✅ Codice Validato")
            st.write("")

            col0, col1, col2 = st.columns([0.3, 1.5, 2])


            # ----------
            # SELETTORI
            # ----------

            # SELETTORE 1: Tipologia Eventi (Principali vs Tutti)
            with col1:
                st.write("**Eventi da analizzare**")
                
                mostra_solo_principali = st.checkbox(
                    "Solo attività principali (Telefonato, Visitato, Inviata e-mail)", 
                    value = True
                )
                st.caption("Deseleziona la casella per analizzare tutte le attività")
            
                if mostra_solo_principali:
                    attivita_da_considerare = ['TELEFONATO', 'VISITATO', 'INVIATA MAIL']
                    df_filtered_types = df_temp[
                        (df_temp['TIPO ANAGRAFICA'].isin(target_categories)) & 
                        (df_temp['TIPO EVENTO'].isin(attivita_da_considerare))
                    ]
                else:
                    df_filtered_types = df_temp[df_temp['TIPO ANAGRAFICA'].isin(target_categories)]
                
                if df_filtered_types.empty:
                    st.warning("Nessun dato disponibile con i filtriCampi selezionati.")
                    return
            
                # Creiamo la tabella pivot (Crosstab) di base
                pivot_df        = pd.crosstab(df_filtered_types['TIPO ANAGRAFICA'], df_filtered_types['TIPO EVENTO'])
                pivot_df        = pivot_df.reindex(target_categories, fill_value=0)
                pivot_df.index  = [idx.capitalize() for idx in pivot_df.index]
                
                # Mappa Colori Custom per la modalità assoluta
                color_mapping_eventi = {
                    'VISITARE': '#ffff00',       
                    'VISITATO': '#ffcc00',       
                    'TELEFONARE': '#ff66ff',     
                    'TELEFONATO': '#af7ac5',     
                    'INVIARE EMAIL': '#66ff66',   
                    'INVIATA MAIL': '#009900',    
                    'INVIO E-MAIL SFC': '#009900', 
                    'PARTECIPAZIONE WEBINAR': '#3498db', 
                    'SOLLECITARE OFFERTA COMMERCIALE': '#000000' 
                }
            
            # SELETTORE 2: Modalità Visualizzazione (Volume vs Percentuali)
            with col2: 
                st.write(f"**Modalità di Analisi**")
                tipo_visualizzazione = st.radio(
                    "Seleziona la modalità di analisi dati:",
                    ["Volume Attività per Anagrafica", "Quote Anagrafiche per Attività"],
                    horizontal = True
                )
            st.write("")
            st.write("")


            # -------------------------------------------------------------
            # CONFIGURAZIONI TAVOLOZZA COLORI SOFT PER LO STYLING TABELLE
            # -------------------------------------------------------------
            ordine_grafico = ['Prospect', 'Lead', 'Cliente']

            colori_anagrafiche_soft = {
                'Prospect': 'rgba(236, 112, 99, 0.25)',  
                'Lead': 'rgba(88, 214, 141, 0.25)',     
                'Cliente': 'rgba(93, 173, 226, 0.25)'    
            }

            colori_attivita_soft = {
                'VISITATO': 'rgba(255, 204, 0, 0.25)',
                'VISITARE': 'rgba(255, 255, 0, 0.25)',
                'TELEFONATO': 'rgba(175, 122, 197, 0.25)',
                'TELEFONARE': 'rgba(255, 102, 255, 0.25)',
                'INVIATA MAIL': 'rgba(0, 153, 0, 0.25)',
                'INVIARE EMAIL': 'rgba(102, 255, 102, 0.25)',
                'INVIO E-MAIL SFC': 'rgba(0, 153, 0, 0.25)',
                'PARTECIPAZIONE WEBINAR': 'rgba(52, 152, 219, 0.25)',
                'SOLLECITARE OFFERTA COMMERCIALE': 'rgba(0, 0, 0, 0.1)'
            }


            # --------
            # GRAFICI 
            # --------

            # --- TRACCIAMENTO DEI TOTALI COMPLESSIVI PER ATTIVITÀ PER I TOOLTIP ---
            totali_globali_attivita = pivot_df.sum(axis=0).to_dict()


            # PLOT 1: Quote Anagrafiche per Attività
            if tipo_visualizzazione == "Quote Anagrafiche per Attività":

                st.write(f"**Quote Anagrafiche per Attività**")
                st.caption("Di seguito le quote delle anagrafiche (cliente, lead e prospect) per ogni tipologia di attività")
                
                # 1. Calcoliamo i valori assoluti solo per l'hovertemplate (al passaggio del mouse)
                df_assoluto = pivot_df.T.reset_index().melt(id_vars='TIPO EVENTO', var_name='Target Anagrafica', value_name='Conteggio')

                # Calcolo percentuali verticali
                pivot_perc = pivot_df.div(pivot_df.sum(axis=0), axis=1) * 100
                df_long = pivot_perc.T.reset_index()
                df_long = df_long.melt(id_vars='TIPO EVENTO', var_name='Target Anagrafica', value_name='Percentuale')
                
                # Uniamo i due dataframe per non perdere i dati nell'hover
                df_long['Conteggio'] = df_assoluto['Conteggio']
                
                # Mappiamo il totale dell'attività globale per ciascuna riga
                df_long['Totale_Attivita_Team'] = df_long['TIPO EVENTO'].map(totali_globali_attivita)
                
                # Creiamo la stringa della percentuale da mostrare come etichetta principale
                df_long['Etichetta_Perc'] = df_long['Percentuale'].apply(lambda x: f"<b>{x:.1f}%</b>" if x > 0 else "")

                # Grafico BARRE AFFIANCATE (Usiamo Etichetta_Perc come testo del grafico)
                fig_bar = px.bar(
                    df_long,
                    y='TIPO EVENTO',
                    x='Percentuale',
                    color='Target Anagrafica',
                    text='Etichetta_Perc',  
                    barmode='group',
                    orientation='h',
                    color_discrete_map={'Cliente': '#5dade2', 'Lead': '#58d68d', 'Prospect': '#ec7063'},
                    custom_data=['Target Anagrafica', 'Conteggio', 'Totale_Attivita_Team']
                )
                
                fig_bar.update_traces(
                    hovertemplate=(
                        "<b>Attività: %{y}</b><br>"
                        "Target: %{customdata[0]}<br>"
                        "Eventi sul Target: %{customdata[1]}<br>"
                        "Eventi Tot. Attività: %{customdata[2]}<br>"
                        "Quota Target: %{x:.1f}%<extra></extra>"
                    ),
                    textposition="outside",             
                    cliponaxis=False,                   
                    outsidetextfont=dict(color="#2c3e50", size=13) 
                )
                
                fig_bar.update_layout(xaxis_title = "Quota (%)")
                fig_bar.update_xaxes(ticksuffix= "%")
                
                # Estendiamo l'asse X del 15% per dare respiro alle scritte a destra
                massimo_x = df_long['Percentuale'].max()
                fig_bar.update_layout(xaxis=dict(range=[0, massimo_x * 1.15] if massimo_x > 0 else [0, 100]))

                # Render del Grafico principale delle quote
                st.plotly_chart(fig_bar, use_container_width=True)


            # PLOT 2: Volume Attività per Anagrafica
            else:

                st.write(f"**Volume Attività per Anagrafica**")
                st.caption("Di seguito il volume totale di attività svolte per le tre anagrafiche (cliente, lead, prospect)")
                
                df_long = pivot_df.reset_index()
                df_long = df_long.melt(id_vars='index', var_name='Tipo Evento', value_name='Conteggio')
                df_long.columns = ['Tipo Anagrafica', 'Tipo Evento', 'Conteggio']
                
                pivot_perc_verticale = pivot_df.div(pivot_df.sum(axis=0), axis=1) * 100
                df_perc_long = pivot_perc_verticale.reset_index().melt(id_vars='index', var_name='Tipo Evento', value_name='Percentuale')
                
                df_long['Percentuale'] = df_perc_long['Percentuale']
                df_long['Totale_Attivita_Team'] = df_long['Tipo Evento'].map(totali_globali_attivita)
                
                # Grafico BARRE IMPILATE
                fig_bar = px.bar(
                    df_long,
                    y='Tipo Anagrafica',
                    x='Conteggio',
                    color='Tipo Evento',
                    text='Conteggio',              
                    barmode='relative',
                    orientation='h',
                    color_discrete_map=color_mapping_eventi,
                    custom_data=['Tipo Evento', 'Percentuale', 'Totale_Attivita_Team']
                )
                
                fig_bar.update_traces(
                    hovertemplate=(
                        "<b>Target: %{y}</b><br>"
                        "Attività: %{customdata[0]}<br>"
                        "Eventi: %{x}<br>"
                        "Eventi Tot. Attività: %{customdata[2]}<br>"
                        "Quota Target: %{customdata[1]:.1f}%<extra></extra>"
                    ),
                    texttemplate="%{text}",        
                    textposition="inside",         
                    insidetextanchor="middle"      
                )
                
                fig_bar.update_layout(xaxis_title="Numero di Eventi")
                
                # AGGIUNTA TOTALI COMPLESSIVI SULLA CIMA DELLA BARRA IMPILATA
                totali_anagrafica = pivot_df.sum(axis=1)
                
                for anagrafica, totale in totali_anagrafica.items():
                    if totale > 0:
                        fig_bar.add_annotation(
                            y=anagrafica,
                            x=totale,
                            text=f"<b>{totale:.0f}</b>", 
                            showarrow=False,
                            xshift=10,                   
                            yanchor="middle",
                            xanchor="left",
                            font=dict(color="#2c3e50", size=12)
                        )
                        
                massimo_conteggio = totali_anagrafica.max()
                fig_bar.update_layout(xaxis=dict(range=[0, massimo_conteggio * 1.15] if massimo_conteggio > 0 else [0, 10]))

                # Regolazioni estetica e render grafico volumi
                fig_bar.update_layout(
                    yaxis_title="",
                    legend_title="Legenda",
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',  
                    height=450
                )
                fig_bar.update_xaxes(showgrid=True, gridcolor='rgba(200,200,200,0.2)')
                st.plotly_chart(fig_bar, use_container_width=True)


            # --------------------
            # TABELLA RIASSUNTIVA
            # --------------------

            st.write("")
            

            # =========================================================================
            # TABELLA 1: Quote delle anagrafiche sul totale attività (Sincronizzata con "Quote Anagrafiche per Attività")
            # =========================================================================
            if tipo_visualizzazione == "Quote Anagrafiche per Attività":
                
                # Calcolo percentuali e totali per asse verticale (Attività)
                df_totali_attivita = pivot_df.sum(axis=0)
                
                # Generiamo i dati strutturati in modo dinamico
                righe_tabella = []
                
                # Seguiamo l'ordine del grafico (dall'alto verso il basso) invertendo le colonne della pivot
                for attivita in pivot_df.columns[::-1]:
                    totale_att = df_totali_attivita[attivita]
                    
                    # --- MODIFICA: Spostiamo il 'Totale Eventi' all'inizio del dizionario ---
                    riga = {
                        "Attività": attivita,
                        "Totale Eventi": totale_att
                    }
                    
                    # Cicliamo dinamicamente sull'ordine grafico per popolare i target esistenti a destra
                    for target in ordine_grafico:
                        conteggio = pivot_df.loc[target, attivita] if target in pivot_df.index else 0
                        quota = (conteggio / totale_att * 100) if totale_att > 0 else 0.0
                        
                        riga[f"{target} (Ev.)"] = conteggio
                        riga[f"{target} (%)"] = f"{quota:.1f}%"
                    
                    righe_tabella.append(riga)
                
                df_riepilogo_tabella = pd.DataFrame(righe_tabella).set_index("Attività")
                
                # Mappa dei colori ACCESI e SOLIDI delle attività presi direttamente dal plot
                colori_attivita_accesi = {
                    'TELEFONATO': '#af7ac5',     # Viola acceso
                    'VISITATO': '#ffcc00',       # Giallo acceso
                    'INVIATA MAIL': '#009900',    # Verde acceso
                    'VISITARE': '#ffff00',       
                    'TELEFONARE': '#ff66ff',     
                    'INVIARE EMAIL': '#66ff66',   
                    'INVIO E-MAIL SFC': '#009900', 
                    'PARTECIPAZIONE WEBINAR': '#3498db', 
                    'SOLLECITARE OFFERTA COMMERCIALE': '#2c3e50' 
                }

                # --- APPLICAZIONE STILE RIGIDO E ACCESO SULLE PRIME DUE COLONNE ---
                def stile_tabella_1(row):
                    styles = [''] * len(row)
                    # Recuperiamo il nome dell'attività corrente (l'indice della riga)
                    attivita_corrente = row.name.upper()
                    
                    for i, col in enumerate(row.index):
                        # COLONNA 2 (Totale Eventi): prende il colore acceso dell'attività corrente, testo nero e grassetto
                        if col == "Totale Eventi":
                            colore_vivido = colori_attivita_soft.get(attivita_corrente, 'rgba(200,200,200,0.25)')
                            # Estraiamo il colore solido corrispondente per accenderlo
                            for chiave_att, esadecimale in colori_attivita_accesi.items():
                                if chiave_att in attivita_corrente:
                                    colore_vivido = esadecimale
                                    break
                            styles[i] = f"background-color: {colore_vivido}; color: black; font-weight: bold;"
                        else:
                            # Tutte le colonne dei target a destra mantengono il loro colore soft/sbiadito
                            if "Prospect" in col:
                                styles[i] = f"background-color: {colori_anagrafiche_soft['Prospect']}; color: black;"
                            elif "Lead" in col:
                                styles[i] = f"background-color: {colori_anagrafiche_soft['Lead']}; color: black;"
                            elif "Cliente" in col:
                                styles[i] = f"background-color: {colori_anagrafiche_soft['Cliente']}; color: black;"
                    return styles

                # COLONNA 1 (Indice / Nomi riga): Forziamo lo stesso colore acceso e testo nero in grassetto
                def stile_indice_tabella_1(index_series):
                    colori_indici = []
                    for idx in index_series:
                        idx_upper = idx.upper()
                        colore_trovato = 'rgba(200,200,200,0.15)' # Fallback grigio soft se non censito
                        for chiave_att, esadecimale in colori_attivita_accesi.items():
                            if chiave_att in idx_upper:
                                colore_trovato = esadecimale
                                break
                        colori_indici.append(f"background-color: {colore_trovato}; color: black; font-weight: bold;")
                    return colori_indici

                # Combiniamo gli stili per accendere le prime due colonne
                df_styled_1 = df_riepilogo_tabella.style.apply(stile_tabella_1, axis=1).apply_index(stile_indice_tabella_1, axis=0)

                # Generiamo le regole di formattazione per tutte le colonne numeriche dei target
                config_colonne_1 = {"Totale Eventi": st.column_config.NumberColumn(format="%d")}
                for target in ordine_grafico:
                    config_colonne_1[f"{target} (Ev.)"] = st.column_config.NumberColumn(format="%d")

                col0, col1, col2 = st.columns([0.1, 2, 0.1])
                with col1:
                    st.dataframe(
                        df_styled_1, 
                        use_container_width=True,
                        column_config=config_colonne_1
                    )


            # =========================================================================
            # TABELLA 2: Mix di attività per ogni anagrafica (Sincronizzata con "Volume Attività per Anagrafica")
            # =========================================================================
            else:
                # Forza il riordinamento righe della pivot secondo l'ordine del grafico
                pivot_df_ordinata = pivot_df.reindex(ordine_grafico, fill_value=0)
                df_totali_anagrafica = pivot_df_ordinata.sum(axis=1)
                
                # Generiamo i dati strutturati per la tabella invertita
                righe_tabella_invertita = []
                for anagrafica in pivot_df_ordinata.index:
                    totale_ana = df_totali_anagrafica[anagrafica]
                    
                    riga_dati = {
                        "Target Anagrafica": anagrafica,
                        "Totale Attività": totale_ana
                    }
                    
                    # Cicliamo dinamicamente su TUTTE le attività effettivamente presenti nella pivot
                    for attivita in pivot_df_ordinata.columns:
                        conteggio_evento = pivot_df_ordinata.loc[anagrafica, attivita]
                        quota_evento = (conteggio_evento / totale_ana * 100) if totale_ana > 0 else 0.0
                        
                        # Formattazione pulita mantenendo intatta la stringa originale per evitare perdite di matching
                        att_label = attivita.strip().capitalize()
                        riga_dati[f"{att_label} (Ev.)"] = conteggio_evento
                        riga_dati[f"{att_label} (%)"] = f"{quota_evento:.1f}%"
                        
                    righe_tabella_invertita.append(riga_dati)
                
                df_riepilogo_invertito = pd.DataFrame(righe_tabella_invertita).set_index("Target Anagrafica")
                
                # Mappa dei colori ACCESI e SOLIDI presi dal grafico (Senza alcuna trasparenza)
                colori_anagrafiche_accesi = {
                    'Prospect': '#ec7063',  # Rosso acceso originale
                    'Lead': '#58d68d',     # Verde acceso originale
                    'Cliente': '#5dade2'    # Blu acceso originale
                }

                # --- APPLICAZIONE STILE RIGIDO SULLE DUE COLONNE INIZIALI ---
                def stile_tabella_2(row):
                    styles = [''] * len(row)
                    anagrafica_corrente = row.name 
                    
                    for i, col in enumerate(row.index):
                        # COLONNA 2 (Totale Attività): prende il colore acceso, testo nero e grassetto
                        if col == "Totale Attività":
                            colore_vivido = colori_anagrafiche_accesi.get(anagrafica_corrente, '')
                            styles[i] = f"background-color: {colore_vivido}; color: black; font-weight: bold;"
                        else:
                            # Tutte le altre colonne delle attività mantengono i loro colori soft originari
                            col_upper = col.upper()
                            for att_chiave, colore_rgb in colori_attivita_soft.items():
                                if att_chiave in col_upper:
                                    styles[i] = f"background-color: {colore_rgb}; color: black;"
                                    break
                    return styles

                # COLONNA 1 (Indice / Nomi riga): Forziamo lo stesso identico colore acceso e testo nero in grassetto
                def stile_indice_tabella_2(index_series):
                    return [f"background-color: {colori_anagrafiche_accesi.get(idx, '')}; color: black; font-weight: bold;" for idx in index_series]

                # Combiniamo gli stili: apply sulle colonne dati + apply_index sull'asse delle righe (X=0)
                df_styled_2 = df_riepilogo_invertito.style.apply(stile_tabella_2, axis=1).apply_index(stile_indice_tabella_2, axis=0)

                # Generiamo dinamicamente la configurazione per qualsiasi attività apparsa nella pivot
                config_colonne_dinamiche = {"Totale Attività": st.column_config.NumberColumn(format="%d")}
                for attivita in pivot_df_ordinata.columns:
                    config_colonne_dinamiche[f"{attivita.strip().capitalize()} (Ev.)"] = st.column_config.NumberColumn(format="%d")

                col0, col1, col2 = st.columns([0.1, 2, 0.1])
                with col1:
                    st.dataframe(
                        df_styled_2, 
                        use_container_width=True,
                        column_config=config_colonne_dinamiche
                    )


            # ***********************************************************
            # SEZ. 2B - PROFILI STRATEGICI (Cliente vs Lead vs Prospect)
            # ***********************************************************

            st.write("")
            st.write("")
            st.write("Conversione della tabella in un grafico radar per visualizzare il profilo strategico adottato.")
            st.write("")
            
            # Isoliamo le tre attività principali e i tre target di anagrafica
            attivita_radar = ['TELEFONATO', 'VISITATO', 'INVIATA MAIL']
            
            # Filtriamo il dataframe originale per includere solo ciò che serve al Radar
            df_radar_base = df_temp[
                (df_temp['TIPO ANAGRAFICA'].isin(target_categories)) & 
                (df_temp['TIPO EVENTO'].isin(attivita_radar))
            ].copy()

            if not df_radar_base.empty:
                
                # Incrociamo i dati delle colonne TIPO ANAGRAFICA e TIPO EVENTO. 
                pivot_radar = pd.crosstab(df_radar_base['TIPO ANAGRAFICA'], df_radar_base['TIPO EVENTO'])

                # Riempiamo eventuali attività mancanti con 0 mantenendo tutte le righe e le colonne della matrice
                pivot_radar = pivot_radar.reindex(index=target_categories, columns=attivita_radar, fill_value=0)

                # Riscrive i nomi di righe e colonne da stampatello a "normale"
                pivot_radar.index = [idx.capitalize() for idx in pivot_radar.index]


                # --- LAYOUT AFFIANCATO ---
                col_radar, col_controlli = st.columns([3.2, 0.8])

                with col_controlli:
                    st.write("")
                    st.write("")
                    normalizza_radar = st.toggle(
                        "Normalizzazione dati", 
                        value=True,
                        key="toggle_normalizza_radar"
                    )

                import plotly.graph_objects as go
                fig_radar = go.Figure()

                # Tavolozza Colori Solidi per le linee/anagrafiche
                colori_mappa = {'Cliente': '#5dade2', 'Lead': '#58d68d', 'Prospect': '#ec7063'}
                colori_riempimento = {
                    'Cliente': 'rgba(93, 173, 226, 0.15)',  
                    'Lead': 'rgba(88, 214, 141, 0.15)',      
                    'Prospect': 'rgba(236, 112, 99, 0.15)'   
                }
                
                # Tavolozza Colori Solidi per le attività (estratti dai tuoi colori soft delle tabelle)
                colori_solidi_attivita = {
                    'TELEFONATO': '#af7ac5',     # Viola
                    'VISITATO': '#ffcc00',       # Giallo/Arancio
                    'INVIATA MAIL': '#009900'    # Verde
                }
                
                colori_attivita = {'Telefonato': '#af7ac5', 'Visitato': '#ffcc00', 'Inviata mail': '#009900'}
                colori_riempimento_attivita = {
                    'Telefonato': 'rgba(175, 122, 197, 0.15)',
                    'Visitato': 'rgba(255, 204, 0, 0.15)',
                    'Inviata mail': 'rgba(0, 153, 0, 0.15)'
                }

                # Configurazione asse in base alla normalizzazione
                suffisso_unita = "%" if normalizza_radar else ""


                # =========================================================================
                # SINCRO RADAR 1: Profilo delle Anagrafiche per ogni Attività (Su base Colonna)
                # Sincronizzato nativamente con "Quote Anagrafiche per Attività"
                # =========================================================================
                if tipo_visualizzazione == "Quote Anagrafiche per Attività":
                    
                    # Calcolo percentuali verticali (colonna)
                    totali_per_attivita = pivot_radar.sum(axis=0)
                    pivot_radar_perc = pivot_radar.div(totali_per_attivita, axis=1) * 100
                    pivot_radar_perc = pivot_radar_perc.fillna(0)

                    pivot_radar_plot = pivot_radar_perc.copy() if normalizza_radar else pivot_radar.copy()
                    
                    # Vertici del grafico = le Anagrafiche (Prospect, Lead, Cliente)
                    categorie_radar = list(pivot_radar_plot.index)
                    categorie_radar_chiuso = categorie_radar + [categorie_radar[0]]

                    # Mappa dei colori dei pallini (colonne della Tabella 1 = le Anagrafiche)
                    # Essendo i vertici del radar le anagrafiche, ogni pallino prende il colore del rispettivo Target
                    colori_pallini_anagrafiche = [colori_mappa.get(cat, '#000000') for cat in categorie_radar]
                    colori_pallini_anagrafiche_chiuso = colori_pallini_anagrafiche + [colori_pallini_anagrafiche[0]]

                    # Tracce = le Attività
                    for attivita in pivot_radar_plot.columns:
                        attivita_label = attivita.capitalize()
                        
                        valori_r = list(pivot_radar_plot[attivita])
                        valori_r_chiuso = valori_r + [valori_r[0]]
                        
                        volumi_assoluti = list(pivot_radar[attivita])
                        volumi_assoluti_chiuso = volumi_assoluti + [volumi_assoluti[0]]
                        
                        percentuali = list(pivot_radar_perc[attivita])
                        percentuali_chiuso = percentuali + [percentuali[0]]
                        
                        totale_dell_attivita = totali_per_attivita.loc[attivita]
                        totali_attivita_chiuso = [totale_dell_attivita] * len(valori_r_chiuso)
                        
                        dati_hover_fusi = list(zip(volumi_assoluti_chiuso, percentuali_chiuso, totali_attivita_chiuso))

                        fig_radar.add_trace(go.Scatterpolar(
                            r=valori_r_chiuso,
                            theta=categorie_radar_chiuso,
                            mode='lines+markers',
                            # FIX COLORAZIONE: linea dell'Attività, pallini mappati sui colori dei Target
                            marker=dict(
                                size=10, 
                                symbol='circle',
                                color=colori_pallini_anagrafiche_chiuso,
                                line=dict(width=1, color='white') # Un piccolo bordo bianco per staccare il pallino
                            ),
                            name=attivita_label,
                            fill='toself',
                            fillcolor=colori_riempimento_attivita.get(attivita_label, 'rgba(0,0,0,0)'),
                            line=dict(color=colori_attivita.get(attivita_label), width=2.5),
                            customdata=dati_hover_fusi,
                            hovertemplate=(
                                "<b>Attività: " + attivita_label + "</b><br>"
                                "Target: %{theta}<br>"
                                "Eventi su Target: %{customdata[0]:.0f}<br>"
                                "Totale Eventi Attività: %{customdata[2]:.0f}<br>"
                                "Quota: %{customdata[1]:.1f}%<extra></extra>"
                            )
                        ))


                # =========================================================================
                # SINCRO RADAR 2: Profilo delle Attività per ogni Anagrafica (Su base Riga)
                # Sincronizzato nativamente con "Volume Attività per Anagrafica"
                # =========================================================================
                else:
                    
                    # Calcolo percentuali orizzontali (riga)
                    totali_per_profilo = pivot_radar.sum(axis=1)
                    pivot_radar_perc = pivot_radar.div(totali_per_profilo, axis=0) * 100
                    pivot_radar_perc = pivot_radar_perc.fillna(0)

                    pivot_radar_plot = pivot_radar_perc.copy() if normalizza_radar else pivot_radar.copy()
                    
                    # Vertici del grafico = le Attività (Telefonato, Visitato, Inviata Mail)
                    categorie_radar = list(pivot_radar_plot.columns)
                    categorie_radar_chiuso = [cat.capitalize() for cat in categorie_radar] + [categorie_radar[0].capitalize()]

                    # Mappa dei colori dei pallini (colonne della Tabella 2 = le Attività)
                    # Essendo i vertici del radar le attività, ogni pallino prende il colore della rispettiva Attività
                    colori_pallini_attivita = [colori_solidi_attivita.get(cat.upper(), '#000000') for cat in categorie_radar]
                    colori_pallini_attivita_chiuso = colori_pallini_attivita + [colori_pallini_attivita[0]]

                    # Tracce = le Anagrafiche
                    for anagrafica in pivot_radar_plot.index:
                        valori_r = list(pivot_radar_plot.loc[anagrafica])
                        valori_r_chiuso = valori_r + [valori_r[0]]
                        
                        volumi_assoluti = list(pivot_radar.loc[anagrafica])
                        volumi_assoluti_chiuso = volumi_assoluti + [volumi_assoluti[0]]
                        
                        percentuali = list(pivot_radar_perc.loc[anagrafica])
                        percentuali_chiuso = percentuali + [percentuali[0]]
                        
                        totale_del_profilo = totali_per_profilo.loc[anagrafica]
                        totali_profilo_chiuso = [totale_del_profilo] * len(valori_r_chiuso)
                        
                        dati_hover_fusi = list(zip(volumi_assoluti_chiuso, percentuali_chiuso, totali_profilo_chiuso))

                        fig_radar.add_trace(go.Scatterpolar(
                            r=valori_r_chiuso,
                            theta=categorie_radar_chiuso,
                            mode='lines+markers',
                            # FIX COLORAZIONE: linea del Target, pallini mappati sui colori delle Attività
                            marker=dict(
                                size=10, 
                                symbol='circle',
                                color=colori_pallini_attivita_chiuso,
                                line=dict(width=1, color='white')
                            ),
                            name=anagrafica,
                            fill='toself',
                            fillcolor=colori_riempimento.get(anagrafica, 'rgba(0,0,0,0)'),
                            line=dict(color=colori_mappa.get(anagrafica), width=2.5),
                            customdata=dati_hover_fusi,
                            hovertemplate=(
                                "<b>Profilo: " + anagrafica + "</b><br>"
                                "Attività: %{theta}<br>"
                                "Eventi: %{customdata[0]:.0f}<br>"
                                "Totale Attività Profilo: %{customdata[2]:.0f}<br>"
                                "Quota: %{customdata[1]:.1f}%<extra></extra>"
                            )
                        ))

                # Aggiorniamo i tooltip e il layout generale
                fig_radar.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            showticklabels=True,
                            gridcolor='rgba(200,200,200,0.4)',
                            ticksuffix=suffisso_unita
                        ),
                        angularaxis=dict(
                            gridcolor='rgba(200,200,200,0.4)',
                            tickfont=dict(size=12, weight='bold')
                        ),
                        bgcolor='rgba(0,0,0,0)'
                    ),
                    paper_bgcolor='rgba(0,0,0,0)',
                    height=550, 
                    margin=dict(l=40, r=40, t=25, b=25),
                    
                    # --- CONFIGURAZIONE LEGENDA DI FIANCO VERTICALE ---
                    legend=dict(
                        orientation="v",        
                        yanchor="middle",       
                        y=0.5,                  
                        xanchor="left",         
                        x=1.1,                  
                        title_text=""           
                    )
                )

                # Plottiamo il grafico dentro la colonna di sinistra appena definita
                with col_radar:
                    st.plotly_chart(fig_radar, use_container_width=True)
                    
            else:
                st.info("Dati insufficienti per generare il grafico Radar sulle attività principali.")



            # **************************
            # SEZ. 3 - CUSTUMER JOURNEY
            # **************************

            st.divider()
            st.write("")
            st.write("")
            col1, col2, col3 = st.columns([1.8, 1.9, 0.6])
            with col1:
                st.write(f"#### 3. Panoramica delle transizioni delle attività (Customer Journey)")
                st.write("Questa mappa mostra quale attività segue più frequentemente un'altra sullo stessa azienda, divisa per tipologia anagrafica (cliente, lead e prospect).")
            with col3:
                st.success("✅ Codice Validato")
            st.write("")
         
            # Verifichiamo la presenza delle colonne necessarie (Azienda e Data)
            colonna_azienda = next((c for c in df_events.columns if c in ['RAGIONE SOCIALE', 'NOME AZIENDA', 'CLIENTE', 'AZIENDA']), None)
            colonna_data = next((c for c in df_events.columns if c in ['DATA', 'DATA EVENTO', 'DATA_EVENTO']), None)

            if colonna_azienda and colonna_data:
                # Creiamo una copia pulita per non intaccare il dataframe originale
                df_journey_base = df_temp.copy()
                
                # Assicuriamoci che la data sia in formato datetime e standardizziamo i testi
                df_journey_base[colonna_data] = pd.to_datetime(df_journey_base[colonna_data], errors='coerce')
                df_journey_base['TIPO EVENTO'] = df_journey_base['TIPO EVENTO'].str.upper().str.strip()
                
                # Rimuoviamo righe senza data o senza attività
                df_journey_base = df_journey_base.dropna(subset=[colonna_data, 'TIPO EVENTO', colonna_azienda])
                
                # --- BLOCCO FILTRI LAYOUT ---
                col_f1, col_f2 = st.columns([1.5, 2])
                
                with col_f1:
                    solo_principali_journey = st.checkbox(
                        "Filtra solo attività principali (Telefonato, Visitato, Inviata mail)", 
                        value=True,
                        key="checkbox_journey_principali"
                    )
                    attivita_target = ['TELEFONATO', 'VISITATO', 'INVIATA MAIL']
                
                with col_f2:
                    modalita_heatmap = st.radio(
                        "Mostra dati come:",
                        ["Numero di Transizioni (Valori Assoluti)", "Probabilità di Passaggio (% sulla riga)"],
                        horizontal=True,
                        key="radio_heatmap"
                    )
                # ----------------------------

                st.write("")
                
                # Creiamo 3 colonne affiancate, una per ogni anagrafica target
                st_cols = st.columns([1, 1, 1])
                
                for i, cat in enumerate(target_categories):
                    with st_cols[i]:
                        #st.subheader(f" {cat.capitalize()}")

                        # TITOLO CENTRATO CON HTML
                        st.markdown(f"<h3 style='text-align: center;'>{cat.capitalize()}</h3>", unsafe_allow_html=True)
                        
                        # Filtriamo i dati per la singola anagrafica corrente
                        df_journey = df_journey_base[df_journey_base['TIPO ANAGRAFICA'] == cat].copy()
                        
                        if solo_principali_journey:
                            df_journey = df_journey[df_journey['TIPO EVENTO'].isin(attivita_target)]
                        
                        # 1. Ordiniamo cronologicamente per Azienda e Data
                        df_journey = df_journey.sort_values(by=[colonna_azienda, colonna_data])
                        
                        # 2. Identifichiamo l'attività successiva per la STESSA azienda
                        df_journey['ATTIVITA_SUCCESSIVA'] = df_journey.groupby(colonna_azienda)['TIPO EVENTO'].shift(-1)
                        
                        if solo_principali_journey:
                            df_journey = df_journey[df_journey['ATTIVITA_SUCCESSIVA'].isin(attivita_target)]
                        
                        df_transizioni = df_journey.dropna(subset=['ATTIVITA_SUCCESSIVA']).copy()
                        
                        if not df_transizioni.empty:
                            # 3. Creiamo la matrice di contingenza (Crosstab)
                            matrice_transizione = pd.crosstab(
                                df_transizioni['TIPO EVENTO'], 
                                df_transizioni['ATTIVITA_SUCCESSIVA']
                            )
                            
                            # Forziamo l'indicizzazione per avere sempre gli stessi assi coordinati
                            indici_assi = attivita_target if solo_principali_journey else sorted(list(set(df_journey_base['TIPO EVENTO'])))
                            matrice_transizione = matrice_transizione.reindex(
                                index=indici_assi, 
                                columns=indici_assi, 
                                fill_value=0
                            )
                            
                            # Formattazione etichette assi per la visualizzazione
                            matrice_transizione.index = [idx.capitalize() for idx in matrice_transizione.index]
                            matrice_transizione.columns = [col.capitalize() for col in matrice_transizione.columns]
                            
                            # Calcolo dei valori in base alla modalità selezionata
                            if "Probabilità" in modalita_heatmap:
                                matrice_plot = matrice_transizione.div(matrice_transizione.sum(axis=1), axis=0) * 100
                                matrice_plot = matrice_plot.fillna(0)
                                
                                # Usiamo .map() (sostituisce il vecchio applymap) per formattare i numeri puliti
                                testo_celle = matrice_plot.map(lambda x: f"{x:.1f}%")
                                hovertemplate_heat = "<b>Da:</b> %{y}<br><b>A:</b> %{x}<br><b>Probabilità:</b> %{z:.1f}%<extra></extra>"
                            else:
                                matrice_plot = matrice_transizione.copy()
                                testo_celle = matrice_plot.map(lambda x: f"{x:.0f}")
                                hovertemplate_heat = "<b>Da:</b> %{y}<br><b>A:</b> %{x}<br><b>Conteggio:</b> %{z:.0f} volte<extra></extra>"
                            
                            # 4. Generazione del grafico per la colonna corrente
                            fig_heat = px.imshow(
                                matrice_plot,
                                text_auto=False, # Gestiamo i testi manualmente sotto per evitare bug nativi
                                color_continuous_scale="Blues",
                                labels=dict(x="Attività Successiva ➡️", y="⬅️ Attività Corrente")
                            )
                            
                            # Forziamo Plotly a inserire la matrice di testo e a renderla visibile al centro
                            fig_heat.update_traces(
                                text=testo_celle,
                                texttemplate="%{text}", 
                                selector=dict(type='heatmap'),
                                hovertemplate=hovertemplate_heat
                            )
                            
                            fig_heat.update_layout(
                                # ASSE X (Attività Successiva)
                                xaxis=dict(
                                    side="bottom", 
                                    tickangle=-30 if not solo_principali_journey else 0, 
                                    tickfont=dict(size=12, weight='bold') 
                                ),
                                # ASSE Y (Attività Corrente)
                                yaxis=dict(
                                    tickfont=dict(size=12, weight='bold') 
                                ),
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                coloraxis_showscale=False, 
                                height=380,
                                margin=dict(l=50, r=40, t=10, b=40) # Aumentato leggermente il margine sinistro (l=50) per dare spazio ai testi più grandi sulla Y
                            )
                            
                            st.plotly_chart(fig_heat, use_container_width=True)
                        else:
                            st.info(f"Nessun pattern sequenziale per {cat.lower()}.")
                            
                st.info(
                    "💡 **Come leggere le mappe:** Scegli la categoria di azienda da analizzare (es. *Cliente*). Scegli un'azione (es. *Telefonato*) "
                    "e scorri lungo la riga per osservare quali sono le attività successive più probabili."
                )
            else:
                st.caption("ℹ️ *Nota: Per sbloccare le tre matrici del Customer Journey affiancate, assicurati che il file contenga una colonna temporale (es. 'DATA EVENTO') e una identificativa dell'azienda (es. 'RAGIONE SOCIALE').*")


            
        else:
            st.warning("Colonna 'TIPO EVENTO' non trovata. Impossibile mostrare il dettaglio delle attività.")
            
    else:
        st.error(f"Colonna 'TIPO ANAGRAFICA' non trovata. Colonne presenti: {list(df_events.columns)}")


