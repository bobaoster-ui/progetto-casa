import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import io
import time

# --- REGOLE DELLA PROPRIETÀ ---
# La parola "Proprietà" si scrive con la "à" accentata.

# 1. INIZIALIZZAZIONE (Fix Errore Immagine 1)
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
if "password_correct" not in st.session_state: st.session_state.password_correct = False
if "budget_target" not in st.session_state: st.session_state.budget_target = 15000.0

if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V22.9.25", layout="wide", page_icon="🚀")

# --- MOTORE PDF (Anti-Sovrapposizione e Fix Download) ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182); self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        t = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, t.encode('latin-1','replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

    def add_item_row(self, data, w):
        self.set_font('Arial', '', 9); self.set_text_color(0, 0, 0)
        lines = [len(self.multi_cell(w[i], 8, str(txt), split_only=True)) for i, txt in enumerate(data)]
        h = max(lines) * 8
        if h < 10: h = 10
        if self.get_y() + h > 270: self.add_page()
        curr_x, curr_y = self.get_x(), self.get_y()
        for i, txt in enumerate(data):
            self.set_xy(curr_x + sum(w[:i]), curr_y)
            self.multi_cell(w[i], h, str(txt).encode('latin-1','replace').decode('latin-1'), border=1, align='L' if i < 2 else 'R')
        self.set_y(curr_y + h)

def clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    cols = ['Articolo', 'Acquistato', 'Costo', 'Importo Totale', 'Acquista S/N', 'Note',
            'Prezzo Pieno', 'Sconto %', 'Stato Pagamento', 'Versato', 'Link Fattura',
            'Data Scadenza', 'Link', 'Foto']
    for c in cols:
        if c not in df.columns: df[c] = ""
    for c in ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    if 'Data Scadenza' in df.columns:
        df['Data Scadenza'] = pd.to_datetime(df['Data Scadenza'], errors='coerce')
    return df

# --- UI ---
if not st.session_state.password_correct:
    st.title("🔒 Accesso Sistema")
    u, p = st.text_input("Utente"), st.text_input("Password", type="password")
    if st.button("Entra"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
            st.session_state.password_correct = True; st.rerun()
        else: st.error("Credenziali errate")
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        # LOGO UFFICIALE (Fix logo.png)
        st.image("https://i.ibb.co/Xz9kHHz/logo-jacopo.png", width=180)
        st.session_state.dark_mode = st.toggle("🌙 Modalità Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU PRINCIPALE", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze])
        st.markdown("---")
        st.session_state.budget_target = st.number_input("💰 Budget Obiettivo", value=st.session_state.budget_target, step=500.0)
        edit_struct = st.toggle("⚙️ Modifica Struttura", False)
        st.markdown("---")
        st.markdown(f"✨ **Roberto & Gemini**\n\nProprietà: Jacopo")
        if st.button("Esci 🚪"): st.session_state.password_correct = False; st.rerun()

    if "Riepilogo" in sel:
        st.title("🏠 Command Center")
        all_d = []
        for s in stanze:
            try:
                d = clean_df(conn.read(worksheet=s, ttl="1m"))
                if not d.empty:
                    dc = d[d['Acquista S/N'].str.upper().str.strip() == 'S'].copy()
                    dc['Stanza'] = s.capitalize(); all_d.append(dc)
            except: continue

        if all_d:
            df_r = pd.concat(all_d)
            conf, pag = df_r['Importo Totale'].sum(), df_r['Versato'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("TOTALE IMPEGNATO", f"{conf:,.2f} €")
            c2.metric("TOTALE PAGATO", f"{pag:,.2f} €")
            c3.metric("RESIDUO DA PAGARE", f"{conf-pag:,.2f} €")

            col_sx, col_dx = st.columns([1, 1.2])
            with col_sx:
                st.plotly_chart(px.pie(df_r, values='Importo Totale', names='Stanza', hole=0.4, title="Spesa/Stanza"), use_container_width=True)

            with col_dx:
                # RIPRISTINO SCADENZIARIO (Fix Immagine 10)
                st.subheader("🗓️ Scadenzario Pagamenti")
                scad = df_r[df_r['Data Scadenza'].notna() & (df_r['Versato'] < df_r['Importo Totale'])].copy()
                if not scad.empty:
                    scad = scad.sort_values('Data Scadenza')
                    st.dataframe(scad[['Stanza','Articolo','Data Scadenza']], use_container_width=True, hide_index=True)
                else:
                    st.info("✅ Nessun pagamento in scadenza trovato.")

            st.subheader("🛒 Lista Dettagliata Acquisti")
            st.dataframe(df_r[['Stanza', 'Articolo', 'Importo Totale', 'Versato', 'Stato Pagamento']], use_container_width=True, hide_index=True)

            if st.button("📄 Esporta Report PDF"):
                pdf = PDF(); pdf.add_page(); w = [30, 90, 35, 35]
                pdf.set_fill_color(46, 117, 182); pdf.set_text_color(255, 255, 255); pdf.set_font('Arial', 'B', 10)
                pdf.cell(w[0], 10, 'Stanza', 1, 0, 'C', 1); pdf.cell(w[1], 10, 'Articolo', 1, 0, 'C', 1)
                pdf.cell(w[2], 10, 'Totale', 1, 0, 'C', 1); pdf.cell(w[3], 10, 'Versato', 1, 1, 'C', 1)
                for _, r in df_r.iterrows():
                    pdf.add_item_row([r['Stanza'], r['Articolo'], f"{r['Importo Totale']:.2f}", f"{r['Versato']:.2f}"], w)

                output_pdf = pdf.output(dest='S').encode('latin-1')
                st.download_button("📥 Scarica Report PDF", output_pdf, "Report_Jacopo.pdf", "application/pdf")
        else:
            st.warning("Nessun acquisto confermato trovato.")

    else:
        sn = "desideri" if "Wishlist" in sel else sel.replace("📦 ", "").lower()
        st.title(f"{sel}")
        try:
            df = clean_df(conn.read(worksheet=sn, ttl="0"))
            with st.form(f"form_{sn}"):
                cfg = {
                    "Link": st.column_config.LinkColumn("Sito"),
                    "Foto": st.column_config.LinkColumn("📸 Foto"),
                    "Acquista S/N": st.column_config.SelectboxColumn("Acquista", options=["S", "N"]),
                    "Stato Pagamento": st.column_config.SelectboxColumn("Stato", options=["", "Acconto", "Saldato", "Preventivo"]),
                    "Data Scadenza": st.column_config.DateColumn("Scadenza")
                }
                df_e = st.data_editor(df, use_container_width=True, hide_index=True, column_config=cfg, num_rows="dynamic" if edit_struct else "fixed")
                if st.form_submit_button("💾 SALVA"):
                    for i, r in df_e.iterrows():
                        p_p, sco = float(r.get('Prezzo Pieno',0)), float(r.get('Sconto %',0))
                        c_u = p_p * (1 - (sco/100)) if p_p > 0 else float(r.get('Costo',0))
                        df_e.at[i, 'Costo'], df_e.at[i, 'Importo Totale'] = c_u, c_u * float(r.get('Acquistato',1))
                        if str(r.get('Stato Pagamento', "")).strip() == "Saldato": df_e.at[i, 'Versato'] = df_e.at[i, 'Importo Totale']
                    conn.update(worksheet=sn, data=df_e.fillna(''))
                    st.cache_data.clear(); st.success("✅ Modifiche salvate!"); time.sleep(1); st.rerun()
        except Exception as e: st.error(f"Errore connessione: {e}")
