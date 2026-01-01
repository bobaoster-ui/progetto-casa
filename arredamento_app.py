import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Monitoraggio Casa", layout="wide")
st.title("🏠 Monitoraggio Casa Cloud")

# Connessione
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. TEST DI CONNESSIONE: Proviamo a leggere il foglio senza specificare il nome
try:
    # Se non mettiamo worksheet, legge il primo foglio disponibile
    df_test = conn.read(ttl=0)
    st.sidebar.success("✅ Connessione stabilita!")
except Exception as e:
    st.sidebar.error("❌ Errore di connessione")
    st.error(f"L'app non riesce a raggiungere Google Sheets. Errore: {e}")
    st.stop()

# 2. FUNZIONE DI PULIZIA DATI (Basata sui tuoi file reali)
def pulisci_dati(df):
    df.columns = [str(c).strip() for c in df.columns]
    # Gestione numeri (es. 6878,22 della cucina o 360 del letto)
    for col in ['Costo', 'Importo Totale', 'Acquistato']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('€', '').str.replace('.', '').str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

# 3. MENU NAVIGAZIONE
nomi_stanze = ["Camera da Letto", "Tavolo e Sedie", "Salotto", "Cucina", "Attività Muratore, Idraulico et"]
selezione = st.sidebar.selectbox("Seleziona Stanza:", nomi_stanze)

# 4. CARICAMENTO DATI
try:
    # Cerchiamo di caricare la tab selezionata
    df = conn.read(worksheet=selezione, ttl=0)
    df = pulisci_dati(df)

    st.subheader(f"Dettaglio: {selezione}")

    # Mostriamo i dati che abbiamo nei tuoi file
    # Ad esempio il Letto contenitore a 360€ o il Tavolo a 174€
    st.data_editor(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Non trovo la tab '{selezione}' su Google Sheets.")
    st.info("⚠️ CONTROLLO FINALE: Vai su Google Sheets, rinomina la tab scrivendo 'Test' e prova a cambiare il nome nel codice in 'Test'. Se funziona, i nomi originali hanno caratteri invisibili.")
