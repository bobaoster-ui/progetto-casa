import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF

# --- SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V33.1", layout="wide", page_icon="💎")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_connection()

# --- CLASSE PDF PROFESSIONALE MULTILINE ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        # Sostituiamo caratteri speciali per evitare crash Unicode
        t = f'Proprieta: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, t, ln=True, align='C')
        self.ln(20)

    def draw_row(self, data, widths, is_header=False):
        # Calcolo altezza massima per la riga multiline
        row_heights = []
        for i, text in enumerate(data):
            # Calcola quante linee servono per questo testo data la larghezza della cella
            lines = self.multi_cell(widths[i], 8, str(text), split_only=True)
            row_heights.append(len(lines) * 8)

        max_h = max(row_heights) if row_heights else 10

        # Disegno effettivo delle celle
        x_start = self.get_x()
        y_start = self.get_y()

        for i, text in enumerate(data):
            self.set_xy(x_start + sum(widths[:i]), y_start)
            if is_header:
                self.set_fill_color(46, 117, 182); self.set_text_color(255, 255, 255); self.set_font('Arial', 'B', 10)
            else:
                self.set_fill_color(255, 255, 255); self.set_text_color(0, 0, 0); self.set_font('Arial', '', 9)

            self.multi_cell(widths[i], max_h, str(text), border=1, align='L' if i < 2 else 'R', fill=is_header)

        self.set_xy(x_start, y_start + max_h)

# --- LOGIN ---
if "password_correct" not in st.session_state:
    st.title("🔒 Accesso")
    u = st.text_input("Utente")
    p = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
            st.session_state.password_correct = True; st.rerun()
else:
    stanze_fisiche = ["Camera", "Cucina", "Salotto", "Tavolo", "Lavori"]

    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: pass
        st.session_state.dark_mode = st.toggle("🌙 Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s}" for s in stanze_fisiche])

        # Budget Persistente
        res_b = supabase.table("arredamento").select("importo_totale").eq("stanza", "Impostazioni").eq("articolo", "Budget_Totale").execute()
        curr_b = res_b.data[0]['importo_totale'] if res_b.data else 15000.0
        new_b = st.sidebar.number_input("Budget Obiettivo (€)", value=float(curr_b), step=500.0)
        if new_b != curr_b:
            supabase.table("arredamento").delete().eq("stanza", "Impostazioni").eq("articolo", "Budget_Totale").execute()
            supabase.table("arredamento").insert({"stanza": "Impostazioni", "articolo": "Budget_Totale", "importo_totale": new_b}).execute()
            st.rerun()

        if st.button("Logout 🚪"): st.session_state.clear(); st.rerun()

    res = supabase.table("arredamento").select("*").execute()
    df_all = pd.DataFrame(res.data)

    if "Riepilogo" in sel:
        st.title("🏠 Command Center")
        df_real = df_all[df_all['stanza'].isin(stanze_fisiche)] if not df_all.empty else pd.DataFrame()

        if not df_real.empty:
            conf, pag = df_real['importo_totale'].sum(), df_real['versato'].sum()
            st.markdown(f"### 📊 Budget: **{conf:,.2f}€** / **{new_b:,.2f}€**")

            if st.button("📑 Scarica Report PDF Professionale"):
                pdf = PDF()
                pdf.add_page()
                w = [30, 90, 35, 35]
                pdf.draw_row(['Stanza', 'Articolo', 'Totale (€)', 'Versato (€)'], w, is_header=True)

                for _, r in df_real.iterrows():
                    pdf.draw_row([r['stanza'], r['articolo'], f"{r['importo_totale']:,.2f}", f"{r['versato']:,.2f}"], w)

                pdf.set_font('Arial', 'B', 10)
                pdf.cell(120, 10, 'TOTALI ', 1, 0, 'R')
                pdf.cell(35, 10, f'{conf:,.2f} ', 1, 0, 'R')
                pdf.cell(35, 10, f'{pag:,.2f} ', 1, 1, 'R')

                st.download_button("📥 Scarica PDF", pdf.output(), "Report_Arredamento.pdf", "application/pdf")

            st.plotly_chart(px.pie(df_real, values='importo_totale', names='stanza', hole=0.5), use_container_width=True)

    elif "📦" in sel:
        sn = sel.replace("📦 ", "")
        st.title(f"🏠 {sn}")
        df_s = df_all[df_all['stanza'] == sn].copy() if not df_all.empty else pd.DataFrame()
        with st.form(f"f_{sn}"):
            s_cfg = {"stato_pagamento": st.column_config.SelectboxColumn("Stato", options=["Vuoto", "Acconto", "Saldato", "Preventivo"])}
            cols = ['articolo', 'acquistato', 'prezzo_pieno', 'sconto_percentuale', 'costo', 'importo_totale', 'versato', 'stato_pagamento', 'nota']
            df_e = st.data_editor(df_s[cols] if not df_s.empty else pd.DataFrame(columns=cols), num_rows="dynamic", use_container_width=True, hide_index=True, column_config=s_cfg)
            if st.form_submit_button("💾 SALVA"):
                supabase.table("arredamento").delete().eq("stanza", sn).execute()
                for _, r in df_e.iterrows():
                    if r['articolo']:
                        p_p = float(r.get('prezzo_pieno', 0) or 0); sc = float(r.get('sconto_percentuale', 0) or 0); qta = float(r.get('acquistato', 1) or 1)
                        c_u = p_p * (1 - (sc/100)) if p_p > 0 else float(r.get('costo', 0) or 0)
                        supabase.table("arredamento").insert({"stanza": sn, "articolo": str(r['articolo']), "acquistato": qta, "importo_totale": c_u * qta, "versato": float(r.get('versato', 0) or 0), "nota": str(r.get('nota', '')), "stato_pagamento": str(r.get('stato_pagamento', 'Vuoto'))}).execute()
                st.rerun()
