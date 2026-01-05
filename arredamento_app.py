import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import io

# --- REGOLE DELLA PROPRIETÀ ---
# La parola "Proprietà" si scrive con la "à" accentata.

if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V39.0", layout="wide", page_icon="💎")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_connection()

# --- CLASSE PDF PROFESSIONALE (TABELLARE) ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182); self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        t = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, t.encode('latin-1','replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

    def table_row(self, data, w):
        # Calcolo altezza dinamica per evitare righe sovrascritte
        lines = [len(self.multi_cell(w[i], 7, str(txt), split_only=True)) for i, txt in enumerate(data)]
        h = max(lines) * 7
        x, y = self.get_x(), self.get_y()
        for i, txt in enumerate(data):
            self.set_xy(x + sum(w[:i]), y)
            self.multi_cell(w[i], h, str(txt), border=1, align='L' if i < 2 else 'R')
        self.set_xy(x, y + h)

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

if "password_correct" not in st.session_state:
    st.title("🔒 Accesso")
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
            st.session_state.password_correct = True; st.rerun()
else:
    stanze_fisiche = ["Camera", "Cucina", "Salotto", "Tavolo", "Lavori"]

    with st.sidebar:
        st.session_state.dark_mode = st.toggle("🌙 Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s}" for s in stanze_fisiche])
        st.markdown(f"<br>---<br><small>Proprietà: Jacopo</small>", unsafe_allow_html=True)
        if st.button("Logout 🚪"): st.session_state.clear(); st.rerun()

    # Lettura dati sicura (Fix crash aggiunta riga)
    resp = supabase.table("arredamento").select("*").execute()
    df_all = pd.DataFrame(resp.data)
    if not df_all.empty:
        df_all['scadenza'] = pd.to_datetime(df_all['scadenza'], errors='coerce')

    if "Riepilogo" in sel:
        st.markdown('<div class="main-header"><h1>Command Center</h1><p>Proprietà: Jacopo</p></div>', unsafe_allow_html=True)
        df_real = df_all[df_all['stanza'].isin(stanze_fisiche)] if not df_all.empty else pd.DataFrame()

        if not df_real.empty:
            conf, pag = df_real['importo_totale'].sum(), df_real['versato'].sum()
            budget_max = st.sidebar.number_input("Budget Totale (€)", value=50000, step=1000)

            m1, m2, m3 = st.columns(3)
            m1.markdown(f'<div class="metric-card">CONFERMATO<div class="metric-value">{conf:,.2f}€</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card">PAGATO<div class="metric-value">{pag:,.2f}€</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card">DA PAGARE<div class="metric-value">{conf-pag:,.2f}€</div></div>', unsafe_allow_html=True)

            c1, c2 = st.columns([1, 1.2])
            with c1: st.plotly_chart(px.pie(df_real, values='importo_totale', names='stanza', hole=0.5), use_container_width=True)
            with c2:
                st.subheader("🗓️ Scadenzario")
                sc = df_real[df_real['scadenza'].notna() & (df_real['versato'] < df_real['importo_totale'])].copy()
                if not sc.empty:
                    sc['gg'] = (sc['scadenza'].dt.date - datetime.now().date()).apply(lambda x: x.days)
                    sc['Stato'] = sc['gg'].apply(lambda x: "🔴 SCADUTO" if x < 0 else ("🟠 IMMINENTE" if x <= 7 else "🟢 OK"))
                    st.dataframe(sc.sort_values('gg')[['stanza','articolo','scadenza','Stato']], use_container_width=True, hide_index=True)

            if st.button("📑 Genera Report PDF"):
                pdf = PDF()
                pdf.add_page()
                w = [30, 85, 35, 35]
                # Header Tabella
                pdf.set_fill_color(200, 220, 255); pdf.set_font('Arial', 'B', 10)
                pdf.cell(w[0], 10, "Stanza", 1, 0, 'C', True); pdf.cell(w[1], 10, "Articolo", 1, 0, 'C', True)
                pdf.cell(w[2], 10, "Totale", 1, 0, 'C', True); pdf.cell(w[3], 10, "Versato", 1, 1, 'C', True)

                pdf.set_font('Arial', '', 9)
                for _, r in df_real.iterrows():
                    art = str(r['articolo']).encode('latin-1', 'replace').decode('latin-1')
                    pdf.table_row([r['stanza'], art, f"{r['importo_totale']:.2f}", f"{r['versato']:.2f}"], w)

                # Fix finale Bytearray
                buf = io.BytesIO()
                pdf_bin = pdf.output(dest='S')
                buf.write(pdf_bin.encode('latin-1') if isinstance(pdf_bin, str) else pdf_bin)
                st.download_button("📥 Scarica PDF", buf.getvalue(), "Report.pdf", "application/pdf")

    elif "Wishlist" in sel or "📦" in sel:
        sn = "Wishlist" if "Wishlist" in sel else sel.replace("📦 ", "")
        st.title(f"📍 {sn}")
        df_s = df_all[df_all['stanza'] == sn].copy() if not df_all.empty else pd.DataFrame()

        with st.form(f"f_{sn}"):
            cols = ['articolo', 'acquistato', 'prezzo_pieno', 'sconto_percentuale', 'versato', 'scadenza', 'nota'] if sn != "Wishlist" else ['articolo', 'importo_totale', 'link_fattura', 'link_foto', 'nota']
            df_ed = st.data_editor(df_s[cols] if not df_s.empty else pd.DataFrame(columns=cols), num_rows="dynamic", use_container_width=True)

            if st.form_submit_button("💾 SALVA"):
                supabase.table("arredamento").delete().eq("stanza", sn).execute()
                for _, r in df_ed.iterrows():
                    if r['articolo']:
                        p_p = float(r.get('prezzo_pieno', 0) or 0)
                        sc = float(r.get('sconto_percentuale', 0) or 0)
                        qta = float(r.get('acquistato', 1) or 1)
                        c_u = p_p * (1 - (sc/100)) if p_p > 0 else float(r.get('importo_totale', 0) or 0)
                        scad = str(r['scadenza']) if pd.notnull(r.get('scadenza')) else None

                        supabase.table("arredamento").insert({
                            "stanza": sn, "articolo": str(r['articolo']), "acquistato": qta,
                            "prezzo_pieno": p_p, "sconto_percentuale": sc, "costo": c_u,
                            "importo_totale": c_u * qta, "versato": float(r.get('versato', 0) or 0),
                            "scadenza": scad, "nota": str(r.get('nota', '')),
                            "link_fattura": str(r.get('link_fattura', '')), "link_foto": str(r.get('link_foto', ''))
                        }).execute()
                st.rerun()
