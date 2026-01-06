import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time
import requests

# --- SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V22.10.11", layout="wide", page_icon="🚀")

# --- CONNESSIONE SUPABASE ---
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

sb = get_supabase()

# --- STILE ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
bc, cc, tc = ("#0e1117", "#1d2129", "#ffffff") if st.session_state.dark_mode else ("#f8f9fc", "#ffffff", "#1f2937")
st.markdown(f"""<style>.stApp {{background-color: {bc}; color: {tc};}}</style>""", unsafe_allow_html=True)

def clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    mapping = {'articolo': 'Articolo', 'acquistato': 'Acquistato', 'costo': 'Costo', 'importo_totale': 'Importo Totale', 'acquista_sn': 'Acquista S/N', 'note': 'Note', 'versato': 'Versato', 'prezzo_pieno': 'Prezzo Pieno', 'sconto_perc': 'Sconto %', 'stato_pagamento': 'Stato Pagamento', 'link_fattura': 'Link Fattura', 'link': 'Link', 'foto': 'Foto', 'data_scadenza': 'Data Scadenza', 'stanza_chiusa': 'Stanza Chiusa'}
    df = df.rename(columns=mapping)
    for c in ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    return df

if "password_correct" not in st.session_state:
    st.title("🔒 Accesso")
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]: st.session_state.password_correct = True; st.rerun()
else:
    with st.sidebar:
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist", "📦 Camera", "📦 Cucina", "📦 Salotto", "📦 Tavolo", "📦 Lavori"])
        edit_struct = st.toggle("⚙️ Modifica Struttura", True) # Attivato di default per aiutarti

    if sel == "🏠 Riepilogo":
        st.title("Riepilogo 🏠")
        st.info("Ripristina i dati nelle stanze per vedere i grafici.")

    elif "📦" in sel or "✨" in sel:
        sn = "Wishlist" if "✨" in sel else sel.replace("📦 ", "").capitalize()
        st.title(f"Stanza: {sn}")

        # Caricamento dati
        res = sb.table("arredamento").select("*").eq("stanza", sn).execute()
        df = clean_df(pd.DataFrame(res.data))

        # --- TRUCCO EMERGENZA ---
        if df.empty:
            df = pd.DataFrame([{"Articolo": "--- INCOLLA QUI I DATI DA SHEETS ---", "Acquistato": 1, "Prezzo Pieno": 0, "Sconto %": 0, "Acquista S/N": "S", "Stato Pagamento": "Preventivo", "Versato": 0, "Note": "", "Link": "", "Foto": "", "Data Scadenza": None}])

        with st.form(f"f_{sn}"):
            df_e = st.data_editor(df, use_container_width=True, hide_index=True, num_rows="dynamic")
            if st.form_submit_button("💾 SALVA TUTTO NELLA STANZA"):
                # Pulizia prima del salvataggio
                sb.table("arredamento").delete().eq("stanza", sn).execute()

                # Calcolo automatico costi
                for i in range(len(df_e)):
                    p, s, q = float(df_e.iloc[i].get('Prezzo Pieno',0)), float(df_e.iloc[i].get('Sconto %',0)), float(df_e.iloc[i].get('Acquistato',1))
                    c = p * (1-(s/100)) if p>0 else 0.0
                    df_e.at[df_e.index[i],'Costo'] = c
                    df_e.at[df_e.index[i],'Importo Totale'] = c*q

                inv_map = {v: k for k, v in {'articolo': 'Articolo', 'acquistato': 'Acquistato', 'costo': 'Costo', 'importo_totale': 'Importo Totale', 'acquista_sn': 'Acquista S/N', 'note': 'Note', 'versato': 'Versato', 'prezzo_pieno': 'Prezzo Pieno', 'sconto_perc': 'Sconto %', 'stato_pagamento': 'Stato Pagamento', 'data_scadenza': 'Data Scadenza'}.items()}
                df_db = df_e.rename(columns=inv_map)
                df_db['stanza'] = sn

                # Rimuovi colonne extra se presenti
                cols_to_keep = ['articolo', 'acquistato', 'costo', 'importo_totale', 'acquista_sn', 'note', 'versato', 'prezzo_pieno', 'sconto_perc', 'stato_pagamento', 'stanza']
                df_db = df_db[[c for c in cols_to_keep if c in df_db.columns]]

                sb.table("arredamento").insert(df_db.to_dict(orient='records')).execute()
                st.success("Dati ripristinati!"); time.sleep(1); st.rerun()
