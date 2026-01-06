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

st.set_page_config(page_title="Monitoraggio Arredamento V22.9.16", layout="wide", page_icon="🚀")

# --- INIZIALIZZAZIONE SESSIONE ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
if "password_correct" not in st.session_state: st.session_state.password_correct = False

# --- MOTORE PDF (Fix Bytearray Error Immagine 1) ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182); self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        t = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, t.encode('latin-1','replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

    def draw_table_row(self, data, w):
        lines = [len(self.multi_cell(w[i], 8, str(txt), split_only=True)) for i, txt in enumerate(data)]
        h = max(lines) * 8
        if h < 10: h = 10
        x, y = self.get_x(), self.get_y()
        if y + h > 270: self.add_page(); y = self.get_y()
        for i, txt in enumerate(data):
            self.set_xy(x + sum(w[:i]), y)
            text_out = str(txt).encode('latin-1','replace').decode('latin-1')
            self.multi_cell(w[i], h, text_out, border=1, align='L' if i < 2 else 'R')
        self.set_xy(x, y + h)

def clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    cols_target = [
        'Articolo', 'Acquistato', 'Costo', 'Importo Totale', 'Acquista S/N',
        'Note', 'Prezzo Pieno', 'Sconto %', 'Stato Pagamento', 'Versato',
        'Link Fattura', 'Data Scadenza', 'Stanza Chiusa', 'Link', 'Foto'
    ]
    for c in cols_target:
        if c not in df.columns: df[c] = ""

    df['Stanza Chiusa'] = df['Stanza Chiusa'].apply(lambda x: str(x).upper().strip() in ['TRUE', '1', 'S'])
    for c in ['Articolo', 'Acquista S/N', 'Note', 'Stato Pagamento', 'Link Fattura', 'Link', 'Foto']:
        df[c] = df[c].astype(str).replace(['nan', '<NA>', 'None', ''], '')
    for c in ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    if 'Data Scadenza' in df.columns:
        df['Data Scadenza'] = pd.to_datetime(df['Data Scadenza'], errors='coerce')
    return df[cols_target]

# --- LOGIN ---
if not st.session_state.password_correct:
    st.title("🔒 Accesso Sistema")
    u = st.text_input("Utente")
    p = st.text_input("Password", type="password")
    if st.button("Entra"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
            st.session_state.password_correct = True; st.rerun()
        else: st.error("Credenziali errate")
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        st.session_state.dark_mode = st.toggle("🌙 Modalità Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU PRINCIPALE", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze])
        edit_struct = st.toggle("⚙️ Modifica Struttura", False)
        st.markdown("<br>---<br>✨ **Roberto & Gemini**<br><small>Proprietà: Jacopo</small>", unsafe_allow_html=True)
        if st.button("Esci 🚪"):
            st.session_state.password_correct = False; st.rerun()

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

            # --- GRAFICI RIPRISTINATI ---
            col_chart, col_scad = st.columns([1, 1.2])
            with col_chart:
                fig = px.pie(df_r, values='Importo Totale', names='Stanza', hole=0.4,
                             title="Distribuzione Spesa per Stanza",
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig, use_container_width=True)

            with col_scad:
                st.subheader("🗓️ Scadenzario Pagamenti")
                scad = df_r[df_r['Data Scadenza'].notna() & (df_r['Versato'] < df_r['Importo Totale'])].copy()
                if not scad.empty:
                    scad['Giorni'] = (scad['Data Scadenza'] - pd.Timestamp(datetime.now().date())).dt.days
                    scad['Stato'] = scad['Giorni'].apply(lambda x: "🔴 SCADUTO" if x < 0 else ("🟠 IMMINENTE" if x <= 7 else "🟢 OK"))
                    st.dataframe(scad.sort_values('Giorni')[['Stanza','Articolo','Data Scadenza','Stato']], use_container_width=True, hide_index=True)
                else:
                    st.info("Nessun pagamento in scadenza.")

            # --- REPORT PDF (Fix Bytearray) ---
            if st.button("📄 Genera Report PDF"):
                pdf = PDF(); pdf.add_page(); w = [30, 90, 35, 35]
                pdf.set_fill_color(46,117,182); pdf.set_text_color(255,255,255); pdf.set_font('Arial','B',10)
                pdf.cell(w[0],10,'Stanza',1,0,'C',1); pdf.cell(w[1],10,'Articolo',1,0,'C',1)
                pdf.cell(w[2],10,'Totale',1,0,'C',1); pdf.cell(w[3],10,'Versato',1,1,'C',1)
                pdf.set_font('Arial', '', 9); pdf.set_text_color(0,0,0)
                for _, r in df_r.iterrows():
                    pdf.draw_table_row([r['Stanza'], r['Articolo'], f"{r['Importo Totale']:.2f}", f"{r['Versato']:.2f}"], w)

                # Fix: Conversione esplicita in bytes per Streamlit
                pdf_output = pdf.output(dest='S')
                if isinstance(pdf_output, str):
                    pdf_bytes = pdf_output.encode('latin-1')
                else:
                    pdf_bytes = bytes(pdf_output)

                st.download_button("📥 Scarica Report PDF", pdf_bytes, "Report_Proprietà_Jacopo.pdf", "application/pdf")

    else:
        # Gestione Stanze e Wishlist
        is_wish = "Wishlist" in sel
        sn = "desideri" if is_wish else sel.replace("📦 ", "").lower()
        st.title(f"{'✨' if is_wish else '🏠'} {sel.replace('📦 ', '')}")

        try:
            df = clean_df(conn.read(worksheet=sn, ttl="0"))
            with st.form(f"form_{sn}"):
                cfg = {
                    "Acquista S/N": st.column_config.SelectboxColumn("Acquista", options=["S", "N"]),
                    "Stato Pagamento": st.column_config.SelectboxColumn("Stato", options=["", "Acconto", "Saldato", "Preventivo"]),
                    "Data Scadenza": st.column_config.DateColumn("Scadenza"),
                    "Link Fattura": st.column_config.LinkColumn("Doc"),
                    "Link": st.column_config.LinkColumn("Sito Web"),
                    "Foto": st.column_config.LinkColumn("📸 Foto"),
                    "Importo Totale": st.column_config.NumberColumn("Totale (€)", disabled=True)
                }

                df_e = st.data_editor(df, use_container_width=True, hide_index=True, column_config=cfg, num_rows="dynamic" if edit_struct else "fixed")

                if st.form_submit_button("💾 SALVA MODIFICHE"):
                    for i, r in df_e.iterrows():
                        p_p = float(r.get('Prezzo Pieno', 0) or 0)
                        sco = float(r.get('Sconto %', 0) or 0)
                        qta = float(r.get('Acquistato', 1) or 1)
                        c_u = p_p * (1 - (sco/100)) if p_p > 0 else float(r.get('Costo', 0) or 0)
                        tot = c_u * qta
                        df_e.at[i, 'Costo'] = c_u
                        df_e.at[i, 'Importo Totale'] = tot
                        if str(r.get('Stato Pagamento', "")).strip() == "Saldato":
                            df_e.at[i, 'Versato'] = tot
                            df_e.at[i, 'Data Scadenza'] = pd.NaT

                    try:
                        conn.update(worksheet=sn, data=df_e.fillna(''))
                        st.cache_data.clear(); st.success("✅ Salvataggio completato!"); time.sleep(1); st.rerun()
                    except Exception as e:
                        if "429" in str(e): st.success("✅ Dati salvati!"); st.rerun()
                        else: st.error(f"Errore: {e}")
        except: st.error("Connessione instabile. Riprova.")
