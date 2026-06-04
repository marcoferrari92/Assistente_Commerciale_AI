import streamlit as st
import pandas as pd
import plotly.express as px

def coinvolgimento_aziende(df_events):
    """
    Analisi del coinvolgimento delle aziende lato eventi.
    Layout riorganizzato:
    1. Grafico Attività Medie per Azienda + Mediana
    2. Max-Treemap Unificata a 3 Livelli (Commerciale -> Azienda -> Attività)
    3. Tabella Pivot di ripartizione attività
    4. Registro analitico finale degli eventi
    """
    colonna_utente = 'UTENTE'
    colonna_evento = 'TIPO EVENTO'
    colonna_anagrafica = 'TIPO ANAGRAFICA'
    colonna_ragione_sociale = 'RAGIONE SOCIALE'
    
    # Verifichiamo la presenza delle colonne minime necessarie
    if colonna_ragione_sociale in df_events.columns and colonna_utente in df_events.columns:
        st.write("")
        st.write("")
        
        # Copia di sicurezza per non sporcare il dataframe originale
        df_temp = df_events.copy()
        
        # ---------------------------------------------------------
        # FILTRO: Selezione Target Anagrafica
        # ---------------------------------------------------------
        st.write(f"#### Filtro anagrafiche")
        st.write("")
        st.write("")
        scelta_anagrafica = st.selectbox(
            "Seleziona il target di anagrafica aziende da analizzare:",
            ["Tutte le anagrafiche", "Clienti", "Lead", "Prospect"],
            key="aziende_filtro_anagrafica"
        )
        
        if scelta_anagrafica == "Clienti":
            df_temp = df_temp[df_temp[colonna_anagrafica] == 'CLIENTE']
        elif scelta_anagrafica == "Lead":
            df_temp = df_temp[df_temp[colonna_anagrafica] == 'LEAD']
        elif scelta_anagrafica == "Prospect":
            df_temp = df_temp[df_temp[colonna_anagrafica] == 'PROSPECT']
            
        if df_temp.empty:
            st.warning(f"Nessun dato disponibile per la categoria selezionata: {scelta_anagrafica}")
            return

        

        # ---------------------------------------------------------
        # 1. GRAFICO DEL COINVOLGIMENTO MEDIO PER AZIENDA
        # ---------------------------------------------------------
        st.divider()
        st.write("")
        st.write("")
        st.write(f"#### 1. Numero Medio di Attività per Azienda - {scelta_anagrafica}")
        
        df_metrics_utenti = df_temp.groupby(colonna_utente).agg(
            Attivita_Totali=('TIPO EVENTO', 'count'),
            Aziende_Uniche=(colonna_ragione_sociale, 'nunique')
        ).reset_index()
        
        df_metrics_utenti['Attività Medie'] = (df_metrics_utenti['Attivita_Totali'] / df_metrics_utenti['Aziende_Uniche']).round(1)
        stats_utenti = df_metrics_utenti.sort_values(by='Attività Medie', ascending=True)
        
        if not stats_utenti.empty:
            valore_mediana = stats_utenti['Attività Medie'].median()
            
            fig_bar = px.bar(
                stats_utenti, 
                x='Attività Medie', 
                y=colonna_utente, 
                orientation='h', 
                text='Attività Medie',
                color='Attività Medie', 
                color_continuous_scale='Blues',
                hover_data={'Attivita_Totali': True, 'Aziende_Uniche': True}
            )
            
            fig_bar.update_traces(
                hovertemplate="<b>Commerciale: %{y}</b><br>Media Attività/Azienda: %{x}<br>Azioni Totali: %{customdata[0]}<br>Aziende Gestite: %{customdata[1]}<extra></extra>"
            )
            
            fig_bar.add_vline(
                x=valore_mediana, 
                line_dash="dash", 
                line_color="red",
                line_width=2,
                annotation_text=f"Mediana Team: {valore_mediana:.1f}", 
                annotation_position="top right"
            )
            
            fig_bar.update_layout(
                xaxis_title="Media Attività per Azienda",
                yaxis_title="Commerciale",
                showlegend=False,
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            fig_bar.update_xaxes(showgrid=True, gridcolor='rgba(200,200,200,0.2)')
            st.plotly_chart(fig_bar, use_container_width=True)
        
        


        # ---------------------------------------------------------
        # 2. MAX-TREEMAP UNIFICATA (Commerciale -> Azienda -> Sotto-Attività)
        # ---------------------------------------------------------
        st.divider()
        st.write("")
        st.write("")
        
        # --- LAYOUT SUPERIORE IN DUE COLONNE ---
        col1, col2 = st.columns([3.5, 1.0])
        
        with col1:
            st.write(f"#### 2. Mappa di ripartizione")
            
            # Spiegazione integrata all'interno di un popover pulito ed elegante
            with st.popover("💡 GUIDA"):
                st.write(f"""
                 Ripartizione delle 50 aziende più coinvolte per il commerciale di riferimento.
                 * Fai clic sul blocco di un commerciale o sul quadrato di un'azienda per scendere nei livelli ed esplorare il mix di interazioni.
                 * **N.B.** Ogni azienda viene assegnata a un solo commerciale (anche se le attività sono state fatte da più utenti), in particolare viene assegnata all'utente che ha svolto più attività con quell'azienda.
                 """)
        
        with col2:
            st.write("")  # Piccolo spazio per allineare visivamente il box al titolo
            st.success("✅ Codice Validato")
            
        st.write("")
        
        st.warning(scelta_anagrafica)

        # --- LOGICA GENERALIZZATA PER LE ATTIVITÀ DEL RADAR (CORRETTO df_temp) ---
        # Sostituito df_filtered con df_temp per correggere il NameError
        attivita_disponibili = [
            att for att in df_temp[colonna_evento].unique() 
            if pd.notna(att) and str(att).strip().upper() not in ['NAN', 'NONE', '', 'NAT']
        ]
        
        attivita_radar_target_default = ['TELEFONATO', 'VISITATO', 'INVIATA MAIL']
        ha_scelto_tutte = any(att not in attivita_radar_target_default for att in attivita_disponibili)
        
        if ha_scelto_tutte:
            attivita_radar_target = attivita_disponibili
        else:
            attivita_radar_target = [att for att in attivita_radar_target_default if att in attivita_disponibili]

        # Sostituito df_filtered con df_temp anche qui
        df_tree_base = df_temp[df_temp[colonna_evento].isin(attivita_radar_target)].copy()

        if not df_tree_base.empty:
            solo_principali_tree = st.checkbox(
                "Isola solo attività principali nella mappa (Telefonato, Visitato, Inviata mail)", 
                value=True,
                key="checkbox_unificato_tree_principali"
            )
            attivita_target_tree = ['TELEFONATO', 'VISITATO', 'INVIATA MAIL']
            
            if solo_principali_tree:
                df_tree_base = df_tree_base[df_tree_base[colonna_evento].isin(attivita_target_tree)]
                
            top_50_aziende = df_tree_base[colonna_ragione_sociale].value_counts().head(50).index
            df_tree_filtrato = df_tree_base[df_tree_base[colonna_ragione_sociale].isin(top_50_aziende)].copy()
            
            if not df_tree_filtrato.empty:
                df_top_comm = df_tree_filtrato.groupby([colonna_ragione_sociale, colonna_utente]).size().reset_index(name='Conteggio')
                df_riferimento = df_top_comm.sort_values('Conteggio', ascending=False).drop_duplicates(colonna_ragione_sociale)
                df_riferimento = df_riferimento[[colonna_ragione_sociale, colonna_utente]]
                df_riferimento.columns = ['Azienda', 'Commerciale Prevalente']
                
                df_tree_filtrato['Attività'] = df_tree_filtrato[colonna_evento].str.capitalize()
                df_tree_filtrato['Azienda'] = df_tree_filtrato[colonna_ragione_sociale]
                
                df_aggregato_grezzo = df_tree_filtrato.groupby(['Azienda', 'Attività']).size().reset_index(name='Conteggio Eventi')
                df_tree_unificato = pd.merge(df_aggregato_grezzo, df_riferimento, on='Azienda', how='left')
                
                # Definizione dei colori per il livello finale delle attività
                colori_attivita_tree = {
                    'Visitato': '#ffcc00',       
                    'Telefonato': '#af7ac5',     
                    'Inviata mail': '#009900',    
                    'Visitare': '#ffff00',       
                    'Telefonare': '#ff66ff',     
                    'Inviare email': '#66ff66',   
                    'Envio e-mail sfc': '#009900', 
                    'Partecipazione webinar': '#3498db', 
                    'Sollecitare offerta commerciale': '#2c3e50'
                }
                
                # Costruiamo la Treemap a 3 Livelli Gerarchici
                fig_max_tree = px.treemap(
                    df_tree_unificato,
                    path=['Commerciale Prevalente', 'Azienda', 'Attività'],
                    values='Conteggio Eventi',
                    color='Attività',
                    color_discrete_map=colori_attivita_tree,
                    height=650
                )
                
                # --- FIX VISIVO: FORZATURA DEL COLORE NEUTRO SUI LIVELLI INTERMEDI ---
                # Estraiamo i metadati dei nodi generati da Plotly per mappare i livelli gerarchici
                nomi_nodi = fig_max_tree.data[0].labels
                id_nodi = fig_max_tree.data[0].ids
                
                colori_uniformati = []
                for label, id_nodo in zip(nomi_nodi, id_nodi):
                    # Contiamo quanti '/' ci sono nell'ID del nodo per capire il livello gerarchico:
                    # Livello 0 (Commerciale) -> Nessun '/' o 1 elemento
                    # Livello 1 (Azienda) -> Es. "Nome Commerciale/Nome Azienda"
                    # Livello 2 (Attività) -> Es. "Nome Commerciale/Nome Azienda/Telefonato"
                    profondita = id_nodo.count('/')
                    
                    if profondita == 0:
                        # Macro-blocco del Commerciale: Grigio di struttura leggermente più scuro
                        colori_uniformati.append('#dcdde1')
                    elif profondita == 1:
                        # Blocco intermedio dell'Azienda: Grigio neutro pulito (Evita l'effetto macchia)
                        colori_uniformati.append('#f5f6fa')
                    else:
                        # Sotto-attività finale: applichiamo il rispettivo colore custom registrato
                        colori_uniformati.append(colori_attivita_tree.get(label, '#f5f6fa'))
                
                # Iniettiamo la nuova lista di colori uniformata direttamente nei dati del tracciato
                fig_max_tree.data[0].marker.colors = colori_uniformati
                
                fig_max_tree.update_traces(
                    textinfo="label+value",
                    texttemplate="<b>%{label}</b><br>Eventi: %{value}",
                    hovertemplate="<b>%{label}</b><br>Volume totale registrato: %{value}<extra></extra>",
                    insidetextfont=dict(size=13),
                    textposition="middle center",
                    marker=dict(
                        line=dict(
                            width=1.5,          
                            color='#ffffff'     
                        )
                    )
                )
                
                fig_max_tree.update_layout(
                    margin=dict(t=30, l=10, r=10, b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.03,
                        xanchor="center",
                        x=0.5,
                        title_text="Legenda Attività (Entra nell'azienda per visualizzare la scomposizione a colori)"
                    )
                )
                st.plotly_chart(fig_max_tree, use_container_width=True)
            else:
                st.info("Dati insufficienti per generare la Treemap unificata.")


        st.markdown("---")

        # ---------------------------------------------------------
        # 3. TABELLA PIVOT CON IL DETTAGLIO ATTIVITÀ
        # ---------------------------------------------------------
        st.write("")
        st.write("")
        st.write("#### Dettaglio Attività per Azienda")
        
        pivot_aziende = df_temp.pivot_table(
            index=colonna_ragione_sociale, 
            columns=colonna_evento, 
            values=colonna_utente, 
            aggfunc='count', 
            fill_value=0
        ).reset_index()
        
        colonne_attivita = [c for c in pivot_aziende.columns if c != colonna_ragione_sociale]
        pivot_aziende['TOTALE'] = pivot_aziende[colonne_attivita].sum(axis=1)
        
        comm_riferimento = df_temp.groupby(colonna_ragione_sociale)[colonna_utente].unique().apply(lambda x: ", ".join(x)).reset_index()
        comm_riferimento.columns = [colonna_ragione_sociale, 'Commerciali']
        
        df_finale_aziende = pd.merge(pivot_aziende, comm_riferimento, on=colonna_ragione_sociale)
        cols = [colonna_ragione_sociale, 'TOTALE'] + list(colonne_attivita) + ['Commerciali']
        df_finale_aziende = df_finale_aziende[cols].sort_values(by='TOTALE', ascending=False)
        
        st.dataframe(df_finale_aziende, hide_index=True, use_container_width=True)

        st.markdown("---")

        # ---------------------------------------------------------
        # 4. REGISTRO ANALITICO FINALE
        # ---------------------------------------------------------
        st.write(f"### Dettaglio events ({len(df_events)} record)")
        
        col_view = ['UTENTE', 'DATA', 'ORA EVENTO', 'TIPO EVENTO', 'RAGIONE SOCIALE', 'NOTE']
        col_presenti = [c for c in col_view if c in df_events.columns]
        
        df_DATA_pulita = df_events[col_presenti].sort_values(by=['DATA', 'ORA EVENTO'], ascending=False)
        
        st.dataframe(
            df_DATA_pulita.style.format({
                'DATA': lambda x: pd.to_datetime(x).strftime('%d/%m/%Y') if pd.notnull(x) else "-"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.error(f"Colonne richieste non trovate. Assicurati che nel file ci siano 'RAGIONE SOCIALE' e 'UTENTE'.")