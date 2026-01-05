import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import time

# --- SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V30.8", layout="wide", page_icon="💎")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_connection()

# --- CLASSE PDF (Versione senza errori di codifica) ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182); self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10); t = f'Proprieta: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, t, ln=True, align='C'); self.ln(15)

if "password_correct" not in st.session_state:
    st.title("🔒 Accesso")
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]: st.session_state.password_correct = True; st.rerun()
else:
    stanze_fisiche = ["Camera", "Cucina", "Salotto", "Tavolo", "Lavori"]

    with st.sidebar:
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s}" for s in stanze_fisiche])
        st.markdown("---<br>✨ **Roberto & Gemini**<br><small>Proprietà: Jacopo</small>", unsafe_allow_html=True)

    # Lettura dati
    res = supabase.table("arredamento").select("*").execute()
    df_all = pd.DataFrame(res.data)
    if not df_all.empty:
        df_all['scadenza'] = pd.to_datetime(df_all['scadenza'], errors='coerce').dt.date

    if "Riepilogo" in sel:
        st.title("🏠 Command Center")
        df_real = df_all[df_all['stanza'].isin(stanze_fisiche)] if not df_all.empty else pd.DataFrame()
        if not df_real.empty:
            conf, pag = df_real['importo_totale'].sum(), df_real['versato'].sum()
            budget_max = st.sidebar.number_input("Budget Obiettivo (€)", value=50000)

            # BUDGET VISIBILE
            st.markdown(f"### 📊 Budget: **{conf:,.2f}€** / **{budget_max:,.2f}€**")
            st.progress(min(conf / budget_max, 1.0))
            st.info(f"✅ Residuo Budget: {(budget_max - conf):,.2f}€")

            if st.button("📑 Scarica PDF Riepilogo"):
                pdf = PDF(); pdf.add_page(); pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, f"Totale Impegnato: {conf:,.2f} EUR", ln=True)
                pdf.cell(0, 10, f"Totale Versato: {pag:,.2f} EUR", ln=True)
                pdf.cell(0, 10, f"Residuo da versare: {conf-pag:,.2f} EUR", ln=True)
                st.download_button("Download PDF", pdf.output(), "Report_Jacopo.pdf", "application/pdf")

    elif "📦" in sel:
        sn = sel.replace("📦 ", "")
        st.title(f"🏠 {sn}")
        df_s = df_all[df_all['stanza'] == sn].copy()

        with st.form(f"f_{sn}"):
            # Menu a discesa solo per lo Stato Pagamento
            s_cfg = {
                "stato_pagamento": st.column_config.SelectboxColumn("Stato Pagamento", options=["Vuoto", "Acconto", "Saldato", "Preventivo"]),
                "scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"),
                "importo_totale": st.column_config.NumberColumn("Totale €", format="%.2f €", disabled=True)
            }
            # Rimosso acquisto_sn dalle colonne visualizzate
            cols_edit = ['articolo', 'acquistato', 'prezzo_pieno', 'sconto_percentuale', 'costo', 'importo_totale', 'versato', 'stato_pagamento', 'scadenza', 'nota']

            df_e = st.data_editor(df_s[cols_edit] if not df_s.empty else pd.DataFrame(columns=cols_edit), num_rows="dynamic", use_container_width=True, hide_index=True, column_config=s_cfg)

            if st.form_submit_button("💾 SALVA"):
                supabase.table("arredamento").delete().eq("stanza", sn).execute()
                for _, r in df_e.iterrows():
                    if r['articolo']:
                        p_p = float(r.get('prezzo_pieno', 0) or 0)
                        sc = float(r.get('sconto_percentuale', 0) or 0)
                        qta = float(r.get('acquistato', 1) or 1)
                        c_u = p_p * (1 - (sc/100)) if p_p > 0 else float(r.get('costo', 0) or 0)

                        supabase.table("arredamento").insert({
                            "stanza": sn, "articolo": str(r['articolo']),
                            "acquistato": qta, "prezzo_pieno": p_p, "sconto_percentuale": sc,
                            "costo": c_u, "importo_totale": c_u * qta,
                            "versato": float(r.get('versato', 0) or 0), "nota": str(r.get('nota', '')),
                            "stato_pagamento": str(r.get('stato_pagamento', 'Vuoto')),
                            "scadenza": str(r['scadenza']) if pd.notnull(r.get('scadenza')) else None
                        }).execute()
                st.balloons(); st.rerun()
