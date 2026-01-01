import streamlit as st
import pandas as pd

st.set_page_config(page_title="Casa App", layout="wide")
st.title("🏠 Monitoraggio Casa")

# Recupero URL dai Secrets
try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    # Pulizia URL per sicurezza
    url = url.replace("/edit", "/export?format=csv")
except:
    st.error("URL non trovato nei Secrets!")
    st.stop()

# Menu Stanze
stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]
scelta = st.sidebar.selectbox("Scegli stanza:", stanze)

# Funzione di lettura "Forzata"
@st.cache_data(ttl=0)
def carica_dati(sheet_url, nome_tab):
    # Costruisce l'URL diretto per la singola tab
    final_url = f"{sheet_url}&sheet={nome_tab}"
    return pd.read_csv(final_url)

try:
    df = carica_dati(url, scelta)
    
    if df is not None:
        st.success(f"✅ Tab '{scelta}' caricata con successo!")
        
        # Pulizia colonne
        df.columns = [str(c).strip() for c in df.columns]
        
        # Editor
        st.data_editor(df, use_container_width=True, hide_index=True)
        
        st.info("💡 Nota: In questa modalità 'Direct Read', il tasto Salva è disabilitato per testare la lettura. Se vedi i dati, ripristiniamo il salvataggio al prossimo passo!")

except Exception as e:
    st.error("⚠️ Errore di lettura")
    st.code(str(e))
    st.warning("Se vedi ancora 400, vai su Google Sheets -> Condividi -> Assicurati che sia 'Chiunque abbia il link' + 'Editor'")
