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

st.set_page_config(page_title="Monitoraggio Arredamento V41.0", layout="wide", page_icon="💎")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_connection()

# --- MOTORE PDF CON FIX SOVRAPPOSIZIONE (Immagine 4) ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182); self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        t = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, t.encode('latin-1','replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

    def draw_row(self, data, w):
        lines = [len(self.multi_cell(w[i], 7, str(txt), split_only=True)) for i, txt in enumerate(data)]
        h = max(lines) * 7
        if h < 8: h = 8
        x, y = self.get_x(), self.get_y()
        if y + h > 270: self.add_page(); y = self.get_y()
        for i, txt in enumerate(data):
            self.set_xy(x + sum(w[:i]), y)
            self.multi_cell(w[i], h, str(txt), border=1, align='L' if i < 2 else 'R')
        self.set_xy(x, y + h)

# --- LOGIN ---
if "password_correct" not in st.session_state: st.session_state.password_correct = False

if not st.session_state.password_correct:
    st.title("🔒 Accesso")
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
            st.session_state.password_correct = True; st.rerun()
else:
    stanze_fisiche = ["Camera", "Cucina", "Salotto", "Tavolo", "Lavori"]
    with st.sidebar:
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s}" for s in stanze_fisiche])
        st.markdown(f"<br><small>Proprietà: Jacopo</small>", unsafe_allow_html=True)
        if st.button("Logout 🚪"): st.session_state.clear(); st.rerun()

    # Lettura dati (Fix crash data Immagine 7)
    resp = supabase.table("arredamento").select("*").execute()
    df_all = pd.DataFrame(resp.data)
    if not df_all.empty:
        df_all['scadenza'] = pd.to_datetime(df_all['scadenza'], errors='coerce')

    if "Riepilogo" in sel:
        st.title("🏠 Command Center")
        df_r = df_all[df_all['stanza'].isin(stanze_fisiche)] if not df_all.empty else pd.DataFrame()
        if not df_r.empty:
            # --- 1. METRICHE ---
            c1, c2, c3 = st.columns(3)
            tot, pag = df_r['importo_totale'].sum(), df_r['versato'].sum()
            c1.metric("CONFERMATO", f"{tot:,.2f} €")
            c2.metric("PAGATO", f"{pag:,.2f} €")
            c3.metric("DA PAGARE", f"{tot-pag:,.2f} €")

            # --- 2. GRAFICI E SCADENZARIO (Ripristinati) ---
            g1, g2 = st.columns([1, 1.2])
            with g1:
                st.plotly_chart(px.pie(df_r, values='importo_totale', names='stanza', hole=0.5, title="Spesa per Stanza"), use_container_width=True)
            with g2:
                st.subheader("🗓️ Scadenzario")
                sc = df_r[df_r['scadenza'].notna() & (df_r['versato'] < df_r['importo_totale'])].copy()
                if not sc.empty:
                    sc['gg'] = (sc['scadenza'].dt.date - datetime.now().date()).apply(lambda x: x.days)
                    sc['Stato'] = sc['gg'].apply(lambda x: "🔴 SCADUTO" if x < 0 else ("🟠 < 7gg" if x <= 7 else "🟢 OK"))
                    st.dataframe(sc.sort_values('gg')[['stanza','articolo','scadenza','Stato']], use_container_width=True, hide_index=True)

            # --- 3. PDF (Fix Bytearray Immagine 8) ---
            if st.button("📑 Genera Report PDF"):
                pdf = PDF(); pdf.add_page(); w = [30, 85, 35, 35]
                pdf.set_fill_color(200, 220, 255); pdf.set_font('Arial', 'B', 10)
                pdf.cell(w[0], 10, "Stanza", 1, 0, 'C', 1); pdf.cell(w[1], 10, "Articolo", 1, 0, 'C', 1)
                pdf.cell(w[2], 10, "Totale", 1, 0, 'C', 1); pdf.cell(w[3], 10, "Versato", 1, 1, 'C', 1)
                pdf.set_font('Arial', '', 9)
                for _, r in df_r.iterrows():
                    art_puro = str(r['articolo']).encode('latin-1', 'replace').decode('latin-1')
                    pdf.draw_row([r['stanza'], art_puro, f"{r['importo_totale']:.2f}", f"{r['versato']:.2f}"], w)

                buf = io.BytesIO()
                pdf_data = pdf.output(dest='S')
                buf.write(pdf_data.encode('latin-1') if isinstance(pdf_data, str) else pdf_data)
                st.download_button("📥 Scarica PDF", buf.getvalue(), "Report.pdf", "application/pdf")

    elif "📦" in sel:
        sn = sel.replace("📦 ", "")
        st.title(f"🏠 {sn}")
        df_s = df_all[df_all['stanza'] == sn].copy() if not df_all.empty else pd.DataFrame()
        with st.form(f"f_{sn}"):
            # Ripristino Menu Tendina e Colonne (Fix immagine 11)
            cfg = {
                "stato_pagamento": st.column_config.SelectboxColumn("Stato", options=["Vuoto", "Preventivo", "Acconto", "Saldato"]),
                "scadenza": st.column_config.DateColumn("Scadenza"),
                "importo_totale": st.column_config.NumberColumn("Totale (€)", disabled=True)
            }
            cols = ['articolo', 'acquistato', 'prezzo_pieno', 'sconto_percentuale', 'costo', 'importo_totale', 'versato', 'stato_pagamento', 'scadenza', 'nota']
            df_ed = st.data_editor(df_s[cols] if not df_s.empty else pd.DataFrame(columns=cols), num_rows="dynamic", use_container_width=True, column_config=cfg)
            if st.form_submit_button("💾 SALVA"):
                supabase.table("arredamento").delete().eq("stanza", sn).execute()
                for _, r in df_ed.iterrows():
                    if r['articolo']:
                        p_p = float(r.get('prezzo_pieno', 0) or 0)
                        sc = float(r.get('sconto_percentuale', 0) or 0)
                        qta = float(r.get('acquistato', 1) or 1)
                        c_u = p_p * (1 - (sc/100)) if p_p > 0 else float(r.get('costo', 0) or 0)
                        supabase.table("arredamento").insert({
                            "stanza": sn, "articolo": str(r['articolo']), "acquistato": qta, "prezzo_pieno": p_p,
                            "sconto_percentuale": sc, "costo": c_u, "importo_totale": c_u * qta,
                            "versato": float(r.get('versato', 0) or 0), "stato_pagamento": str(r.get('stato_pagamento', 'Vuoto')),
                            "scadenza": str(r['scadenza']) if pd.notnull(r.get('scadenza')) else None, "nota": str(r.get('nota', ''))
                        }).execute()
                st.rerun()

    elif "✨ Wishlist" in sel:
        st.title("✨ Wishlist")
        df_w = df_all[df_all['stanza'] == "Wishlist"].copy() if not df_all.empty else pd.DataFrame()
        df_ew = st.data_editor(df_w[['articolo', 'importo_totale', 'link_fattura', 'link_foto', 'nota']], num_rows="dynamic", use_container_width=True)
        if st.button("💾 SALVA WISHLIST"):
            supabase.table("arredamento").delete().eq("stanza", "Wishlist").execute()
            for _, r in df_ew.iterrows():
                if r['articolo']:
                    supabase.table("arredamento").insert({"stanza": "Wishlist", "articolo": str(r['articolo']), "importo_totale": float(r.get('importo_totale', 0) or 0), "link_fattura": str(r.get('link_fattura', '')), "link_foto": str(r.get('link_foto', '')), "nota": str(r.get('nota', ''))}).execute()
            st.rerun()
