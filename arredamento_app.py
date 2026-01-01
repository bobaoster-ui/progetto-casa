import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# Configurazione Pagina
st.set_page_config(page_title="Monitoraggio Casa", page_icon="🏠", layout="wide")

# Connessione
conn = st.connection("gsheets", type=GSheetsConnection)

def pulisci_df(df):
    """Pulisce i dati e gestisce i formati (es. 6878,22 della cucina)"""
    df.columns = [str(c).strip() for c in df.columns]
    if 'Acquista S/N' not in df.columns: df['Acquista S/N'] = "N"

    # Conversione numerica per Costi e Importi
    for col in ['Costo', 'Importo Totale', 'Acquistato']:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace('€', '').str.replace('.', '').str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['Importo Totale'] = df['Acquistato'] * df['Costo']
    return df

st.title("🏠 Monitoraggio Casa")

# Nomi delle stanze (devono essere IDENTICI alle tab su Google Sheets)
nomi_stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

st.sidebar.header("📍 Navigazione")
selezione = st.sidebar.selectbox("Vai a:", ["Riepilogo"] + nomi_stanze)

if selezione == "Riepilogo":
    st.subheader("Situazione Generale Spese")
    st.info("Benvenuto! Seleziona una stanza dal menu a sinistra per gestire i dettagli.")

    try:
        # Test di connessione semplice
        conn.read(ttl=0)
        st.sidebar.success("✅ Cloud Collegato")
    except:
        st.sidebar.warning("⏳ In attesa di connessione...")

else:
    stanza_selezionata = selezione
    st.subheader(f"Gestione: {stanza_selezionata}")

    try:
        # Caricamento della tab specifica
        df_origine = conn.read(worksheet=stanza_selezionata, ttl=0)
        df_origine = pulisci_df(df_origine)

        # Editor interattivo
        df_editabile = st.data_editor(
            df_origine,
            column_config={
                "Acquista S/N": st.column_config.SelectboxColumn("Acquista", options=["S", "N"]),
                "Costo": st.column_config.NumberColumn("Costo €", format="%.2f"),
                "Importo Totale": st.column_config.NumberColumn("Totale €", format="%.2f", disabled=True)
            },
            hide_index=True, use_container_width=True, key=f"editor_{stanza_selezionata}"
        )

        if st.button("💾 SALVA MODIFICHE"):
            conn.update(worksheet=stanza_selezionata, data=df_editabile)
            st.success("Dati salvati su Google Sheets!")
            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"Impossibile trovare la tab '{stanza_selezionata}'")
        st.info("Assicurati che su Google Sheets la tab si chiami esattamente così (tutto minuscolo).")
