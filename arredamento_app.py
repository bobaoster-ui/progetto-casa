import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("🧪 Test Finale")

# Connessione
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Legge il foglio SENZA specificare worksheet
    # Questo carica la prima tab in assoluto del file
    df = conn.read(ttl=0) 
    
    st.success("✅ SE VEDI QUESTO, IL COLLEGAMENTO È RISOLTO!")
    st.dataframe(df)
    
except Exception as e:
    st.error("Errore persistente")
    st.code(str(e))
