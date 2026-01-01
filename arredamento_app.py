import streamlit as st
import pandas as pd

st.set_page_config(page_title="Monitoraggio Casa", layout="wide")
st.title("🏠 Monitoraggio Casa")

# URL del tuo foglio (formato export per saltare gli errori 400)
URL_BASE = "https://docs.google.com/spreadsheets/d/1O__ZbkbxowCxyfk_Wg0VYv2QoCNHHSfezw6bRLjMqRU/gviz/tq?tqx=out:csv"

# Menu Stanze
stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]
scelta = st.sidebar.selectbox("Scegli stanza:", stanze)

# Funzione per caricare i dati forzando il cambio tab
def carica_dati(nome_tab):
    # Costruiamo l'URL che punta esattamente alla tab scelta
    url = f"{URL_BASE}&sheet={nome_tab}"
    # Leggiamo il CSV (aggiungiamo un parametro casuale per saltare la cache)
    return pd.read_csv(url)

try:
    # Carichiamo i dati della stanza scelta
    df = carica_dati(scelta)
    
    if df is not None:
        st.success(f"✅ Dati di '{scelta}' caricati!")
        
        # Pulizia colonne
        df.columns = [str(c).strip() for c in df.columns]
        
        # Visualizzazione (Sola Lettura per ora, per essere sicuri che vedi tutto)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.info("💡 Se ora vedi correttamente tutte le stanze, aggiungiamo il tasto salva nel prossimo passo.")

except Exception as e:
    st.error(f"Errore nel caricamento di {scelta}")
    st.code(str(e))
