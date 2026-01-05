import streamlit as st
from streamlit_gsheets import GSheetsConnection
from supabase import create_client
import pandas as pd

# Connessione a Supabase (usa le chiavi che hai appena messo nei Secrets)
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase = create_client(url, key)

# Connessione a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

st.title("🚀 Migrazione Dati: Sheets ➡️ Supabase")

if st.button("AVVIA TRASLOCO"):
    for s in stanze:
        st.write(f"Trasferimento stanza: {s}...")
        try:
            # Leggi da Sheets
            df = conn.read(worksheet=s)

            for _, row in df.iterrows():
                # Prepariamo il dato per il database
                data = {
                    "stanza": s.capitalize(),
                    "articolo": str(row.get('Articolo', row.get('Oggetto', 'N/A'))),
                    "importo_totale": float(pd.to_numeric(row.get('Importo Totale', 0), errors='coerce') or 0),
                    "versato": float(pd.to_numeric(row.get('Versato', 0), errors='coerce') or 0),
                    "prezzo_pieno": float(pd.to_numeric(row.get('Prezzo Pieno', 0), errors='coerce') or 0),
                    "sconto_percentuale": float(pd.to_numeric(row.get('Sconto %', 0), errors='coerce') or 0),
                    "acquistato": float(pd.to_numeric(row.get('Acquistato', 1), errors='coerce') or 1),
                    "costo": float(pd.to_numeric(row.get('Costo', 0), errors='coerce') or 0),
                    "nota": str(row.get('Note', '')),
                    "stato_pagamento": str(row.get('Stato Pagamento', row.get('Stato', ''))),
                    "stanza_chiusa": str(row.get('Stanza Chiusa', 'FALSE')).upper() == 'TRUE'
                }
                # Inserimento nel Database
                supabase.table("arredamento").insert(data).execute()

            st.success(f"✅ Stanza {s} completata!")
        except Exception as e:
            st.error(f"Errore su {s}: {e}")

    st.balloons()
    st.info("Trasloco terminato! Ora puoi controllare il 'Table Editor' su Supabase.")
