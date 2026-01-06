import streamlit as st
from streamlit_gsheets import GSheetsConnection
from supabase import create_client
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import time

# --- SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V22.10.3", layout="wide", page_icon="🚀")

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

def clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    df['DV'] = df['Articolo'] if 'Articolo' in df.columns else df.get('Oggetto', 'N/A')
    for c in ['Importo Totale', 'Versato']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    return df

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
        all_d = []
        for s in stanze:
            try:
                d = clean_df(conn.read(worksheet=s, ttl="1m"))
                if not d.empty: d['Stanza'] = s.capitalize(); all_d.append(d)
            except: continue
        if all_d:
            df_r = pd.concat(all_d); conf, pag = df_r['Importo Totale'].sum(), df_r['Versato'].sum()
            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="metric-card">IMPEGNATO<div class="metric-value">{conf:,.2f}€</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card">PAGATO<div class="metric-value">{pag:,.2f}€</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card">RESIDUO<div class="metric-value">{conf-pag:,.2f}€</div></div>', unsafe_allow_html=True)

            if st.button("📄 Genera Report PDF"):
                p = PDF(); p.add_page(); p.set_font('Arial','B',10)
                p.set_fill_color(46,117,182); p.set_text_color(255,255,255)
                p.cell(30,10,'Stanza',1,0,'C',1); p.cell(90,10,'Articolo',1,0,'C',1); p.cell(35,10,'Totale',1,0,'C',1); p.cell(35,10,'Versato',1,1,'C',1)
                p.set_font('Arial','',9); p.set_text_color(0,0,0)
                for _, r in df_r.iterrows():
                    p.cell(30,10, str(r['Stanza']),1)
                    p.cell(90,10, str(r['DV'])[:45].encode('latin-1','replace').decode('latin-1'),1)
                    p.cell(35,10, f"{r['Importo Totale']:,.2f}",1)
                    p.cell(35,10, f"{r['Versato']:,.2f}",1,1)
                st.download_button("📥 Scarica PDF", bytes(p.output(dest='S')), "Report.pdf")

    elif sel == "🛠️ Migrazione Database":
        st.title("🚀 Migrazione")
        if st.button("AVVIA TRASLOCO DATI"):
            try:
                # CREO IL CLIENT SOLO QUI PER EVITARE ERRORI ALL'AVVIO
                sb = create_client(st.secrets["supabase_url"], st.secrets["supabase_key"])
                for s in stanze + ["desideri"]:
                    df = conn.read(worksheet=s)
                    for _, row in df.iterrows():
                        d = {
                            "articolo": str(row.get('Articolo', row.get('Oggetto', 'N/A'))),
                            "acquistato": float(row.get('Acquistato', 1)),
                            "costo": float(row.get('Costo', 0)),
                            "importo_totale": float(row.get('Importo Totale', 0)),
                            "acquista_sn": str(row.get('Acquista S/N', 'N')),
                            "stanza": "Wishlist" if s == "desideri" else s.capitalize(),
                            "note": str(row.get('Note', '')),
                            "versato": float(row.get('Versato', 0))
                        }
                        sb.table("arredamento").insert(d).execute()
                st.success("✅ Migrazione completata!")
            except Exception as e: st.error(f"Errore: {e}")
