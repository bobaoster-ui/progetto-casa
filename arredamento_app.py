import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Monitoraggio Casa", layout="wide")
st.title("🏠 Monitoraggio Casa")

# Inizializza connessione
conn = st.connection("gsheets", type=GSheetsConnection)

# Sidebar
stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]
scelta = st.sidebar.selectbox("Scegli stanza:", stanze)

try:
    # Tentativo di lettura con refresh forzato
    df = conn.read(worksheet=scelta, ttl=0)
    
    if df is not None:
        st.success(f"Dati caricati per {scelta}!")
        # Editor semplice
        df_edit = st.data_editor(df, use_container_width=True, hide_index=True)
        
        if st.button("💾 SALVA"):
            conn.update(worksheet=scelta, data=df_edit)
            st.balloons()
            st.success("Sincronizzato!")
            
except Exception as e:
    st.error("⚠️ Errore di connessione")
    st.write("Dettaglio errore:", e)
    # Verifica se l'URL è quello giusto
    if "spreadsheet" in st.secrets["connections"]["gsheets"]:
        st.info(f"L'app sta cercando di connettersi a: {st.secrets['connections']['gsheets']['spreadsheet']}")
