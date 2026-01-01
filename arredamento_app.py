import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Monitoraggio Casa", layout="wide")
st.title("🏠 Monitoraggio Casa")

# 1. Configurazione Connessione
# Aggiungiamo un parametro per forzare l'autenticazione se necessaria
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. URL per la lettura veloce (che funziona!)
URL_BASE = "https://docs.google.com/spreadsheets/d/1O__ZbkbxowCxyfk_Wg0VYv2QoCNHHSfezw6bRLjMqRU/gviz/tq?tqx=out:csv"

stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]
scelta = st.sidebar.selectbox("Seleziona la stanza:", stanze)

def carica_dati(nome_tab):
    url = f"{URL_BASE}&sheet={nome_tab}"
    return pd.read_csv(url)

try:
    df = carica_dati(scelta)
    
    if df is not None:
        st.success(f"Dati di '{scelta}' pronti")
        
        df.columns = [str(c).strip() for c in df.columns]
        
        # Editor
        df_edit = st.data_editor(df, use_container_width=True, hide_index=True, key=f"ed_{scelta}")
        
        st.divider()
        
        if st.button(f"💾 SALVA MODIFICHE IN {scelta.upper()}"):
            with st.spinner("Tentativo di salvataggio..."):
                try:
                    # TENTATIVO DI SALVATAGGIO
                    conn.update(worksheet=scelta, data=df_edit)
                    st.success("✅ Salvataggio riuscito!")
                    st.balloons()
                except Exception as e_save:
                    st.error("Errore di permessi Google")
                    st.write("Google richiede un'autenticazione privata per scrivere.")
                    st.info("💡 Roberto, se questo fallisce, dobbiamo attivare una 'API Key' su Google Cloud, o usare un trucco diverso.")
                    st.code(str(e_save))

except Exception as e:
    st.error(f"Errore: {e}")
