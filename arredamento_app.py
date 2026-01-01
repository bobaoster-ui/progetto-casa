import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# Configurazione Pagina
st.set_page_config(page_title="Monitoraggio Casa Cloud", page_icon="🏠", layout="wide")

# Connessione
conn = st.connection("gsheets", type=GSheetsConnection)

def pulisci_df(df):
    """Pulisce i dati e gestisce i formati numerici [cite: 1, 2, 3]"""
    df.columns = [str(c).strip() for c in df.columns]

    if 'Acquista S/N' not in df.columns:
        df['Acquista S/N'] = "N"

    cols_da_pulire = ['Costo', 'Importo Totale', 'Acquistato']
    for col in cols_da_pulire:
        if col in df.columns:
            if df[col].dtype == object:
                # Gestisce formati come 6.878,22  o €0,00 [cite: 1]
                df[col] = df[col].astype(str).str.replace('€', '').str.replace('.', '').str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['Importo Totale'] = df['Acquistato'] * df['Costo']
    return df

st.title("🏠 Monitoraggio Casa Cloud")

# Nomi stanze IDENTICI alle tab di Google Sheets (tutti minuscoli)
nomi_stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

st.sidebar.header("📍 Navigazione")
# Menu a tendina con nomi esatti per evitare confusione
selezione = st.sidebar.selectbox("Vai a:", ["📊 Riepilogo"] + nomi_stanze)

if selezione == "📊 Riepilogo":
    st.subheader("Situazione Generale Spese")
    st.info("Seleziona una stanza dal menu a sinistra per gestire i dettagli.")

    try:
        # Tenta di leggere la prima tab per confermare la connessione
        conn.read(worksheet="camera", ttl=0)
        st.sidebar.success("✅ Cloud Collegato!")
    except:
        st.sidebar.warning("⏳ Collegamento in corso...")

else:
    stanza_selezionata = selezione
    st.subheader(f"Gestione: {stanza_selezionata}")

    try:
        # Caricamento dati dalla tab specifica
        df_origine = conn.read(worksheet=stanza_selezionata, ttl=0)
        df_origine = pulisci_df(df_origine)

        df_editabile = st.data_editor(
            df_origine,
            column_config={
                "Acquista S/N": st.column_config.SelectboxColumn("Acquista", options=["S", "N"]),
                "Costo": st.column_config.NumberColumn("Costo €", format="%.2f"),
                "Importo Totale": st.column_config.NumberColumn("Totale €", format="%.2f", disabled=True)
            },
            hide_index=True,
            use_container_width=True,
            key=f"editor_{stanza_selezionata}"
        )

        if st.button("💾 SALVA MODIFICHE", use_container_width=True):
            conn.update(worksheet=stanza_selezionata, data=df_editabile)
            st.success("Sincronizzazione completata!")
            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"Impossibile leggere la tabella '{stanza_selezionata}'.")
        st.info("Controlla che il nome della Tab su Google Sheets sia tutto minuscolo e senza spazi.")
