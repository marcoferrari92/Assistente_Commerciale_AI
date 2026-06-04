import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go

def render_grafico_torta(data, values_col, names_col, titolo, tipo="numerico"):
    """
    Renderizza un grafico a torta con stile fisso e ordine orario costante.
    """
    palette = {
        "PREVENTIVO": "#A2D2FF",  
        "ORDINE APERTO": "#B4E197", 
        "ORDINE": "#4E944F"         
    }
    ordine_fisso = ["PREVENTIVO", "ORDINE APERTO", "ORDINE"]

    fig = px.pie(
        data, 
        values=values_col, 
        names=names_col,
        title=titolo,
        hole=0.4,
        color=names_col,
        color_discrete_map=palette,
        category_orders={names_col: ordine_fisso} 
    )

    if tipo == "soldi":
        testo_etichette = '%{label}<br>%{percent}<br>€%{value:,.2f}'
    else:
        testo_etichette = '%{label}<br>%{percent}<br>N. %{value}'

    fig.update_traces(
        textinfo='percent+value+label',
        texttemplate=testo_etichette,
        pull=[0.05] * len(data),
        marker=dict(line=dict(color='#FFFFFF', width=2)),
        sort=False 
    )

    fig.update_layout(
        height=500, 
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="center", 
            x=0.5,
            traceorder="normal"
        ),
        margin=dict(t=100, b=20, l=20, r=20),
        title_x=0.35 
    )
    st.plotly_chart(fig, use_container_width=True)


