import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configurazione base
st.set_page_config(page_title="Monitoraggio Casa", layout="wide")
st.title("🏠 Monitoraggio Casa - Test Diretto")

# Inizializzazione connessione
conn = st.connection("gsheets", type=GSheetsConnection)

# Menu semplice con i nomi esatti che hai su Google Sheets
nomi_stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]
selezione = st.sidebar.selectbox("Seleziona una stanza:", nomi_stanze)

st.write(f"Tentativo di lettura della tab: **{selezione}**")

try:
    # IL CUORE DELLA SOLUZIONE: 
    # Usiamo ttl=0 per ignorare la memoria vecchia (cache)
    # Usiamo un metodo di lettura più grezzo per evitare errori di formato
    df = conn.read(worksheet=selezione, ttl=0)
    
    if df is not None and not df.empty:
        st.success(f"Dati trovati per {selezione}!")
        
        # Pulizia veloce dei nomi colonne
        df.columns = [str(c).strip() for c in df.columns]
        
        # Mostriamo la tabella così com'è, senza filtri sui prezzi per ora
        st.dataframe(df, use_container_width=True)
        
        # Se vuoi provare a modificare e salvare:
        st.divider()
        st.subheader("Modifica i dati")
        df_edit = st.data_editor(df, key=f"editor_{selezione}", hide_index=True)
        
        if st.button("💾 SALVA SU GOOGLE SHEETS"):
            conn.update(worksheet=selezione, data=df_edit)
            st.success("Salvataggio inviato! Ricarica la pagina tra un istante.")
    else:
        st.warning(f"La tab '{selezione}' sembra essere vuota o non formattata correttamente.")

except Exception as e:
    st.error(f"Errore durante la lettura di '{selezione}'")
    st.code(str(e)) # Questo ci dirà l'errore tecnico esatto se fallisce
    st.info("💡 Se vedi questo errore, prova a ricreare la tab su Google Sheets scrivendo i nomi a mano invece di incollarli.")
