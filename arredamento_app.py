import streamlit as st
from streamlit_gsheets import GSheetsConnection
from supabase import create_client
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# --- SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V22.10.6", layout="wide", page_icon="🚀")

# --- STILE ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
bc, cc, tc = ("#0e1117", "#1d2129", "#ffffff") if st.session_state.dark_mode else ("#f8f9fc", "#ffffff", "#1f2937")
grad = "linear-gradient(90deg, #0f2027, #203a43, #2c5364)" if st.session_state.dark_mode else "linear-gradient(90deg, #2e5a88, #4a90e2)"
st.markdown(f"""<style>
    .stApp {{background-color: {bc}; color: {tc};}}
    .main-header {{background: {grad}; padding: 30px; border-radius: 15px; color: white; margin-bottom: 25px;}}
    .metric-card {{background-color: {cc}; padding: 15px; border-radius: 10px; border-bottom: 4px solid #2e5a88; text-align: center; color: {tc}; margin-bottom: 10px;}}
    .metric-value {{font-size: 1.8em; font-weight: 800; color: #2e5a88;}}
</style>""", unsafe_allow_html=True)

class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182); self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10); t = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, t.encode('latin-1','replace').decode('latin-1'), ln=True, align='C'); self.ln(15)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(128, 128, 128)
        self.cell(0, 10, "Prodotto di Proprietà: Roberto & Gemini".encode('latin-1','replace').decode('latin-1'), 0, 0, 'C')

def clean_val(val, default=0):
    """Pulisce i valori NaN per evitare errori JSON con Supabase"""
    if pd.isna(val): return default
    return val

if "password_correct" not in st.session_state:
    st.title("🔒 Accesso")
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]: st.session_state.password_correct = True; st.rerun()
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: st.info("Logo non trovato")
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "🛠️ Migrazione Database"] + [f"📦 {s.capitalize()}" for s in stanze])

    if sel == "🏠 Riepilogo":
        st.markdown('<div class="main-header"><h1>Command Center</h1><p>Proprietà: Jacopo</p></div>', unsafe_allow_html=True)
        st.write("Dati caricati da Google Sheets (Stabile).")

    elif sel == "🛠️ Migrazione Database":
        st.title("🚀 Migrazione")
        if "supabase" not in st.secrets:
            st.error("⚠️ Configurazione [supabase] non trovata nei Secrets.")
        else:
            if st.button("AVVIA TRASLOCO DATI"):
                try:
                    sb = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
                    for s in stanze + ["desideri"]:
                        st.write(f"Migrazione stanza: {s}...")
                        df = conn.read(worksheet=s)
                        for _, row in df.iterrows():
                            # Mappatura con pulizia dei NaN
                            d = {
                                "articolo": str(row.get('Articolo', row.get('Oggetto', 'N/A'))),
                                "acquistato": float(clean_val(row.get('Acquistato'), 1)),
                                "costo": float(clean_val(row.get('Costo'), 0)),
                                "importo_totale": float(clean_val(row.get('Importo Totale'), 0)),
                                "acquista_sn": str(row.get('Acquista S/N', 'N')),
                                "stanza": "Wishlist" if s == "desideri" else s.capitalize(),
                                "note": str(clean_val(row.get('Note'), '')),
                                "versato": float(clean_val(row.get('Versato'), 0)),
                                "prezzo_pieno": float(clean_val(row.get('Prezzo Pieno'), 0)),
                                "sconto_perc": float(clean_val(row.get('Sconto %'), 0)),
                                "stato_pagamento": str(clean_val(row.get('Stato Pagamento'), '')),
                                "link_fattura": str(clean_val(row.get('Link Fattura'), '')),
                                "link": str(clean_val(row.get('Link'), '')),
                                "foto": str(clean_val(row.get('Foto'), ''))
                            }
                            sb.table("arredamento").insert(d).execute()
                    st.success("✅ Migrazione completata con successo!")
                except Exception as e: st.error(f"Errore tecnico: {e}")
