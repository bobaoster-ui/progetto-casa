import streamlit as st
from supabase import create_client
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Inizializzo connessioni
conn_sheets = st.connection("gsheets", type=GSheetsConnection)
supabase = create_client(st.secrets["supabase_url"], st.secrets["supabase_key"])

# Aggiunto 'desideri' alla lista delle stanze da migrare
stanze_da_migrare = ["camera", "cucina", "salotto", "tavolo", "lavori", "desideri"]

def migra_dati():
    for s in stanze_da_migrare:
        st.write(f"Migrazione in corso: {s}...")
        try:
            df = conn_sheets.read(worksheet=s)
            if df is None or df.empty:
                st.warning(f"Foglio {s} vuoto, salto...")
                continue

            for _, row in df.iterrows():
                # Definiamo la stanza: se è 'desideri' scriviamo 'Wishlist'
                nome_stanza = "Wishlist" if s == "desideri" else s.capitalize()

                dati_db = {
                    "articolo": str(row.get('Articolo', row.get('Oggetto', 'N/A'))),
                    "acquistato": float(row.get('Acquistato', 1)),
                    "costo": float(row.get('Costo', 0)),
                    "importo_totale": float(row.get('Importo Totale', 0)),
                    "acquista_sn": str(row.get('Acquista S/N', row.get('S/N', 'N'))),
                    "note": str(row.get('Note', '')),
                    "prezzo_pieno": float(row.get('Prezzo Pieno', 0)),
                    "sconto_perc": float(row.get('Sconto %', 0)),
                    "stato_pagamento": str(row.get('Stato Pagamento', row.get('Stato', ''))),
                    "versato": float(row.get('Versato', 0)),
                    "link_fattura": str(row.get('Link Fattura', '')),
                    "data_scadenza": str(row['Data Scadenza']) if pd.notnull(row.get('Data Scadenza')) else None,
                    "stanza_chiusa": False,
                    "link": str(row.get('Link', '')),
                    "foto": str(row.get('Foto', '')),
                    "stanza": nome_stanza
                }
                supabase.table("arredamento").insert(dati_db).execute()
            st.success(f"✅ {s} migrata!")
        except Exception as e:
            st.error(f"Errore durante la migrazione di {s}: {e}")

if st.button("🚀 AVVIA MIGRAZIONE TOTALE"):
    migra_dati()
