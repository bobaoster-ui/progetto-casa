import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import time
import os
import signal

# Configurazione Pagina
st.set_page_config(page_title="Home Decor Cloud v9.2", page_icon="🏠", layout="wide")

# Connessione a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def pulisci_df(df):
    """Pulisce e converte i dati dal foglio Google"""
    df.columns = [str(c).strip() for c in df.columns]
    if 'Note' not in df.columns: df['Note'] = ""
    if 'Acquista S/N' not in df.columns: df['Acquista S/N'] = "N"

    for col in ['Acquistato', 'Costo', 'Importo Totale']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['Importo Totale'] = df['Acquistato'] * df['Costo']
    return df

# --- INTERFACCIA ---
st.title("🏠 Monitoraggio Casa Cloud")

# LISTA STANZE CORRETTA
nomi_stanze = [
    "Camera da Letto",
    "Tavolo e Sedie",
    "Salotto",
    "Cucina",
    "Attività Muratore, Idraulico et"
]

st.sidebar.header("📍 Navigazione")
opzioni_menu = ["📊 Riepilogo Casa"] + nomi_stanze
selezione = st.sidebar.selectbox("Vai a:", opzioni_menu)

st.sidebar.write("---")
with st.sidebar.expander("🛠️ Impostazioni Avanzate"):
    abilita_chiusura = st.checkbox("Abilita tasto spegnimento")
    if abilita_chiusura:
        if st.button("🛑 CHIUDI APPLICAZIONE", use_container_width=True, type="primary"):
            os.kill(os.getpid(), signal.SIGINT)

# --- LOGICA PAGINE ---

if selezione == "📊 Riepilogo Casa":
    st.subheader("Riepilogo Spese Totale")
    riassunto = []

    with st.spinner("Sincronizzazione Cloud..."):
        for stanza in nomi_stanze:
            try:
                df = conn.read(worksheet=stanza, ttl=0)
                if df is not None and not df.empty:
                    df = pulisci_df(df)
                    tot = df['Importo Totale'].sum()
                    mask = df['Acquista S/N'].str.upper().str.strip() == 'S'
                    speso = df[mask]['Importo Totale'].sum()
                    riassunto.append({"Stanza": stanza, "Budget": tot, "Speso": speso, "Mancante": tot-speso})
            except:
                continue

    if riassunto:
        df_riepilogo = pd.DataFrame(riassunto)
        c1, c2, c3 = st.columns(3)
        c1.metric("BUDGET TOTALE", f"€ {df_riepilogo['Budget'].sum():,.2f}")
        c2.metric("TOTALE SPESO", f"€ {df_riepilogo['Speso'].sum():,.2f}",
                  delta=f"€ {df_riepilogo['Mancante'].sum():,.2f} residui", delta_color="inverse")

        st.plotly_chart(px.bar(df_riepilogo, x="Stanza", y=["Speso", "Mancante"], barmode="stack",
                               color_discrete_map={"Speso": "#2ecc71", "Mancante": "#e74c3c"}), use_container_width=True)

else:
    stanza_selezionata = selezione
    st.subheader(f"Gestione: {stanza_selezionata}")

    try:
        df_origine = conn.read(worksheet=stanza_selezionata, ttl=0)
        df_origine = pulisci_df(df_origine)

        tot_st = df_origine['Importo Totale'].sum()
        mask_s = df_origine['Acquista S/N'].str.upper().str.strip() == 'S'
        speso_st = df_origine[mask_s]['Importo Totale'].sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("Budget", f"€ {tot_st:,.2f}")
        m2.metric("Speso", f"€ {speso_st:,.2f}")
        m3.metric("Residuo", f"€ {tot_st - speso_st:,.2f}")

        df_editabile = st.data_editor(
            df_origine,
            column_config={
                "Acquista S/N": st.column_config.SelectboxColumn("S/N", options=["S", "N"]),
                "Costo": st.column_config.NumberColumn("Costo (€)", format="€ %.2f"),
                "Importo Totale": st.column_config.NumberColumn("Totale (€)", format="€ %.2f", disabled=True),
            },
            disabled=["Articolo", "Importo Totale"],
            hide_index=True, use_container_width=True, key=f"ed_{stanza_selezionata}"
        )

        if st.button("💾 SALVA MODIFICHE", use_container_width=True, type="primary"):
            df_editabile['Importo Totale'] = df_editabile['Acquistato'] * df_editabile['Costo']
            conn.update(worksheet=stanza_selezionata, data=df_editabile)
            st.success("Sincronizzato!")
            time.sleep(1)
            st.rerun()

    except Exception:
        st.error(f"Tab '{stanza_selezionata}' non trovata. Controlla il nome su Google Sheets.")
