import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

# --- SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V36.0", layout="wide", page_icon="💎")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_connection()

# --- CLASSE PDF RINFORZATA (NO SOVRAPPOSIZIONI) ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, f'Proprieta: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}', ln=True, align='C')
        self.ln(20)

    def row_tabella(self, stanza, articolo, totale, versato):
        # Calcolo altezza basato sul testo più lungo (articolo)
        self.set_font('Arial', '', 9)
        larghezza_art = 90
        # multi_cell split_only restituisce la lista di righe che verrebbero create
        linee = self.multi_cell(larghezza_art, 7, str(articolo), split_only=True)
        h_riga = len(linee) * 7
        if h_riga < 10: h_riga = 10

        # Disegno celle con XY per evitare sovrapposizioni (Fix immagine 7)
        x, y = self.get_x(), self.get_y()
        self.rect(x, y, 30, h_riga)
        self.cell(30, h_riga, str(stanza), border=0)

        self.set_xy(x + 30, y)
        self.multi_cell(larghezza_art, 7, str(articolo), border=1)

        self.set_xy(x + 120, y)
        self.cell(35, h_riga, f"{totale:,.2f} ", border=1, align='R')

        self.set_xy(x + 155, y)
        self.cell(35, h_riga, f"{versato:,.2f} ", border=1, align='R', ln=True)

# --- STATO SESSIONE ---
if "password_correct" not in st.session_state: st.session_state.password_correct = False
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False

# --- LOGIN ---
if not st.session_state.password_correct:
    st.title("🔒 Accesso")
    u = st.text_input("Utente")
    p = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
            st.session_state.password_correct = True; st.rerun()
else:
    stanze_fisiche = ["Camera", "Cucina", "Salotto", "Tavolo", "Lavori"]

    with st.sidebar:
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

    # Scarico dati una volta sola
    data_res = supabase.table("arredamento").select("*").execute()
    df_all = pd.DataFrame(data_res.data)

    if "Riepilogo" in sel:
        st.title("🏠 Command Center")
        df_real = df_all[df_all['stanza'].isin(stanze_fisiche)] if not df_all.empty else pd.DataFrame()

        if not df_real.empty:
            conf, pag = df_real['importo_totale'].sum(), df_real['versato'].sum()
            st.metric("Totale Impegnato", f"{conf:,.2f} €", f"{conf-new_b:,.2f} € vs Budget")

            # --- PDF FIX (Fix immagine 1, 2, 3, 5, 8, 9) ---
            if st.button("📑 Genera Report PDF"):
                pdf = PDF()
                pdf.add_page()
                # Header Tabella
                pdf.set_fill_color(46, 117, 182); pdf.set_text_color(255, 255, 255); pdf.set_font('Arial', 'B', 10)
                pdf.cell(30, 10, " Stanza", 1, 0, 'L', True)
                pdf.cell(90, 10, " Articolo", 1, 0, 'L', True)
                pdf.cell(35, 10, " Totale", 1, 0, 'C', True)
                pdf.cell(35, 10, " Versato", 1, 1, 'C', True)

                pdf.set_text_color(0, 0, 0)
                for _, r in df_real.iterrows():
                    pdf.row_tabella(r['stanza'], r['articolo'], r['importo_totale'], r['versato'])

                # Download con buffer per evitare 'bytearray' error
                buffer = io.BytesIO()
                pdf_output = pdf.output(dest='S')
                if isinstance(pdf_output, str): pdf_output = pdf_output.encode('latin-1')
                buffer.write(pdf_output)
                st.download_button("📥 Scarica Ora", data=buffer.getvalue(), file_name="Report_Jacopo.pdf", mime="application/pdf")

    elif "Wishlist" in sel:
        st.title("✨ Wishlist")
        df_w = df_all[df_all['stanza'] == "Wishlist"].copy() if not df_all.empty else pd.DataFrame()
        cols_w = ['articolo', 'importo_totale', 'link_fattura', 'link_foto', 'nota']
        df_ew = st.data_editor(df_w[cols_w] if not df_w.empty else pd.DataFrame(columns=cols_w), num_rows="dynamic", use_container_width=True)
        if st.button("💾 Salva Wishlist"):
            supabase.table("arredamento").delete().eq("stanza", "Wishlist").execute()
            for _, r in df_ew.iterrows():
                if r['articolo']:
                    supabase.table("arredamento").insert({"stanza": "Wishlist", "articolo": str(r['articolo']), "importo_totale": float(r.get('importo_totale', 0) or 0), "link_fattura": str(r.get('link_fattura', '')), "link_foto": str(r.get('link_foto', '')), "nota": str(r.get('nota', ''))}).execute()
            st.rerun()

    elif "📦" in sel:
        sn = sel.replace("📦 ", "")
        st.title(f"🏠 {sn}")
        df_s = df_all[df_all['stanza'] == sn].copy() if not df_all.empty else pd.DataFrame()
        # Fix salvataggio record (immagine 11)
        cols = ['articolo', 'acquistato', 'prezzo_pieno', 'sconto_percentuale', 'costo', 'importo_totale', 'versato', 'stato_pagamento', 'nota']
        df_e = st.data_editor(df_s[cols] if not df_s.empty else pd.DataFrame(columns=cols), num_rows="dynamic", use_container_width=True)

        if st.button(f"💾 Salva {sn}"):
            supabase.table("arredamento").delete().eq("stanza", sn).execute()
            for _, r in df_e.iterrows():
                if r['articolo']:
                    p_p = float(r.get('prezzo_pieno', 0) or 0)
                    sc = float(r.get('sconto_percentuale', 0) or 0)
                    qta = float(r.get('acquistato', 1) or 1)
                    c_u = p_p * (1 - (sc/100)) if p_p > 0 else float(r.get('costo', 0) or 0)
                    # Payload pulito per Supabase
                    supabase.table("arredamento").insert({
                        "stanza": sn,
                        "articolo": str(r['articolo']),
                        "acquistato": qta,
                        "prezzo_pieno": p_p,
                        "sconto_percentuale": sc,
                        "costo": c_u,
                        "importo_totale": c_u * qta,
                        "versato": float(r.get('versato', 0) or 0),
                        "nota": str(r.get('nota', '') or ''),
                        "stato_pagamento": str(r.get('stato_pagamento', 'Vuoto'))
                    }).execute()
            st.success("Dati Salvati!"); st.rerun()
