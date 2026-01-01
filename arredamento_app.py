import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# Configurazione Pagina
st.set_page_config(page_title="Monitoraggio Casa Cloud", page_icon="🏠", layout="wide")

# Connessione
conn = st.connection("gsheets", type=GSheetsConnection)

def pulisci_df(df):
    """Pulisce i dati e gestisce i formati numerici dei tuoi file"""
    # Rimuove spazi bianchi dai nomi delle colonne
    df.columns = [str(c).strip() for c in df.columns]

    # Assicura la presenza della colonna decisionale
    if 'Acquista S/N' not in df.columns:
        df['Acquista S/N'] = "N"

    # Converte i costi (gestisce formati come 6.878,22 o €360)
    cols_da_pulire = ['Costo', 'Importo Totale', 'Acquistato']
    for col in cols_da_pulire:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace('€', '').str.replace('.', '').str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Ricalcola il totale per sicurezza
    df['Importo Totale'] = df['Acquistato'] * df['Costo']
    return df

st.title("🏠 Monitoraggio Casa Cloud")

# Nomi stanze IDENTICI alle tab di Google Sheets (in minuscolo)
nomi_stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

st.sidebar.header("📍 Navigazione")
# Nel menu appariranno con la prima lettera maiuscola per estetica
opzioni_menu = ["📊 Riepilogo"] + [n.capitalize() for n in nomi_stanze]
selezione = st.sidebar.selectbox("Vai a:", opzioni_menu)

if selezione == "📊 Riepilogo":
    st.subheader("Situazione Generale Spese")
    st.info("Seleziona una stanza dal menu a sinistra per gestire i dettagli.")

    # Test di connessione visibile nella sidebar
    try:
        conn.read(worksheet="camera", ttl=0)
        st.sidebar.success("✅ Cloud Collegato!")
    except:
        st.sidebar.error("❌ Connessione in corso...")

else:
    # Converte la selezione del menu nel nome esatto della tab (minuscolo)
    stanza_selezionata = selezione.lower()
    st.subheader(f"Gestione: {selezione}")

    try:
        # Caricamento dati dalla tab specifica
        df_origine = conn.read(worksheet=stanza_selezionata, ttl=0)
        df_origine = pulisci_df(df_origine)

        # Interfaccia di modifica dati
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
        st.info("Assicurati che su Google Sheets la tab si chiami esattamente così, senza spazi.")
