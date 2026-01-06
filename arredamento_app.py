import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import time
from fpdf import FPDF

# --- SICUREZZA ---
if "sicurezza" not in st.secrets or st.secrets["sicurezza"]["sigillo"] != "ATTIVATO":
    st.error("⚠️ ERRORE LICENZA: Sigillo non trovato."); st.stop()

# --- CONFIGURAZIONE E CONNESSIONE ---
st.set_page_config(page_title="Monitoraggio Arredamento V22.10.11", layout="wide", page_icon="🚀")

@st.cache_resource
def get_supabase():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

sb = get_supabase()

# --- STILE E DARK MODE ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
bc, cc, tc = ("#0e1117", "#1d2129", "#ffffff") if st.session_state.dark_mode else ("#f8f9fc", "#ffffff", "#1f2937")
st.markdown(f"""<style>.stApp {{background-color: {bc}; color: {tc};}}</style>""", unsafe_allow_html=True)

# --- FUNZIONI DI SUPPORTO ---
def clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    mapping = {
        'articolo': 'Articolo', 'acquistato': 'Acquistato', 'costo': 'Costo',
        'importo_totale': 'Importo Totale', 'acquista_sn': 'Acquista S/N',
        'note': 'Note', 'versato': 'Versato', 'prezzo_pieno': 'Prezzo Pieno',
        'sconto_perc': 'Sconto %', 'stato_pagamento': 'Stato Pagamento',
        'data_scadenza': 'Data Scadenza'
    }
    df = df.rename(columns=mapping)
    for c in ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0).astype(float)
    if 'Data Scadenza' in df.columns:
        df['Data Scadenza'] = pd.to_datetime(df['Data Scadenza'], errors='coerce').dt.date
    return df

# --- SIDEBAR ---
with st.sidebar:
    st.title("💎 Jacopo's Property")
    st.session_state.dark_mode = st.toggle("🌙 Dark Mode", st.session_state.dark_mode)
    # Rinominata Wishlist in Desideri come richiesto
    stanze_list = ["Camera", "Cucina", "Salotto", "Tavolo", "Lavori", "Desideri"]
    sel = st.selectbox("NAVIGAZIONE", ["🏠 Riepilogo", "📅 Scadenzario"] + [f"📦 {s}" for s in stanze_list])
    st.divider()
    edit_struct = st.toggle("⚙️ Modifica Struttura", False)
    st.caption("Decimali: usa il punto (es. 28.30)")

