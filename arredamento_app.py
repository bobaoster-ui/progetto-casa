import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. CONFIGURAZIONE
st.set_page_config(page_title="Monitoraggio Arredamento", layout="wide", page_icon="🏠")

# 2. CONNESSIONE
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. LOGICA MENU
st.title("🏠 Monitoraggio Spese Arredamento")
stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]
opzioni_menu = ["Riepilogo"] + stanze_reali
selezione = st.sidebar.selectbox("Vai a:", opzioni_menu)

# --- CASO A: RIEPILOGO CON GRAFICI ---
if selezione == "Riepilogo":
    st.subheader("📊 Analisi Investimento Totale")

    totale_confermato = 0
    totale_potenziale = 0
    dati_per_grafico = []

    with st.spinner("Elaborazione grafici..."):
        for s in stanze_reali:
            try:
                temp_df = conn.read(worksheet=s, ttl=0)
                if temp_df is not None and not temp_df.empty:
                    temp_df.columns = [str(c).strip() for c in temp_df.columns]
                    col_prezzo = next((c for c in ['Importo Totale', 'Costo', 'Prezzo'] if c in temp_df.columns), None)
                    col_scelta = next((c for c in ['Acquista S/N', 'S/N', 'Acquistato', 'Scelta'] if c in temp_df.columns), None)

                    if col_prezzo:
                        temp_df[col_prezzo] = pd.to_numeric(temp_df[col_prezzo], errors='coerce').fillna(0)
                        s_pot = temp_df[col_prezzo].sum()
                        totale_potenziale += s_pot

                        s_conf = 0
                        if col_scelta:
                            temp_df[col_scelta] = temp_df[col_scelta].astype(str).str.strip().str.upper()
                            s_conf = temp_df[(temp_df[col_scelta] == 'S') | (temp_df[col_scelta] == '1')][col_prezzo].sum()

                        totale_confermato += s_conf
                        dati_per_grafico.append({"Stanza": s.capitalize(), "Confermato": s_conf, "Totale": s_pot})
            except:
                continue

    # Metriche principali
    c1, c2, c3 = st.columns(3)
    c1.metric("CONFERMATO (S)", f"{totale_confermato:,.2f} €")
    c2.metric("TOTALE (S+N)", f"{totale_potenziale:,.2f} €")
    c3.metric("DA DECIDERE", f"{totale_potenziale - totale_confermato:,.2f} €")

    st.divider()

    # Grafici
    if dati_per_grafico:
        g1, g2 = st.columns(2)
        df_plot = pd.DataFrame(dati_per_grafico)

        with g1:
            st.markdown("##### Distribuzione Spese per Stanza")
            fig_bar = px.bar(df_plot, x="Stanza", y=["Confermato", "Totale"], barmode="group",
                             color_discrete_sequence=["#2ecc71", "#e74c3c"])
            st.plotly_chart(fig_bar, use_container_width=True)

        with g2:
            st.markdown("##### Stato Budget Totale")
            fig_pie = px.pie(values=[totale_confermato, totale_potenziale - totale_confermato],
                             names=["Confermato (S)", "Ancora da decidere (N)"],
                             color_discrete_sequence=["#2ecc71", "#ecf0f1"], hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

# --- CASO B: STANZA SINGOLA CON DROPDOWN ---
else:
    st.subheader(f"Dettaglio: {selezione.capitalize()}")
    try:
        df = conn.read(worksheet=selezione, ttl=0)
        if df is not None:
            # Pulizia nomi colonne per sicurezza
            df.columns = [str(c).strip() for c in df.columns]

            # Identifichiamo la colonna S/N per il dropdown
            col_scelta = next((c for c in ['Acquista S/N', 'S/N', 'Acquistato', 'Scelta'] if c in df.columns), None)

            # Configurazione editor: trasforma la colonna S/N in una lista di scelta
            config_colonne = {}
            if col_scelta:
                config_colonne[col_scelta] = st.column_config.SelectboxColumn(
                    "Acquista?",
                    options=["S", "N"],
                    required=True,
                )

            df_edit = st.data_editor(
                df,
                use_container_width=True,
                hide_index=True,
                column_config=config_colonne,
                key=f"ed_{selezione}",
                num_rows="dynamic"
            )

            if st.button(f"💾 SALVA MODIFICHE {selezione.upper()}"):
                with st.spinner("Salvataggio..."):
                    conn.update(worksheet=selezione, data=df_edit)
                    st.success("Dati salvati!")
                    st.balloons()
                    st.rerun()
    except Exception as e:
        st.error(f"Errore: {e}")
