import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("🏠 Test Monitoraggio")

# Connessione
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Leggiamo la tabella 'camera' (assicurati che si chiami così!)
    df = conn.read(worksheet="camera", ttl=0)
    st.success("Connessione riuscita!")
    st.dataframe(df)
except Exception as e:
    st.error("C'è ancora un problema di configurazione.")
    st.write("Errore rilevato:", e)
