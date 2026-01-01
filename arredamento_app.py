import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# Configurazione Pagina
st.set_page_config(page_title="Monitoraggio Casa Cloud", page_icon="🏠", layout="wide")

# Connessione
conn = st.connection("gsheets", type=GSheetsConnection)

def pulisci_df(df):
    """Pulisce i dati per uniformarli al formato richiesto"""
    df.columns = [str(c).strip() for c in df.columns]
    if 'Acquista S/N' not in df.columns: df['Acquista S/N'] = "N"

    # Conversione numerica per i costi (gestisce il formato € e virgole)
    for col in ['Costo', 'Importo Totale', 'Acquistato']:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace('€', '').str.replace('.', '').str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['Importo Totale'] = df['Acquistato'] * df['Costo']
    return df

st.title("🏠 Monitoraggio Casa Cloud")

# Lista stanze identica alle Tab su Google Sheets
nomi_stanze = [
    "Camera da Letto",
    "Tavolo e Sedie",
    "Salotto",
    "Cucina",
    "Attività Muratore, Idraulico et"
]

st.sidebar.header("📍 Navigazione")
opzioni = ["📊 Riepilogo Spese"] + nomi_stanze
selezione = st.sidebar.selectbox("Vai a:", opzioni)

if selezione == "📊 Riepilogo Spese":
    st.subheader("Situazione Generale Spese")
    # Tentativo di caricamento silenzioso per il riepilogo
    trovati = False
    for stanza in nomi_stanze:
        try:
            df = conn.read(worksheet=stanza, ttl=0)
            if df is not None:
                trovati = True
                break
        except:
            continue

    if not trovati:
        st.warning("In attesa di dati... Verifica che l'URL nei Secrets sia corretto e il foglio sia 'Editor'.")
    else:
        st.info("Dati rilevati nel Cloud. Seleziona una stanza dal menu a sinistra.")

else:
    stanza_selezionata = selezione
    st.subheader(f"Gestione: {stanza_selezionata}")

    try:
        # Caricamento della tab selezionata
        df_origine = conn.read(worksheet=stanza_selezionata, ttl=0)
        df_origine = pulisci_df(df_origine)

        # Editor per modificare i dati
        df_editabile = st.data_editor(
            df_origine,
            column_config={
                "Acquista S/N": st.column_config.SelectboxColumn("Acquista", options=["S", "N"]),
                "Costo": st.column_config.NumberColumn("Costo €", format="%.2f"),
                "Importo Totale": st.column_config.NumberColumn("Totale €", format="%.2f", disabled=True)
            },
            hide_index=True, use_container_width=True, key=f"editor_{stanza_selezionata}"
        )

        if st.button("💾 SALVA MODIFICHE", use_container_width=True):
            conn.update(worksheet=stanza_selezionata, data=df_editabile)
            st.success("Dati salvati con successo!")
            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"Tab '{stanza_selezionata}' non trovata o errore di connessione.")
        st.info("Suggerimento: Verifica che il nome della Tab su Google Sheets non abbia spazi vuoti alla fine.")
