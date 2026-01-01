import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configurazione Pagina
st.set_page_config(page_title="Monitoraggio Arredamento Casa", layout="wide", page_icon="🏠")

st.title("🏠 Monitoraggio Spese Arredamento")

# Connessione sicura
conn = st.connection("gsheets", type=GSheetsConnection)

# Elenco stanze
stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

# --- SEZIONE RIEPILOGO GENERALE ---
st.markdown("### 📊 Riepilogo Generale")
col_rip1, col_rip2 = st.columns(2)

totale_casa = 0
dati_riepilogo = []

try:
    # Carichiamo velocemente i totali di ogni stanza
    for s in stanze:
        temp_df = conn.read(worksheet=s, ttl=600) # cache di 10 minuti per il riepilogo
        if 'Prezzo' in temp_df.columns:
            temp_df['Prezzo'] = pd.to_numeric(temp_df['Prezzo'], errors='coerce').fillna(0)
            somma_stanza = temp_df['Prezzo'].sum()
            totale_casa += somma_stanza
            dati_riepilogo.append({"Stanza": s.capitalize(), "Spesa": somma_stanza})

    with col_rip1:
        st.metric(label="TOTALE INVESTIMENTO CASA", value=f"{totale_casa:,.2f} €")
    
    with col_rip2:
        # Una piccola tabella di riepilogo veloce
        df_sommario = pd.DataFrame(dati_riepilogo)
        st.dataframe(df_sommario, hide_index=True, use_container_width=True)

except Exception:
    st.info("Caricamento riepilogo in corso...")

st.divider()

# --- SEZIONE DETTAGLIO STANZA ---
selezione = st.sidebar.selectbox("Vai alla stanza specifica:", stanze)
st.subheader(f"Dettaglio: {selezione.capitalize()}")

try:
    # Lettura dati della stanza selezionata (senza cache per permettere modifiche immediate)
    df = conn.read(worksheet=selezione, ttl=0)
    
    if df is not None:
        df.columns = [str(c).strip() for c in df.columns]
        
        # Calcolo totale stanza singola
        if 'Prezzo' in df.columns:
            df['Prezzo'] = pd.to_numeric(df['Prezzo'], errors='coerce').fillna(0)
            st.write(f"Totale parziale {selezione}: **{df['Prezzo'].sum():,.2f} €**")
        
        # Editor dati
        df_edit = st.data_editor(
            df, 
            use_container_width=True, 
            hide_index=True, 
            key=f"editor_{selezione}",
            num_rows="dynamic"
        )

        # Tasto Salva
        if st.button(f"💾 SALVA MODIFICHE {selezione.upper()}"):
            with st.spinner("Sincronizzazione con Google Sheets..."):
                conn.update(worksheet=selezione, data=df_edit)
                st.success("Dati salvati! Aggiornamento in corso...")
                st.balloons()
                st.rerun()

except Exception as e:
    st.error("Errore nel caricamento dei dettagli.")
    st.code(str(e))

st.sidebar.markdown("---")
st.sidebar.write("✅ Connessione Protetta Attiva")
