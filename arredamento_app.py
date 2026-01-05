import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF

# --- SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V33.0", layout="wide", page_icon="💎")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_connection()

# --- CLASSE PDF PROFESSIONALE (TABLE MULTILINE) ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182) # Blu testata
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Helvetica', 'I', 10)
        t = f'Proprieta: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, t, ln=True, align='C')
        self.ln(20)

    def draw_table_header(self):
        self.set_fill_color(46, 117, 182)
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 10)
        self.cell(30, 10, ' Stanza', 1, 0, 'L', True)
        self.cell(90, 10, ' Articolo', 1, 0, 'L', True)
        self.cell(35, 10, ' Totale', 1, 0, 'C', True)
        self.cell(35, 10, ' Versato', 1, 1, 'C', True)

# --- STILE ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
bc, cc, tc = ("#0e1117", "#1d2129", "#ffffff") if st.session_state.dark_mode else ("#f8f9fc", "#ffffff", "#1f2937")
st.markdown(f"<style>.stApp {{background-color: {bc}; color: {tc};}}</style>", unsafe_allow_html=True)

# --- LOGIN (Etichette Utente/Password ripristinate) ---
if "password_correct" not in st.session_state:
    st.title("🔒 Accesso")
    u = st.text_input("Utente")
    p = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
            st.session_state.password_correct = True
            st.rerun()
else:
    stanze_fisiche = ["Camera", "Cucina", "Salotto", "Tavolo", "Lavori"]

    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: pass
        st.session_state.dark_mode = st.toggle("🌙 Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s}" for s in stanze_fisiche])

        # Budget Persistente su DB
        res_b = supabase.table("arredamento").select("importo_totale").eq("stanza", "Impostazioni").eq("articolo", "Budget_Totale").execute()
        curr_b = res_b.data[0]['importo_totale'] if res_b.data else 15000.0
        new_b = st.number_input("Budget Obiettivo (€)", value=float(curr_b), step=500.0)
        if new_b != curr_b:
            supabase.table("arredamento").delete().eq("stanza", "Impostazioni").eq("articolo", "Budget_Totale").execute()
            supabase.table("arredamento").insert({"stanza": "Impostazioni", "articolo": "Budget_Totale", "importo_totale": new_b}).execute()
            st.rerun()

        st.markdown("<br>---<br>✨ **Roberto & Gemini**<br><small>Proprieta: Jacopo</small>", unsafe_allow_html=True)
        if st.button("Logout 🚪"): st.session_state.clear(); st.rerun()

    response = supabase.table("arredamento").select("*").execute()
    df_all = pd.DataFrame(response.data)
    if not df_all.empty:
        df_all['scadenza'] = pd.to_datetime(df_all['scadenza'], errors='coerce').dt.date

    if "Riepilogo" in sel:
        st.title("🏠 Command Center")
        df_real = df_all[df_all['stanza'].isin(stanze_fisiche)] if not df_all.empty else pd.DataFrame()

        if not df_real.empty:
            conf, pag = df_real['importo_totale'].sum(), df_real['versato'].sum()
            st.markdown(f"### 📊 Budget: **{conf:,.2f}€** / **{new_b:,.2f}€**")
            st.progress(min(conf / new_b, 1.0))

            # --- GENERAZIONE PDF PROFESSIONALE ---
            if st.button("📑 Scarica Report PDF Professionale"):
                pdf = PDF()
                pdf.add_page()
                pdf.draw_table_header()
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Helvetica', '', 9)

                for _, r in df_real.iterrows():
                    # Calcolo altezza riga dinamica in base all'articolo
                    txt = str(r['articolo'])
                    h = 10 if pdf.get_string_width(txt) < 85 else 16

                    x, y = pdf.get_x(), pdf.get_y()
                    pdf.multi_cell(30, h, f" {r['stanza']}", 1, 'L')
                    pdf.set_xy(x + 30, y)
                    pdf.multi_cell(90, h, f" {txt}", 1, 'L')
                    pdf.set_xy(x + 120, y)
                    pdf.multi_cell(35, h, f"{r['importo_totale']:,.2f} ", 1, 'R')
                    pdf.set_xy(x + 155, y)
                    pdf.multi_cell(35, h, f"{r['versato']:,.2f} ", 1, 'R')

                # Riga Totali
                pdf.set_font('Helvetica', 'B', 10)
                pdf.cell(120, 10, ' TOTALI', 1, 0, 'R')
                pdf.cell(35, 10, f'{conf:,.2f} ', 1, 0, 'R')
                pdf.cell(35, 10, f'{pag:,.2f} ', 1, 1, 'R')

                st.download_button("📥 Clicca qui per il PDF", pdf.output(), f"Report_Jacopo_{datetime.now().strftime('%d%m%Y')}.pdf", "application/pdf")

            st.plotly_chart(px.pie(df_real, values='importo_totale', names='stanza', hole=0.5), use_container_width=True)

            # Scadenzario
            st.subheader("🗓️ Scadenzario")
            sc = df_real[df_real['scadenza'].notna() & (df_real['versato'] < df_real['importo_totale'])].copy()
            if not sc.empty:
                sc['gg'] = (sc['scadenza'] - datetime.now().date()).apply(lambda x: x.days)
                sc['Stato'] = sc['gg'].apply(lambda x: "🔴 SCADUTO" if x < 0 else ("🟠 IMMINENTE" if x <= 7 else "🟢 OK"))
                st.dataframe(sc.sort_values('gg')[['stanza','articolo','scadenza','Stato']], use_container_width=True, hide_index=True)

    elif "📦" in sel:
        sn = sel.replace("📦 ", "")
        st.title(f"🏠 {sn}")
        df_s = df_all[df_all['stanza'] == sn].copy()
        with st.form(f"f_{sn}"):
            s_cfg = {
                "stato_pagamento": st.column_config.SelectboxColumn("Stato", options=["Vuoto", "Acconto", "Saldato", "Preventivo"]),
                "scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"),
                "importo_totale": st.column_config.NumberColumn("Totale €", disabled=True, format="%.2f €")
            }
            cols = ['articolo', 'acquistato', 'prezzo_pieno', 'sconto_percentuale', 'costo', 'importo_totale', 'versato', 'stato_pagamento', 'scadenza', 'nota']
            df_e = st.data_editor(df_s[cols] if not df_s.empty else pd.DataFrame(columns=cols), num_rows="dynamic", use_container_width=True, hide_index=True, column_config=s_cfg)

            if st.form_submit_button("💾 SALVA"):
                supabase.table("arredamento").delete().eq("stanza", sn).execute()
                for _, r in df_e.iterrows():
                    if r['articolo']:
                        p_p = float(r.get('prezzo_pieno', 0) or 0); sc = float(r.get('sconto_percentuale', 0) or 0); qta = float(r.get('acquistato', 1) or 1)
                        c_u = p_p * (1 - (sc/100)) if p_p > 0 else float(r.get('costo', 0) or 0)
                        supabase.table("arredamento").insert({"stanza": sn, "articolo": str(r['articolo']), "acquistato": qta, "prezzo_pieno": p_p, "sconto_percentuale": sc, "costo": c_u, "importo_totale": c_u * qta, "versato": float(r.get('versato', 0) or 0), "nota": str(r.get('nota', '')), "stato_pagamento": str(r.get('stato_pagamento', 'Vuoto')), "scadenza": str(r['scadenza']) if pd.notnull(r.get('scadenza')) else None}).execute()
                st.rerun()
