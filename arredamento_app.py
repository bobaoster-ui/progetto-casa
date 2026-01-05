import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

# --- REGOLE DELLA PROPRIETÀ ---
# La parola "Proprietà" si scrive con la "à" accentata.

if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V37.0", layout="wide", page_icon="💎")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_connection()

# --- PDF ENGINE (FIX SOVRAPPOSIZIONI) ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        # Usiamo 'Proprieta' senza accento solo nel PDF per evitare crash Unicode fatali
        self.cell(0, 10, f'Proprieta: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}', ln=True, align='C')
        self.ln(20)

    def aggiungi_riga(self, dati, widths):
        # Calcolo preventivo dell'altezza riga basato sulle celle multiline
        altezze = []
        for i, testo in enumerate(dati):
            linee = self.multi_cell(widths[i], 8, str(testo), split_only=True)
            altezze.append(len(linee) * 8)
        h_max = max(altezze) if altezze else 10

        # Disegno delle celle con posizionamento assoluto per evitare sovrapposizioni
        x_curr, y_curr = self.get_x(), self.get_y()
        for i, testo in enumerate(dati):
            self.set_xy(x_curr, y_curr)
            self.multi_cell(widths[i], h_max, str(testo), border=1, align='L' if i < 2 else 'R')
            x_curr += widths[i]
        self.ln(h_max)

# --- SETUP STATO ---
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

        # Budget Persistente
        res_b = supabase.table("arredamento").select("importo_totale").eq("stanza", "Impostazioni").eq("articolo", "Budget_Totale").execute()
        curr_b = res_b.data[0]['importo_totale'] if res_b.data else 15000.0
        new_b = st.number_input("Budget Obiettivo (€)", value=float(curr_b), step=500.0)
        if new_b != curr_b:
            supabase.table("arredamento").delete().eq("stanza", "Impostazioni").eq("articolo", "Budget_Totale").execute()
            supabase.table("arredamento").insert({"stanza": "Impostazioni", "articolo": "Budget_Totale", "importo_totale": new_b}).execute()
            st.rerun()

        st.markdown(f"<br><br><small>Proprietà: Jacopo</small>", unsafe_allow_html=True)
        if st.button("Logout 🚪"): st.session_state.clear(); st.rerun()

    # Caricamento dati
    res_all = supabase.table("arredamento").select("*").execute()
    df_all = pd.DataFrame(res_all.data)

    if "Riepilogo" in sel:
        st.title("🏠 Command Center")
        df_real = df_all[df_all['stanza'].isin(stanze_fisiche)] if not df_all.empty else pd.DataFrame()
        if not df_real.empty:
            tot_imp = df_real['importo_totale'].sum()
            tot_pag = df_real['versato'].sum()
            st.metric("Totale Impegnato", f"{tot_imp:,.2f} €", f"{tot_imp - new_b:,.2f} € vs Budget")

            if st.button("📑 Genera Report PDF"):
                pdf = PDF()
                pdf.add_page()
                w = [30, 90, 35, 35]
                # Header Tabella
                pdf.set_fill_color(46, 117, 182); pdf.set_text_color(255, 255, 255); pdf.set_font('Arial', 'B', 10)
                pdf.cell(w[0], 10, " Stanza", 1, 0, 'L', True)
                pdf.cell(w[1], 10, " Articolo", 1, 0, 'L', True)
                pdf.cell(w[2], 10, " Totale", 1, 0, 'C', True)
                pdf.cell(w[3], 10, " Versato", 1, 1, 'C', True)

                pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 9)
                for _, r in df_real.iterrows():
                    art_puro = str(r['articolo']).encode('latin-1', 'replace').decode('latin-1')
                    pdf.aggiungi_riga([r['stanza'], art_puro, f"{r['importo_totale']:,.2f}", f"{r['versato']:,.2f}"], w)

                # Buffer binario per evitare errore 'bytearray'
                buf = io.BytesIO()
                buf.write(pdf.output(dest='S').encode('latin-1') if isinstance(pdf.output(dest='S'), str) else pdf.output(dest='S'))
                st.download_button("📥 Scarica PDF", data=buf.getvalue(), file_name="Report_Arredamento.pdf", mime="application/pdf")

    elif "Wishlist" in sel:
        st.title("✨ Wishlist")
        df_w = df_all[df_all['stanza'] == "Wishlist"].copy() if not df_all.empty else pd.DataFrame(columns=['articolo', 'importo_totale', 'nota'])
        df_ew = st.data_editor(df_w[['articolo', 'importo_totale', 'nota']], num_rows="dynamic", use_container_width=True)
        if st.button("💾 Salva Wishlist"):
            supabase.table("arredamento").delete().eq("stanza", "Wishlist").execute()
            for _, r in df_ew.iterrows():
                if r['articolo']:
                    supabase.table("arredamento").insert({"stanza": "Wishlist", "articolo": str(r['articolo']), "importo_totale": float(r.get('importo_totale', 0) or 0), "nota": str(r.get('nota', ''))}).execute()
            st.rerun()

    elif "📦" in sel:
        sn = sel.replace("📦 ", "")
        st.title(f"🏠 {sn}")
        df_s = df_all[df_all['stanza'] == sn].copy() if not df_all.empty else pd.DataFrame(columns=['articolo', 'importo_totale', 'versato', 'nota'])
        df_e = st.data_editor(df_s[['articolo', 'importo_totale', 'versato', 'nota']], num_rows="dynamic", use_container_width=True)
        if st.button(f"💾 Salva {sn}"):
            supabase.table("arredamento").delete().eq("stanza", sn).execute()
            for _, r in df_e.iterrows():
                if r['articolo']:
                    supabase.table("arredamento").insert({
                        "stanza": sn, "articolo": str(r['articolo']),
                        "importo_totale": float(r.get('importo_totale', 0) or 0),
                        "versato": float(r.get('versato', 0) or 0),
                        "nota": str(r.get('nota', ''))
                    }).execute()
            st.rerun()
