import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Monitoraggio Casa", layout="wide")
st.title("🏠 Monitoraggio Casa")

# 1. Configurazione Connessione per il salvataggio
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. URL per la lettura veloce (quello che sta funzionando!)
URL_BASE = "https://docs.google.com/spreadsheets/d/1O__ZbkbxowCxyfk_Wg0VYv2QoCNHHSfezw6bRLjMqRU/gviz/tq?tqx=out:csv"

# Sidebar
stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]
scelta = st.sidebar.selectbox("Seleziona la stanza:", stanze)

# Funzione di lettura che ha funzionato
def carica_dati(nome_tab):
    url = f"{URL_BASE}&sheet={nome_tab}"
    # Il trucco per forzare l'aggiornamento dei dati
    return pd.read_csv(url)

try:
    # Caricamento dati
    df = carica_dati(scelta)
    
    if df is not None:
        st.success(f"Dati di '{scelta}' pronti per la modifica")
        
        # Pulizia colonne
        df.columns = [str(c).strip() for c in df.columns]
        
        # EDITOR: Qui puoi cambiare i prezzi
        # Usiamo una 'key' dinamica così Streamlit non si confonde tra le stanze
        df_edit = st.data_editor(df, use_container_width=True, hide_index=True, key=f"ed_{scelta}")
        
        st.divider()
        
        # TASTO SALVA
        if st.button(f"💾 SALVA MODIFICHE IN {scelta.upper()}"):
            with st.spinner("Salvataggio in corso..."):
                try:
                    # Usiamo la connessione ufficiale solo per scrivere
                    conn.update(worksheet=scelta, data=df_edit)
                    st.success("✅ Salvataggio riuscito! I dati su Google Sheets sono aggiornati.")
                    st.balloons()
                except Exception as e_save:
                    st.error("Errore durante il salvataggio. Verifica i Secrets.")
                    st.code(str(e_save))

except Exception as e:
    st.error(f"Errore nel caricamento di {scelta}")
    st.code(str(e))
