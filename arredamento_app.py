import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Monitoraggio Casa", layout="wide")
st.title("🏠 Monitoraggio Casa - Ultimo Test")

# Connessione
conn = st.connection("gsheets", type=GSheetsConnection)

# Nomi stanze esatti (minuscoli come li hai messi tu)
nomi_stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

# Sidebar semplice
selezione = st.sidebar.selectbox("Seleziona Stanza:", nomi_stanze)

st.write(f"Stai guardando la stanza: **{selezione}**")

try:
    # Lettura ultra-basica: proviamo a caricare TUTTO senza filtri
    df = conn.read(worksheet=selezione, ttl=0)
    
    if df is not None:
        # Pulizia forzata: togliamo righe e colonne completamente vuote
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        if not df.empty:
            st.success(f"Trovate {len(df)} righe in {selezione}!")
            # Mostriamo i dati "puri"
            st.dataframe(df, use_container_width=True)
            
            # Area di modifica
            st.subheader("Modifica Dati")
            df_edit = st.data_editor(df, key=f"edit_{selezione}")
            
            if st.button("💾 SALVA"):
                conn.update(worksheet=selezione, data=df_edit)
                st.success("Dati inviati!")
        else:
            st.warning("Il foglio sembra vuoto. Scrivi qualcosa nella prima cella su Google Sheets.")
            
except Exception as e:
    st.error(f"Errore tecnico su {selezione}")
    # Questo ci dice se il problema è il NOME o il CONTENUTO
    st.write("Dettaglio errore:", e)
