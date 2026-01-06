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

st.set_page_config(page_title="Monitoraggio Arredamento V22.9.18", layout="wide", page_icon="🚀")

# --- INIZIALIZZAZIONE SESSIONE ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
if "password_correct" not in st.session_state: st.session_state.password_correct = False

# --- MOTORE PDF (Anti-Scalino e Fix Formattazione) ---
class PDF(FPDF):
    def header(self):
        # Header blu professionale
        self.set_fill_color(46, 117, 182); self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        t = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, t.encode('latin-1','replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

    def draw_table_row(self, data, w):
        self.set_font('Arial', '', 9)
        # Calcolo dinamico altezza (Fix Scalini Immagine 10)
        txt_heights = [len(self.multi_cell(w[i], 8, str(txt), split_only=True)) for i, txt in enumerate(data)]
        h = max(txt_heights) * 8
        if h < 10: h = 10

        if self.get_y() + h > 270: self.add_page()

        x_start, y_start = self.get_x(), self.get_y()
        for i, txt in enumerate(data):
            self.set_xy(x_start + sum(w[:i]), y_start)
            clean_text = str(txt).encode('latin-1','replace').decode('latin-1')
            # Disegna la cella con altezza uniforme per tutta la riga
            self.multi_cell(w[i], h, clean_text, border=1, align='L' if i < 2 else 'R')
        self.set_y(y_start + h)

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
    u, p = st.text_input("Utente"), st.text_input("Password", type="password")
    if st.button("Entra"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
            st.session_state.password_correct = True; st.rerun()
        else: st.error("Credenziali errate")
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        # LOGO ORIGINALE RIPRISTINATO (Dall'immagine 2)
        st.markdown("""
            <div style="text-align: center; background: white; padding: 15px; border-radius: 15px; border: 1px solid #e0e0e0;">
                <img src="https://i.ibb.co/v4mKHzR/logo-casa.png" width="80" style="margin-bottom: 10px;">
                <h3 style="margin:0; color:#2e75b6; font-size:16px;">Monitoraggio Arredamento</h3>
                <p style="margin:0; color:#666; font-size:12px;">Jacopo</p>
            </div>
        """, unsafe_allow_html=True)

        st.session_state.dark_mode = st.toggle("🌙 Modalità Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze])
        edit_struct = st.toggle("⚙️ Modifica Struttura", False)
        st.markdown("<br>---<br>✨ **Roberto & Gemini**<br><small>Proprietà: Jacopo</small>", unsafe_allow_html=True)
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

            # Grafici e Scadenzario
            col_chart, col_scad = st.columns([1, 1.2])
            with col_chart:
                st.plotly_chart(px.pie(df_r, values='Importo Totale', names='Stanza', hole=0.4, title="Spesa per Stanza"), use_container_width=True)
            with col_scad:
                st.subheader("🗓️ Scadenzario")
                scad = df_r[df_r['Data Scadenza'].notna() & (df_r['Versato'] < df_r['Importo Totale'])].copy()
                if not scad.empty:
                    scad['Giorni'] = (scad['Data Scadenza'] - pd.Timestamp(datetime.now().date())).dt.days
                    scad['Stato'] = scad['Giorni'].apply(lambda x: "🔴 SCADUTO" if x < 0 else ("🟠 IMMINENTE" if x <= 7 else "🟢 OK"))
                    st.dataframe(scad.sort_values('Giorni')[['Stanza','Articolo','Data Scadenza','Stato']], use_container_width=True, hide_index=True)
                else: st.info("Nessuna scadenza.")

            # LISTA ACQUISTI (Ripristinata dall'Immagine 9)
            st.subheader("🛒 Lista Articoli Confermati")
            st.dataframe(df_r[['Stanza', 'Articolo', 'Importo Totale', 'Versato', 'Stato Pagamento']], use_container_width=True, hide_index=True)

            # --- GENERAZIONE PDF (Fix Bytearray e Scalini) ---
            if st.button("📄 Genera Report PDF"):
                pdf = PDF(); pdf.add_page(); w = [30, 90, 35, 35]
                pdf.set_fill_color(46,117,182); pdf.set_text_color(255,255,255); pdf.set_font('Arial','B',10)
                pdf.cell(w[0],10,'Stanza',1,0,'C',1); pdf.cell(w[1],10,'Articolo',1,0,'C',1)
                pdf.cell(w[2],10,'Totale',1,0,'C',1); pdf.cell(w[3],10,'Versato',1,1,'C',1)
                for _, r in df_r.iterrows():
                    pdf.draw_table_row([r['Stanza'], r['Articolo'], f"{r['Importo Totale']:.2f}", f"{r['Versato']:.2f}"], w)

                # Conversione sicura in bytes per evitare errori Streamlit
                try:
                    out = pdf.output(dest='S')
                    final_pdf = out.encode('latin-1') if isinstance(out, str) else bytes(out)
                    st.download_button("📥 Scarica Report PDF", final_pdf, "Report_Proprietà_Jacopo.pdf", "application/pdf")
                except Exception as e:
                    st.error(f"Errore creazione download: {e}")

    else:
        # Gestione Stanze Singole
        sn = "desideri" if "Wishlist" in sel else sel.replace("📦 ", "").lower()
        st.title(f"{sel}")
        try:
            df = clean_df(conn.read(worksheet=sn, ttl="0"))
            with st.form(f"form_{sn}"):
                cfg = {
                    "Acquista S/N": st.column_config.SelectboxColumn("Acquista", options=["S", "N"]),
                    "Stato Pagamento": st.column_config.SelectboxColumn("Stato", options=["", "Acconto", "Saldato", "Preventivo"]),
                    "Data Scadenza": st.column_config.DateColumn("Scadenza"),
                    "Link Fattura": st.column_config.LinkColumn("Doc"),
                    "Link": st.column_config.LinkColumn("Sito"),
                    "Foto": st.column_config.LinkColumn("Foto"),
                    "Importo Totale": st.column_config.NumberColumn("Totale (€)", disabled=True)
                }
                df_e = st.data_editor(df, use_container_width=True, hide_index=True, column_config=cfg, num_rows="dynamic" if edit_struct else "fixed")
                if st.form_submit_button("💾 SALVA MODIFICHE"):
                    for i, r in df_e.iterrows():
                        p_p, sco, qta = float(r.get('Prezzo Pieno',0)), float(r.get('Sconto %',0)), float(r.get('Acquistato',1))
                        c_u = p_p * (1 - (sco/100)) if p_p > 0 else float(r.get('Costo',0))
                        df_e.at[i, 'Costo'], df_e.at[i, 'Importo Totale'] = c_u, c_u * qta
                        if str(r.get('Stato Pagamento', "")).strip() == "Saldato":
                            df_e.at[i, 'Versato'] = df_e.at[i, 'Importo Totale']
                            df_e.at[i, 'Data Scadenza'] = pd.NaT
                    conn.update(worksheet=sn, data=df_e.fillna(''))
                    st.cache_data.clear(); st.success("✅ Salvataggio completato!"); time.sleep(1); st.rerun()
        except: st.error("Errore di connessione a Google Sheets.")
