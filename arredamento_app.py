import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Casa Cloud", layout="wide")

st.title("🏠 Monitoraggio Casa")

# Creazione connessione
conn = st.connection("gsheets", type=GSheetsConnection)

# Elenco tab esatte
nomi_stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]
selezione = st.sidebar.selectbox("Seleziona Stanza:", nomi_stanze)

try:
    # Usiamo il metodo più diretto possibile
    df = conn.read(worksheet=selezione, ttl=0)
    
    if df is not None:
        st.success(f"Dati caricati per: {selezione}")
        # Pulizia veloce colonne
        df.columns = [str(c).strip() for c in df.columns]
        
        # Editor per modificare i prezzi
        df_edit = st.data_editor(df, use_container_width=True, hide_index=True)
        
        if st.button("💾 SALVA MODIFICHE"):
            conn.update(worksheet=selezione, data=df_edit)
            st.success("Sincronizzato con Google Sheets!")
    
except Exception as e:
    st.error("⚠️ Errore di connessione")
    st.code(str(e))
    st.info("Se leggi '400 Bad Request', controlla i Secrets: l'URL deve finire esattamente con /edit")
