import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# Configurazione Pagina
st.set_page_config(page_title="Monitoraggio Casa Cloud", page_icon="🏠", layout="wide")

# Connessione
conn = st.connection("gsheets", type=GSheetsConnection)

def pulisci_df(df):
    """Pulisce i dati (gestisce i formati dei tuoi file come €6.878,22)"""
    df.columns = [str(c).strip() for c in df.columns]
    if 'Acquista S/N' not in df.columns: df['Acquista S/N'] = "N"

    # Conversione per i costi (gestisce virgole e simboli euro)
    for col in ['Costo', 'Importo Totale', 'Acquistato']:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace('€', '').str.replace('.', '').str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['Importo Totale'] = df['Acquistato'] * df['Costo']
    return df

st.title("🏠 Monitoraggio Casa Cloud")

# Nomi stanze semplificati come da tua modifica su Google Sheets
nomi_stanze = ["Camera", "Cucina", "Salotto", "Tavolo", "Lavori"]

st.sidebar.header("📍 Navigazione")
selezione = st.sidebar.selectbox("Vai a:", ["📊 Riepilogo"] + nomi_stanze)

if selezione == "📊 Riepilogo":
    st.subheader("Situazione Generale Spese")
    st.info("Seleziona una stanza dal menu a sinistra per vedere i dettagli.")

    # Test di connessione nella sidebar
    try:
        test_df = conn.read(ttl=0)
        st.sidebar.success("✅ Cloud Collegato!")
    except Exception as e:
        st.sidebar.error("❌ Errore Connessione")
        st.error(f"Controlla i Secrets! Errore: {e}")

else:
    stanza_selezionata = selezione
    st.subheader(f"Gestione: {stanza_selezionata}")

    try:
        # Caricamento dati della tab semplificata
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
            st.success("Dati sincronizzati su Google Sheets!")
            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"La Tab '{stanza_selezionata}' non risponde.")
        st.write("Verifica che il nome sul foglio Google sia esattamente lo stesso (maiuscole incluse).")
