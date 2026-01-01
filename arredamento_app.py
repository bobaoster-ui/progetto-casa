import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configurazione Pagina
st.set_page_config(page_title="Monitoraggio Arredamento Casa", layout="wide")

# Funzione per applicare i colori alle celle
def colora_celle(val):
    if isinstance(val, str) and '✅' in val:
        return 'background-color: #d4edda; color: #155724'
    elif isinstance(val, str) and '⚠️' in val:
        return 'background-color: #fff3cd; color: #856404'
    return ''

st.title("🏠 Monitoraggio Spese Arredamento")
st.markdown("Modifica i prezzi o lo stato e clicca su **Salva** in fondo alla pagina.")

# Connessione (usa i Secrets che abbiamo appena configurato)
conn = st.connection("gsheets", type=GSheetsConnection)

# Menu laterale per le stanze
stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]
selezione = st.sidebar.selectbox("Vai alla stanza:", stanze)

try:
    # Lettura dati
    df = conn.read(worksheet=selezione, ttl=0)
    
    if df is not None:
        # Pulizia nomi colonne
        df.columns = [str(c).strip() for c in df.columns]
        
        # --- CALCOLI ---
        if 'Prezzo' in df.columns:
            # Assicuriamoci che i prezzi siano numeri
            df['Prezzo'] = pd.to_numeric(df['Prezzo'], errors='coerce').fillna(0)
            totale = df['Prezzo'].sum()
            
            # Layout a colonne per i totali
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label=f"Totale {selezione.capitalize()}", value=f"{totale:,.2f} €")
        
        st.divider()

        # --- EDITOR DATI ---
        # Usiamo una key dinamica per non confondere la cache
        df_edit = st.data_editor(
            df, 
            use_container_width=True, 
            hide_index=True, 
            key=f"editor_{selezione}",
            num_rows="dynamic" # Ti permette di aggiungere righe se serve
        )

        st.divider()

        # --- TASTO SALVA ---
        if st.button(f"💾 SALVA MODIFICHE {selezione.upper()}"):
            with st.spinner("Sincronizzazione con Google Sheets..."):
                conn.update(worksheet=selezione, data=df_edit)
                st.success("Dati salvati con successo!")
                st.balloons()
                st.rerun()

except Exception as e:
    st.error("C'è stato un problema nel caricamento dei dati.")
    st.code(str(e))

st.sidebar.info("L'app è ora connessa in modo sicuro tramite Service Account.")