def plot_distribuzione_ordini(df_target):
    """
    Renderizza l'istogramma e il BoxPlot combinati per la distribuzione dei volumi economici.
    """
    if df_target.empty:
        st.warning("Nessun dato disponibile.")
        return

    df_plot = df_target.copy()

    if 'DATA' in df_plot.columns:
        df_plot['DATA_Str'] = pd.to_datetime(df_plot['DATA']).dt.strftime('%d/%m/%Y')
    else:
        df_plot['DATA_Str'] = "N.D."

    if 'bin_size' not in st.session_state:
        st.session_state.bin_size = 1000
        
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.5, 0.5]
    )

    palette = {
        "PREVENTIVO": "#A2D2FF",    
        "ORDINE APERTO": "#B4E197", 
        "ORDINE": "#4E944F"         
    }
    stadi = ["PREVENTIVO", "ORDINE APERTO", "ORDINE"]

    for stadio in stadi:
        df_stadio = df_plot[df_plot['TIPOLOGIA DOC.'] == stadio]
        if df_stadio.empty: 
            continue

        vals = df_stadio['TOTALE']

        # ISTOGRAMMA (Row 2)
        fig.add_trace(
            go.Histogram(
                x=vals,
                name=stadio,
                marker_color=palette[stadio],
                opacity=0.6,
                xbins=dict(size=st.session_state.bin_size),
                marker_line=dict(width=1, color='white'),
                legendgroup=stadio
            ),
            row=2, col=1
        )

        # BOXPLOT (Row 1)
        fig.add_trace(
            go.Box(
                x=vals,
                name=stadio,
                marker_color=palette[stadio],
                boxpoints='all',
                jitter=0.5,      
                pointpos=0,
                legendgroup=stadio,
                showlegend=False,
                orientation='h',
                customdata=df_stadio[['DATA_Str', 'ID DOCUMENTO', 'CLIENTE', 'TITOLO', 'CODICE GESTIONALE UTENTE']],
                hovertemplate=(
                    "<b>TOTALE Articoli:</b> €%{x:,.2f}<br>" +
                    "<b>DATA:</b> %{customdata[0]}<br>" +
                    "<b>ID:</b> %{customdata[1]}<br>" +
                    "<b>CLIENTE:</b> %{customdata[2]}<br>" +
                    "<b>Titolo:</b> %{customdata[3]}<br>" +
                    "<b>UTENTE:</b> %{customdata[4]}<br>" +
                    "<extra></extra>"
                )
            ),
            row=1, col=1
        )

    fig.update_layout(
        height=1000,
        barmode='overlay',
        margin=dict(t=50, b=50, l=50, r=50),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
        xaxis=dict(
            type='linear',
            exponentformat='none',
            gridcolor='lightgray'
        )
    )
    fig.update_xaxes(title_text="Importo Documento (TOTALE articoli) (€)", row=2, col=1)
    fig.update_yaxes(type="log", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

    # SLIDER FASCE DI PREZZO
    col1, col2, col3 = st.columns(3)
    with col2:
        st.slider(
            "Seleziona le fasce di prezzo per l'istogramma (€)", 
            min_value=100, 
            max_value=10000, 
            value=1000, 
            step=100,
            format="%d €", 
            key="bin_size"
        )


def mostra_panoramica_ordini(df_orders_pulito):
    """
    Funzione orchestratrice principale richiamata dall'app per mostrare la sezione Panoramica.
    """
    # 1. CONTEGGI QUANTITÀ E VOLUMI PER LA PANORAMICA
    conteggio_qty = df_orders_pulito['TIPOLOGIA DOC.'].value_counts().reset_index()
    conteggio_qty.columns = ['TIPOLOGIA DOC.', 'Conteggio'] 

    conteggio_vol = df_orders_pulito.groupby('TIPOLOGIA DOC.')['TOTALE'].sum().reset_index()

    with st.expander("📊 Panoramica Quantità e Volumi"):
        if not conteggio_qty.empty and not conteggio_vol.empty:
            col_sinistra, col_destra = st.columns(2)

            with col_sinistra:
                render_grafico_torta(
                    data=conteggio_qty, 
                    values_col='Conteggio', 
                    names_col='TIPOLOGIA DOC.', 
                    titolo="N. Documenti Univoci",
                    tipo="numerico"
                )
            
            with col_destra:
                render_grafico_torta(
                    data=conteggio_vol, 
                    values_col='TOTALE', 
                    names_col='TIPOLOGIA DOC.', 
                    titolo="Valore Economico TOTALE",
                    tipo="soldi"
                )
        
        # 2. METRICHE (Media, Mediana, Percentuali)
        mediane = df_orders_pulito.groupby('TIPOLOGIA DOC.')['TOTALE'].median().reset_index()
        mediane.columns = ['TIPOLOGIA DOC.', 'Mediana (€)']
        
        df_riepilogo = pd.merge(conteggio_qty, conteggio_vol, on='TIPOLOGIA DOC.')
        df_riepilogo = pd.merge(df_riepilogo, mediane, on='TIPOLOGIA DOC.')
        
        tot_qty = df_riepilogo['Conteggio'].sum()
        tot_vol = df_riepilogo['TOTALE'].sum()
        df_riepilogo['% Qty'] = (df_riepilogo['Conteggio'] / tot_qty * 100).round(1).astype(str) + '%'
        df_riepilogo['% Vol'] = (df_riepilogo['TOTALE'] / tot_vol * 100).round(1).astype(str) + '%'
        
        df_riepilogo['Media (€)'] = (df_riepilogo['TOTALE'] / df_riepilogo['Conteggio'])
        
        ORDINE_fisso = ["PREVENTIVO", "ORDINE APERTO", "ORDINE"]
        df_riepilogo['TIPOLOGIA DOC.'] = pd.Categorical(df_riepilogo['TIPOLOGIA DOC.'], categories=ORDINE_fisso, ordered=True)
        df_riepilogo = df_riepilogo.sort_values('TIPOLOGIA DOC.')
        
        colonne_finali = ['TIPOLOGIA DOC.', 'Conteggio', '% Qty', 'TOTALE', '% Vol', 'Media (€)', 'Mediana (€)']

        st.write("")
        st.dataframe(
            df_riepilogo[colonne_finali].style.format({
                'TOTALE': '€ {:,.2f}',
                'Media (€)': '€ {:,.2f}',
                'Mediana (€)': '€ {:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
        st.caption("Nota: I dati sopra riportati sono raggruppati per **ID DOCUMENTO**.")
        
        # 3. GRAFICI DI DISTRIBUZIONE (Istogramma + BoxPlot)
        st.divider()
        st.write("#### Distribuzione Ordini e Preventivi")
        st.info("""
        **Come leggere questo grafico:**
        * **Istogramma:** Indica le fasce di prezzo dove si concentrano i tuoi volumi.
        * **Box Plot:** La linea centrale è la **Mediana**. I punti isolati sono gli **Outliers** (⚠️ ordini eccezionalmente grandi -> verificare).
        """)
        plot_distribuzione_ordini(df_orders_pulito)
