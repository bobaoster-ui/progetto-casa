import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import io

# --- SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V32.0", layout="wide", page_icon="💎")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_connection()

# --- CLASSE PDF PROFESSIONALE (RIPRISTINATA) ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182) # Blu Professionale
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Helvetica', 'I', 10)
        t = f'Proprieta: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, t, ln=True, align='C')
        self.ln(20)

# --- STILE DASHBOARD ---
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
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]: st.session_state.password_correct = True; st.rerun()
else:
    stanze_fisiche = ["Camera", "Cucina", "Salotto", "Tavolo", "Lavori"]

    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: pass
        st.session_state.dark_mode = st.toggle("🌙 Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s}" for s in stanze_fisiche])

        # --- BUDGET PERSISTENTE (FISSO) ---
        res_b = supabase.table("arredamento").select("importo_totale").eq("stanza", "Impostazioni").eq("articolo", "Budget_Totale").execute()
        current_b = res_b.data[0]['importo_totale'] if res_b.data else 15000.0
        new_budget = st.number_input("Budget Obiettivo (€)", value=float(current_b), step=500.0)
        if new_budget != current_b:
            supabase.table("arredamento").delete().eq("stanza", "Impostazioni").eq("articolo", "Budget_Totale").execute()
            supabase.table("arredamento").insert({"stanza": "Impostazioni", "articolo": "Budget_Totale", "importo_totale": new_budget}).execute()
            st.rerun()

        st.markdown("<br>---<br>✨ **Roberto & Gemini**<br><small>Proprietà: Jacopo</small>", unsafe_allow_html=True)
        if st.button("Logout 🚪"): st.session_state.clear(); st.rerun()

    # Lettura dati
    response = supabase.table("arredamento").select("*").execute()
    df_all = pd.DataFrame(response.data)
    if not df_all.empty:
        df_all['scadenza'] = pd.to_datetime(df_all['scadenza'], errors='coerce').dt.date

    if "Riepilogo" in sel:
        st.markdown('<div class="main-header"><h1>Command Center</h1><p>Proprietà: Jacopo</p></div>', unsafe_allow_html=True)
        df_real = df_all[df_all['stanza'].isin(stanze_fisiche)] if not df_all.empty else pd.DataFrame()

        if not df_real.empty:
            conf, pag = df_real['importo_totale'].sum(), df_real['versato'].sum()
            st.markdown(f"### 📊 Budget: **{conf:,.2f}€** / **{new_budget:,.2f}€**")
            st.progress(min(conf / new_budget, 1.0))

            m1, m2, m3 = st.columns(3)
            m1.markdown(f'<div class="metric-card">CONFERMATO<div class="metric-value">{conf:,.0f}€</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card">PAGATO<div class="metric-value">{pag:,.0f}€</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card">DA PAGARE<div class="metric-value">{conf-pag:,.0f}€</div></div>', unsafe_allow_html=True)

            c1, c2 = st.columns([1, 1.2])
            with c1:
                st.plotly_chart(px.pie(df_real, values='importo_totale', names='stanza', hole=0.5), use_container_width=True)
            with c2:
                st.subheader("🗓️ Scadenzario")
                sc = df_real[df_real['scadenza'].notna() & (df_real['versato'] < df_real['importo_totale'])].copy()
                if not sc.empty:
                    sc['gg'] = (sc['scadenza'] - datetime.now().date()).apply(lambda x: x.days)
                    sc['Stato'] = sc['gg'].apply(lambda x: "🔴 SCADUTO" if x < 0 else ("🟠 IMMINENTE" if x <= 7 else "🟢 OK"))
                    st.dataframe(sc.sort_values('gg')[['stanza','articolo','scadenza','Stato']], use_container_width=True, hide_index=True)
                else:
                    st.write("✅ Tutto in regola.")

            # --- FIX PDF DEFINITIVO (METODO BUFFER) ---
            pdf = PDF()
            pdf.add_page()
            pdf.set_text_color(31, 41, 55)
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 10, "RIEPILOGO FINANZIARIO GENERALE", ln=True)
            pdf.set_font('Helvetica', '', 12)
            pdf.cell(0, 8, f"- Totale Impegnato: {conf:,.2f} EUR", ln=True)
            pdf.cell(0, 8, f"- Totale Pagato: {pag:,.2f} EUR", ln=True)
            pdf.cell(0, 8, f"- Residuo da Versare: {conf-pag:,.2f} EUR", ln=True)

            # Generiamo i dati binari e li mettiamo in un pulsante di download sicuro
            pdf_output = pdf.output()
            st.download_button(
                label="📑 Scarica Report PDF Professionale",
                data=bytes(pdf_output),
                file_name=f"Report_Arredamento_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )

    elif "📦" in sel:
        sn = sel.replace("📦 ", "")
        st.title(f"🏠 {sn}")
        df_s = df_all[df_all['stanza'] == sn].copy()
        with st.form(f"form_{sn}"):
            check_chiusura = st.checkbox("🔒 Chiudi Stanza", value=df_s['stanza_chiusa'].any() if not df_s.empty else False)
            s_cfg = {
                "stato_pagamento": st.column_config.SelectboxColumn("Stato Pagamento", options=["Vuoto", "Acconto", "Saldato", "Preventivo"]),
                "scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"),
                "importo_totale": st.column_config.NumberColumn("Totale €", disabled=True, format="%.2f €")
            }
            cols_s = ['articolo', 'acquistato', 'prezzo_pieno', 'sconto_percentuale', 'costo', 'importo_totale', 'versato', 'stato_pagamento', 'scadenza', 'nota']
            df_e = st.data_editor(df_s[cols_s] if not df_s.empty else pd.DataFrame(columns=cols_s), num_rows="dynamic", use_container_width=True, hide_index=True, column_config=s_cfg)

            if st.form_submit_button("💾 SALVA"):
                supabase.table("arredamento").delete().eq("stanza", sn).execute()
                for _, r in df_e.iterrows():
                    if r['articolo']:
                        p_p = float(r.get('prezzo_pieno', 0) or 0); sc = float(r.get('sconto_percentuale', 0) or 0); qta = float(r.get('acquistato', 1) or 1)
                        c_u = p_p * (1 - (sc/100)) if p_p > 0 else float(r.get('costo', 0) or 0)
                        supabase.table("arredamento").insert({"stanza": sn, "articolo": str(r['articolo']), "acquistato": qta, "prezzo_pieno": p_p, "sconto_percentuale": sc, "costo": c_u, "importo_totale": c_u * qta, "versato": float(r.get('versato', 0) or 0), "nota": str(r.get('nota', '')), "stato_pagamento": str(r.get('stato_pagamento', 'Vuoto')), "scadenza": str(r['scadenza']) if pd.notnull(r.get('scadenza')) else None, "stanza_chiusa": check_chiusura}).execute()
                st.balloons(); st.rerun()

    elif "Wishlist" in sel:
        st.title("✨ Wishlist")
        df_w = df_all[df_all['stanza'] == "Wishlist"].copy() if not df_all.empty else pd.DataFrame()
        with st.form("f_wish"):
            w_cfg = {"link_fattura": st.column_config.LinkColumn("🔗 Sito Web", display_text="Apri Sito"), "link_foto": st.column_config.LinkColumn("📸 Foto", display_text="Apri Foto")}
            cols_w = ['articolo', 'importo_totale', 'link_fattura', 'link_foto', 'nota']
            df_ew = st.data_editor(df_w[cols_w] if not df_w.empty else pd.DataFrame(columns=cols_w), num_rows="dynamic", use_container_width=True, hide_index=True, column_config=w_cfg)
            if st.form_submit_button("✨ SALVA"):
                supabase.table("arredamento").delete().eq("stanza", "Wishlist").execute()
                for _, r in df_ew.iterrows():
                    if r['articolo']:
                        supabase.table("arredamento").insert({"stanza": "Wishlist", "articolo": str(r['articolo']), "importo_totale": float(r.get('importo_totale', 0) or 0), "link_fattura": str(r.get('link_fattura', '') or ''), "link_foto": str(r.get('link_foto', '') or ''), "nota": str(r.get('nota', '') or ''), "stanza_chiusa": False}).execute()
                st.rerun()
