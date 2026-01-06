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

if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V22.9.20", layout="wide", page_icon="🚀")

# --- INIZIALIZZAZIONE SESSIONE ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
if "password_correct" not in st.session_state: st.session_state.password_correct = False
if "budget_target" not in st.session_state: st.session_state.budget_target = 15000.0

# --- MOTORE PDF (Anti-Scalino & Anti-Vuoto) ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182); self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        t = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, t.encode('latin-1','replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

    def draw_table_header(self, w):
        self.set_fill_color(46, 117, 182); self.set_text_color(255, 255, 255); self.set_font('Arial', 'B', 10)
        cols = ['Stanza', 'Articolo', 'Totale', 'Versato']
        for i, col in enumerate(cols):
            self.cell(w[i], 10, col, 1, 0, 'C', 1)
        self.ln()

    def add_item_row(self, data, w):
        self.set_font('Arial', '', 9); self.set_text_color(0, 0, 0)
        lines = [len(self.multi_cell(w[i], 8, str(txt), split_only=True)) for i, txt in enumerate(data)]
        h = max(lines) * 8
        if self.get_y() + h > 270:
            self.add_page(); self.draw_table_header(w)
        curr_x, curr_y = self.get_x(), self.get_y()
        for i, txt in enumerate(data):
            self.set_xy(curr_x + sum(w[:i]), curr_y)
            clean_txt = str(txt).encode('latin-1','replace').decode('latin-1')
            self.multi_cell(w[i], h, clean_txt, border=1, align='L' if i < 2 else 'R')
        self.set_y(curr_y + h)

def clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    cols_target = ['Articolo', 'Acquistato', 'Costo', 'Importo Totale', 'Acquista S/N', 'Note', 'Prezzo Pieno', 'Sconto %', 'Stato Pagamento', 'Versato', 'Link Fattura', 'Data Scadenza', 'Link', 'Foto']
    for c in cols_target:
        if c not in df.columns: df[c] = ""
    for c in ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    df['Acquista S/N'] = df['Acquista S/N'].astype(str).str.upper().str.strip()
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
        st.image("https://i.ibb.co/v4mKHzR/logo-casa.png", width=100)
        st.markdown("<h3 style='text-align:center;'>Jacopo</h3>", unsafe_allow_html=True)
        st.session_state.dark_mode = st.toggle("🌙 Modalità Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze])
        st.session_state.budget_target = st.number_input("Budget Obiettivo (€)", value=st.session_state.budget_target, step=500.0)
        edit_struct = st.toggle("⚙️ Modifica Struttura", False)
        if st.button("Esci 🚪"): st.session_state.password_correct = False; st.rerun()

    if "Riepilogo" in sel:
        st.title("🏠 Command Center")
        all_d = []
        for s in stanze:
            try:
                d = clean_df(conn.read(worksheet=s, ttl="1m"))
                if not d.empty:
                    dc = d[d['Acquista S/N'] == 'S'].copy()
                    dc['Stanza'] = s.capitalize(); all_d.append(dc)
            except: continue

        if all_d:
            df_r = pd.concat(all_d)
            conf, pag = df_r['Importo Totale'].sum(), df_r['Versato'].sum()
            diff_budget = st.session_state.budget_target - conf

            c1, c2, c3 = st.columns(3)
            c1.metric("TOTALE IMPEGNATO", f"{conf:,.2f} €", f"{diff_budget:,.2f} € vs Budget")
            c2.metric("TOTALE PAGATO", f"{pag:,.2f} €")
            c3.metric("RESIDUO", f"{conf-pag:,.2f} €")

            # --- SEZIONE GRAFICI & SCADENZARIO RIPRISTINATA ---
            col_chart, col_scad = st.columns([1, 1.2])
            with col_chart:
                st.plotly_chart(px.pie(df_r, values='Importo Totale', names='Stanza', hole=0.4, title="Spesa/Stanza"), use_container_width=True)

            with col_scad:
                st.subheader("🗓️ Scadenzario Pagamenti")
                # Fix: Controllo più attento sulle scadenze (Immagine 9)
                scad = df_r[df_r['Data Scadenza'].notna() & (df_r['Versato'] < df_r['Importo Totale'])].copy()
                if not scad.empty:
                    scad['Giorni'] = (scad['Data Scadenza'] - pd.Timestamp(datetime.now().date())).dt.days
                    scad['Stato'] = scad['Giorni'].apply(lambda x: "🔴 SCADUTO" if x < 0 else ("🟠 IMMINENTE" if x <= 7 else "🟢 OK"))
                    st.dataframe(scad.sort_values('Data Scadenza')[['Stanza','Articolo','Data Scadenza','Stato']], use_container_width=True, hide_index=True)
                else:
                    st.info("Tutti i pagamenti confermati sono stati saldati! 🎉")

            st.subheader("🛒 Lista Dettagliata Acquisti")
            st.dataframe(df_r[['Stanza', 'Articolo', 'Importo Totale', 'Versato', 'Stato Pagamento']], use_container_width=True, hide_index=True)

            if st.button("📄 Genera Report PDF"):
                pdf = PDF(); pdf.add_page(); w = [30, 90, 35, 35]
                pdf.draw_table_header(w)
                for _, r in df_r.iterrows():
                    pdf.add_item_row([r['Stanza'], r['Articolo'], f"{r['Importo Totale']:.2f}", f"{r['Versato']:.2f}"], w)

                pdf_output = pdf.output(dest='S')
                final_pdf = pdf_output.encode('latin-1') if isinstance(pdf_output, str) else bytes(pdf_output)
                st.download_button("📥 Scarica Report PDF", final_pdf, "Report_Jacopo.pdf", "application/pdf")
    else:
        # Stanze e Wishlist
        sn = "desideri" if "Wishlist" in sel else sel.replace("📦 ", "").lower()
        st.title(f"{sel}")
        try:
            df = clean_df(conn.read(worksheet=sn, ttl="0"))
            with st.form(f"form_{sn}"):
                df_e = st.data_editor(df, use_container_width=True, hide_index=True, num_rows="dynamic" if edit_struct else "fixed")
                if st.form_submit_button("💾 SALVA"):
                    for i, r in df_e.iterrows():
                        p_p, sco, qta = float(r.get('Prezzo Pieno',0)), float(r.get('Sconto %',0)), float(r.get('Acquistato',1))
                        c_u = p_p * (1 - (sco/100)) if p_p > 0 else float(r.get('Costo',0))
                        df_e.at[i, 'Costo'], df_e.at[i, 'Importo Totale'] = c_u, c_u * qta
                        if str(r.get('Stato Pagamento', "")).strip() == "Saldato":
                            df_e.at[i, 'Versato'] = df_e.at[i, 'Importo Totale']
                    conn.update(worksheet=sn, data=df_e.fillna(''))
                    st.cache_data.clear(); st.success("✅ Modifiche salvate!"); time.sleep(1); st.rerun()
        except Exception as e: st.error(f"Errore: {e}")
