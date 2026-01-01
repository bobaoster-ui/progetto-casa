import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Monitoraggio Casa", layout="wide")
st.title("🏠 Monitoraggio Casa")

# Inizializziamo la connessione ufficiale (quella che permette di salvare)
conn = st.connection("gsheets", type=GSheetsConnection)

# Menu Stanze
stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]
scelta = st.sidebar.selectbox("Scegli stanza:", stanze)

# Mostra un messaggio di caricamento
st.write(f"Stai visualizzando: **{scelta}**")

try:
    # Usiamo ttl=0 per forzare Streamlit a cambiare dati quando cambi stanza
    df = conn.read(worksheet=scelta, ttl=0)
    
    if df is not None and not df.empty:
        # Pulizia veloce delle colonne
        df.columns = [str(c).strip() for c in df.columns]
        
        # Tabella editabile
        # Il key=scelta è FONDAMENTALE per dire a Streamlit di cambiare tabella
        df_edit = st.data_editor(df, use_container_width=True, hide_index=True, key=f"editor_{scelta}")
        
        if st.button("💾 SALVA MODIFICHE SU CLOUD"):
            conn.update(worksheet=scelta, data=df_edit)
            st.success(f"Dati di '{scelta}' aggiornati correttamente!")
            st.balloons()
    else:
        st.warning(f"La tab '{scelta}' sembra vuota su Google Sheets.")

except Exception as e:
    st.error(f"⚠️ Errore nel caricamento della tab '{scelta}'")
    st.code(str(e))
