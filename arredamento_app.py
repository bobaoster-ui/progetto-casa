import streamlit as st
from supabase import create_client
import pandas as pd
import time

# --- CONNESSIONE ---
sb = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

st.set_page_config(page_title="Ripristino Proprietà Jacopo", layout="wide")

# --- FUNZIONE PULIZIA DATI ---
def prepare_for_db(df, stanza_name):
    # Rinomina per il database (minuscolo e senza spazi)
    mapping = {
        'Articolo': 'articolo', 'Acquistato': 'acquistato', 'Costo': 'costo',
        'Importo Totale': 'importo_totale', 'Acquista S/N': 'acquista_sn',
        'Note': 'note', 'Versato': 'versato', 'Prezzo Pieno': 'prezzo_pieno',
        'Sconto %': 'sconto_perc', 'Stato Pagamento': 'stato_pagamento'
    }
    df_db = df.rename(columns=mapping).copy()
    df_db['stanza'] = stanza_name

    # Forza i numeri a essere numeri
    for col in ['acquistato', 'costo', 'importo_totale', 'versato', 'prezzo_pieno', 'sconto_perc']:
        if col in df_db.columns:
            df_db[col] = pd.to_numeric(df_db[col], errors='coerce').fillna(0.0)

    # Mantieni solo le colonne che esistono davvero nel DB
    allowed_cols = ['articolo', 'acquistato', 'costo', 'importo_totale', 'acquista_sn', 'note', 'versato', 'prezzo_pieno', 'sconto_perc', 'stato_pagamento', 'stanza']
    return df_db[[c for c in allowed_cols if c in df_db.columns]]

st.title("🚀 Caricatore Dati Proprietà Jacopo")

# Seleziona stanza
stanza = st.selectbox("In quale stanza vuoi caricare i dati?", ["Lavori", "Camera", "Cucina", "Salotto", "Tavolo", "Wishlist"])

# Crea un template vuoto su cui incollare
template = pd.DataFrame([{
    "Articolo": "", "Acquistato": 1, "Prezzo Pieno": 0, "Sconto %": 0,
    "Acquista S/N": "S", "Stato Pagamento": "Preventivo", "Versato": 0, "Note": ""
}])

st.write("### 1. Incolla i dati qui sotto")
df_input = st.data_editor(template, num_rows="dynamic", use_container_width=True)

if st.button("💾 CARICA NEL DATABASE"):
    with st.spinner("Salvataggio in corso..."):
        try:
            data_to_save = prepare_for_db(df_input, stanza)
            # Salvataggio
            sb.table("arredamento").insert(data_to_save.to_dict(orient='records')).execute()
            st.success(f"✅ {len(data_to_save)} record caricati con successo in {stanza}!")
            time.sleep(2)
            st.rerun()
        except Exception as e:
            st.error(f"Errore durante il caricamento: {e}")
            st.info("Controlla che non ci siano simboli come € o punti nelle celle numeriche.")
