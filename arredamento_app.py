import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("🧪 Test Connessione Totale")

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Legge la tab 'camera' ignorando ogni tipo di cache
    df = conn.read(worksheet="camera", ttl=0)
    
    if df is not None:
        st.success("FINALMENTE! Dati letti:")
        st.write(df)
    else:
        st.warning("Il foglio è connesso ma non restituisce dati.")

except Exception as e:
    st.error("L'errore persiste. Ecco il dettaglio tecnico:")
    st.code(str(e))