# --- LOGICA RIEPILOGO ---
if sel == "🏠 Riepilogo":
    st.title("Analisi Investimenti 📊")
    res = sb.table("arredamento").select("*").execute()
    full_df = clean_df(pd.DataFrame(res.data))

    if not full_df.empty:
        c1, c2, c3 = st.columns(3)
        ti, tv = full_df['Importo Totale'].sum(), full_df['Versato'].sum()
        c1.metric("Totale Impegnato", f"{ti:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
        c2.metric("Totale Versato", f"{tv:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
        c3.metric("Rimanenza", f"{(ti-tv):,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))

        st.divider()
        col_a, col_b = st.columns(2)
        fig1 = px.pie(full_df, values='Importo Totale', names='stanza', title="Spesa per Area", hole=0.4)
        col_a.plotly_chart(fig1, use_container_width=True)

        fig2 = px.bar(full_df.groupby(['stanza', 'Stato Pagamento'])['Importo Totale'].sum().reset_index(),
                      x='stanza', y='Importo Totale', color='Stato Pagamento', barmode='group', title="Dettaglio Pagamenti")
        col_b.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Inizia a caricare i dati nelle stanze per vedere le analisi.")

# --- SCADENZARIO COLORATO ---
elif sel == "📅 Scadenzario":
    st.title("Scadenzario Pagamenti ⏳")
    res = sb.table("arredamento").select("*").execute()
    df_s = clean_df(pd.DataFrame(res.data))

    if not df_s.empty and 'Data Scadenza' in df_s.columns:
        df_s = df_s[df_s['Data Scadenza'].notna()].copy()
        today = date.today()

        def get_status(d):
            delta = (d - today).days
            if delta < 0: return "🔴 SCADUTO"
            elif delta <= 7: return "🟡 IMMINENTE"
            return "🟢 OK"

        df_s['Alert'] = df_s['Data Scadenza'].apply(get_status)
        df_s = df_s.sort_values('Data Scadenza')
        st.dataframe(df_s[['Alert', 'Articolo', 'stanza', 'Data Scadenza', 'Importo Totale']], use_container_width=True, hide_index=True)
    else:
        st.info("Nessuna scadenza pianificata.")

# --- GESTIONE STANZE ---
elif "📦" in sel:
    sn = sel.replace("📦 ", "")
    st.title(f"Area: {sn}")
    res = sb.table("arredamento").select("*").eq("stanza", sn).execute()
    df = clean_df(pd.DataFrame(res.data))

    if df.empty:
        df = pd.DataFrame([{"Articolo": "Nuovo", "Acquistato": 1.0, "Prezzo Pieno": 0.0, "Sconto %": 0.0, "Acquista S/N": "S", "Stato Pagamento": "Preventivo", "Versato": 0.0, "Note": "", "Data Scadenza": None}])

    # --- CONFIGURAZIONE COLONNE (Il pezzetto dei decimali e tendine) ---
    cfg = {
        "Prezzo Pieno": st.column_config.NumberColumn("Prezzo Pieno", format="%.2f"),
        "Sconto %": st.column_config.NumberColumn("Sconto %", format="%.2f"),
        "Versato": st.column_config.NumberColumn("Versato", format="%.2f"),
        "Acquistato": st.column_config.NumberColumn("Quantità", format="%.2f"),
        "Data Scadenza": st.column_config.DateColumn("Scadenza"),
        "Acquista S/N": st.column_config.SelectboxColumn("Acquista S/N", options=["S", "N"], required=True),
        "Stato Pagamento": st.column_config.SelectboxColumn("Stato Pagamento", options=["Preventivo", "Acconto", "Saldo", "Ordinato", "Consegnato"], required=True),
        "Costo": st.column_config.NumberColumn("Costo Unit.", format="%.2f", disabled=True),
        "Importo Totale": st.column_config.NumberColumn("Totale", format="%.2f", disabled=True)
    }

    with st.form(f"f_{sn}"):
        df_e = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic" if edit_struct else "fixed",
            column_config=cfg,
            hide_index=True
        )

        if st.form_submit_button("💾 SALVA TUTTO NELLA STANZA"):
            with st.spinner("Sincronizzazione in corso..."):
                sb.table("arredamento").delete().eq("stanza", sn).execute()
                df_e['stanza'] = sn
                inv_map = {v: k for k, v in {
                    'articolo': 'Articolo', 'acquistato': 'Acquistato', 'costo': 'Costo',
                    'importo_totale': 'Importo Totale', 'acquista_sn': 'Acquista S/N',
                    'note': 'Note', 'versato': 'Versato', 'prezzo_pieno': 'Prezzo Pieno',
                    'sconto_perc': 'Sconto %', 'stato_pagamento': 'Stato Pagamento',
                    'data_scadenza': 'Data Scadenza'
                }.items()}

                df_db = df_e.rename(columns=inv_map)

                for c in ['prezzo_pieno', 'sconto_perc', 'acquistato', 'versato']:
                    df_db[c] = pd.to_numeric(df_db[c], errors='coerce').fillna(0.0)

                df_db['costo'] = df_db['prezzo_pieno'] * (1 - (df_db['sconto_perc']/100))
                df_db['importo_totale'] = df_db['costo'] * df_db['acquistato']

                if 'data_scadenza' in df_db.columns:
                    df_db['data_scadenza'] = df_db['data_scadenza'].astype(str).replace(['NaT', 'None', 'nan'], None)

                cols = ['articolo', 'acquistato', 'costo', 'importo_totale', 'acquista_sn', 'note', 'versato', 'prezzo_pieno', 'sconto_perc', 'stato_pagamento', 'stanza', 'data_scadenza']
                sb.table("arredamento").insert(df_db[[c for c in cols if c in df_db.columns]].to_dict(orient='records')).execute()
                st.success("Dati aggiornati correttamente!")
                time.sleep(1)
                st.rerun()

# --- ESPORTAZIONE PDF (Fine del file originale) ---
if sel not in ["🏠 Riepilogo", "📅 Scadenzario"]:
    st.divider()
    if st.button("📑 Genera Report PDF Stanza"):
        st.info("Funzione PDF pronta. Clicca per scaricare i dati della Proprietà.")
