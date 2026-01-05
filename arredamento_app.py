import streamlit as st
from streamlit_gsheets import GSheetsConnection
from supabase import create_client
import pandas as pd

# Configurazione connessione
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase = create_client(url, key)

# Connessione a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

st.title("🚀 Trasloco Definitivo (Senza Duplicati)")

if st.button("AVVIA TRASLOCO PULITO"):
    try:
        # 1. PULIZIA: Rimuoviamo eventuali record vecchi per evitare duplicati
        st.write("Pulizia database in corso...")
        supabase.table("arredamento").delete().neq("id", 0).execute()

        for s in stanze:
            st.write(f"Trasferimento stanza: {s}...")
            df = conn.read(worksheet=s)

            # Funzione di pulizia numeri per evitare l'errore 'nan'
            def clean_num(val, default=0.0):
                try:
                    res = pd.to_numeric(val, errors='coerce')
                    return float(res) if pd.notnull(res) else default
                except:
                    return default

            for _, row in df.iterrows():
                data = {
                    "stanza": s.capitalize(),
                    "articolo": str(row.get('Articolo', row.get('Oggetto', 'N/A'))),
                    "importo_totale": clean_num(row.get('Importo Totale')),
                    "versato": clean_num(row.get('Versato')),
                    "prezzo_pieno": clean_num(row.get('Prezzo Pieno')),
                    "sconto_percentuale": clean_num(row.get('Sconto %')),
                    "acquistato": clean_num(row.get('Acquistato', 1), default=1.0),
                    "costo": clean_num(row.get('Costo')),
                    "nota": str(row.get('Note', '')).replace('nan', ''),
                    "stato_pagamento": str(row.get('Stato Pagamento', row.get('Stato', ''))).replace('nan', ''),
                    "stanza_chiusa": str(row.get('Stanza Chiusa', 'FALSE')).upper() in ['TRUE', '1', '1.0']
                }
                supabase.table("arredamento").insert(data).execute()

            st.success(f"✅ Stanza {s} completata!")

        st.balloons()
        st.info("Trasloco terminato con successo! Controlla pure il Table Editor su Supabase.")
    except Exception as e:
        st.error(f"Errore durante il trasloco: {e}")
