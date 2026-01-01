import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import time

# Configurazione Pagina
st.set_page_config(page_title="Monitoraggio Casa", page_icon="🏠", layout="wide")

# Connessione
conn = st.connection("gsheets", type=GSheetsConnection)

def pulisci_df(df):
    """Pulisce i dati importati dai tuoi file Arredamenti_Casa"""
    df.columns = [str(c).strip() for c in df.columns]
    if 'Acquista S/N' not in df.columns: df['Acquista S/N'] = "N"

    # Gestione costi e importi (dai tuoi dati: €6.878,22 etc.)
    for col in ['Costo', 'Importo Totale', 'Acquistato']:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace('€', '').str.replace('.', '').str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['Importo Totale'] = df['Acquistato'] * df['Costo']
    return df

st.title("🏠 Monitoraggio Casa Cloud")

# Nomi esatti delle tue Tab (Verificati dai tuoi file)
nomi_stanze = [
    "Camera da Letto",
    "Tavolo e Sedie",
    "Salotto",
    "Cucina",
    "Attività Muratore, Idraulico et"
]

st.sidebar.header("📍 Navigazione")
selezione = st.sidebar.selectbox("Vai a:", ["📊 Riepilogo Totale"] + nomi_stanze)

if selezione == "📊 Riepilogo Totale":
    st.subheader("Situazione Generale Spese")
    riassunto = []

    for stanza in nomi_stanze:
        try:
            # Lettura forzata senza cache
            df = conn.read(worksheet=stanza, ttl=0)
            if df is not None:
                df = pulisci_df(df)
                tot = df['Importo Totale'].sum()
                mask = df['Acquista S/N'].astype(str).str.upper().strip() == 'S'
                speso = df[mask]['Importo Totale'].sum()
                riassunto.append({"Stanza": stanza, "Budget": tot, "Speso": speso})
        except:
            continue

    if riassunto:
        df_r = pd.DataFrame(riassunto)
        c1, c2 = st.columns(2)
        c1.metric("Budget Totale", f"€ {df_r['Budget'].sum():,.2f}")
        c2.metric("Totale Speso", f"€ {df_r['Speso'].sum():,.2f}")
        st.plotly_chart(px.bar(df_r, x="Stanza", y=["Speso", "Budget"], barmode="group"), use_container_width=True)
    else:
        st.warning("Nessun dato trovato. Verifica l'URL nei Secrets.")

else:
    stanza_selezionata = selezione
    try:
        # Tentativo di lettura della stanza specifica
        df_origine = conn.read(worksheet=stanza_selezionata, ttl=0)
        df_origine = pulisci_df(df_origine)

        st.subheader(f"Gestione: {stanza_selezionata}")

        # Editor interattivo
        df_editabile = st.data_editor(
            df_origine,
            column_config={
                "Acquista S/N": st.column_config.SelectboxColumn("Acquista", options=["S", "N"]),
                "Costo": st.column_config.NumberColumn("Costo €", format="%.2f"),
                "Importo Totale": st.column_config.NumberColumn("Totale €", format="%.2f", disabled=True)
            },
            hide_index=True, use_container_width=True, key=f"ed_{stanza_selezionata}"
        )

        if st.button("💾 SALVA MODIFICHE"):
            conn.update(worksheet=stanza_selezionata, data=df_editabile)
            st.success("Cloud Aggiornato!")
            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"Impossibile trovare la tab '{stanza_selezionata}'.")
        st.info("Assicurati che su Google Sheets il foglio si chiami esattamente così, senza spazi prima o dopo.")
