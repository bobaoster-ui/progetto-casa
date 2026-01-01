import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Casa App", layout="wide")
st.title("🏠 Monitoraggio Casa")

# Connessione
conn = st.connection("gsheets", type=GSheetsConnection)

# Elenco stanze (assicurati siano scritte uguali sul foglio!)
stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]
scelta = st.sidebar.selectbox("Scegli stanza:", stanze)

try:
    # IL SEGRETO: Usiamo ttl=0 per forzare Google a mandarci i dati freschi
    df = conn.read(worksheet=scelta, ttl=0)
    
    if df is not None:
        st.success(f"Caricata tab: {scelta}")
        
        # Pulizia nomi colonne da spazi invisibili
        df.columns = [str(c).strip() for c in df.columns]
        
        # Visualizzazione e modifica
        df_edit = st.data_editor(df, use_container_width=True, hide_index=True)
        
        if st.button("💾 SALVA MODIFICHE"):
            conn.update(worksheet=scelta, data=df_edit)
            st.success("Dati salvati su Google Sheets!")
            st.rerun()

except Exception as e:
    st.error("⚠️ Connessione interrotta")
    st.info("Prova a fare 'Reboot' dal menu di Streamlit in alto a destra.")
    st.code(str(e)) # Questo ci dice l'errore esatto
