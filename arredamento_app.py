import streamlit as st
from supabase import create_client
import pandas as pd

st.set_page_config(page_title="RAGGI X DATABASE", layout="wide")

# Connessione rapida
sb = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

st.title("🔍 Ispezione Profonda Database")

try:
    # Leggiamo TUTTO senza filtri
    res = sb.table("arredamento").select("*").execute()
    df = pd.DataFrame(res.data)

    if df.empty:
        st.error("🚨 ATTENZIONE: Il database restituisce ZERO record. La tabella è vuota.")
    else:
        st.success(f"Trovati {len(df)} record totali.")

        # Filtro rapido per vedere cosa è rimasto
        st.write("### Conteggio per Stanza:")
        if 'stanza' in df.columns:
            st.write(df['stanza'].value_counts())

        st.write("### Dati Grezzi (Controlla se vedi 'Lavori' o 'Wishlist'):")
        st.dataframe(df)

except Exception as e:
    st.error(f"Errore durante la lettura: {e}")

st.info("Se in questa tabella NON vedi i Lavori, significa che sono stati rimossi dal DB.")
