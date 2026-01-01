import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Test Connessione", layout="wide")
st.title("🏠 Test Finale")

try:
    # Creiamo la connessione
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Tentativo di lettura senza specificare nulla
    # ttl=0 serve a dire a Streamlit: "Dimentica gli errori passati!"
    df = conn.read(ttl=0)
    
    if df is not None:
        st.success("✅ CONNESSIONE RIUSCITA!")
        st.write("Ecco i dati che vedo nel tuo foglio:")
        st.dataframe(df)
    else:
        st.warning("Il foglio sembra vuoto o non accessibile.")

except Exception as e:
    st.error("❌ Errore di connessione")
    st.info("Dettaglio tecnico per Roberto:")
    st.code(str(e))
    
    st.divider()
    st.write("Se l'errore è ancora 400, controlla che l'URL nei Secrets sia identico a quello del browser quando apri il foglio Google.")
