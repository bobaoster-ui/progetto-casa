import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# --- 1. SICUREZZA E LICENZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

# --- 2. CONFIGURAZIONE PAGINA ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
st.set_page_config(page_title="Monitoraggio Arredamento V20.4", layout="wide", page_icon="🚀")

# Stili CSS
bc, cc, tc = ("#0e1117", "#1d2129", "#ffffff") if st.session_state.dark_mode else ("#f8f9fc", "#ffffff", "#1f2937")
grad = "linear-gradient(90deg, #0f2027, #2c5364)" if st.session_state.dark_mode else "linear-gradient(90deg, #2e5a88, #4a90e2)"
st.markdown(f"<style>.stApp {{background-color: {bc}; color: {tc};}} .main-header {{background: {grad}; padding: 30px; border-radius: 15px; color: white; margin-bottom: 25px;}} .metric-card {{background-color: {cc}; padding: 20px; border-radius: 12px; border-bottom: 5px solid #2e5a88; text-align: center; color: {tc};}} .metric-value {{font-size: 1.8em; font-weight: 800; color: #2e5a88;}}</style>", unsafe_allow_html=True)

# Classe PDF (Ripristinata integrale)
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182); self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        testo = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C'); self.ln(15)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(128, 128, 128)
        self.cell(0, 10, "Prodotto di Proprietà: Roberto & Gemini".encode('latin-1', 'replace').decode('latin-1'), 0, 0, 'C')

def safe_clean(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    df['DV'] = df['Articolo'] if 'Articolo' in df.columns else df.get('Oggetto', 'N/A')
    for c in ['Note', 'Acquista S/N', 'S/N', 'Stato Pagamento', 'Stato', 'Link Fattura', 'Link', 'Foto']:
        if c in df.columns: df[c] = df[c].astype(str).replace(['None', 'nan', '<NA>', 'null', ''], '')
    for c in ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    if 'Data Scadenza' in df.columns:
        df['Data Scadenza'] = pd.to_datetime(df['Data Scadenza'], errors='coerce')
        df.loc[df['Data Scadenza'].dt.year < 1950, 'Data Scadenza'] = pd.NaT
    return df

# --- 3. ACCESSO ---
if "password_correct" not in st.session_state:
    st.title("🔒 Accesso Riservato")
    u, p = st.text_input("Utente"), st.text_input("Password", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
            st.session_state.password_correct = True; st.rerun()
        else: st.error("Credenziali errate")
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: pass
        st.session_state.dark_mode = st.toggle("🌙 Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU", ["🏠 Riepilogo Generale", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze])
        edit_mode = st.toggle("⚙️ Modifica Struttura", False)
        st.markdown("<br>---<br><small>Proprietà: Jacopo</small>", unsafe_allow_html=True)
        if st.button("Logout 🚪"): st.session_state.clear(); st.rerun()

    if "Riepilogo" in sel:
        st.markdown('<div class="main-header"><h1>Command Center Arredamento</h1><p>Proprietà: Jacopo</p></div>', unsafe_allow_html=True)
        try: bud = pd.to_numeric(conn.read(worksheet="Impostazioni").iloc[0,1], errors='coerce')
        except: bud = 15000.0
        all_d = []
        for s in stanze:
            d = safe_clean(conn.read(worksheet=s, ttl="1m"))
            if not d.empty:
                cs = 'Acquista S/N' if 'Acquista S/N' in d.columns else 'S/N'
                dc = d[d[cs].str.upper() == 'S'].copy(); dc['Stanza'] = s.capitalize(); all_d.append(dc)
        if all_d:
            df = pd.concat(all_d); conf, pag = df['Importo Totale'].sum(), df['Versato'].sum()
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="metric-card">BUDGET<div class="metric-value">{bud:,.0f}€</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card">CONFERMATO<div class="metric-value">{conf:,.0f}€</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card">PAGATO<div class="metric-value">{pag:,.0f}€</div></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-card">DISPONIBILE<div class="metric-value">{bud-conf:,.0f}€</div></div>', unsafe_allow_html=True)

            st.subheader("🗓️ Scadenze")
            sc = df[df['Data Scadenza'].notna() & (df['Versato'] < df['Importo Totale'])].copy()
            if not sc.empty:
                sc['gg'] = (sc['Data Scadenza'] - pd.Timestamp(datetime.now().date())).dt.days
                sc['Alert'] = sc['gg'].apply(lambda x: "🔴 SCADUTO" if x < 0 else ("🟠 IMMINENTE" if x <= 7 else "🟢 OK"))
                st.dataframe(sc.sort_values('gg')[['Stanza','DV','Data Scadenza','Alert']], use_container_width=True, hide_index=True)

            col1, col2 = st.columns([1, 1.5])
            with col1:
                st.plotly_chart(px.pie(df, values='Importo Totale', names='Stanza', hole=0.5), use_container_width=True)
                if st.button("📄 Genera Report PDF"):
                    pdf = PDF(); pdf.add_page(); pdf.set_font('Arial','B',10); pdf.set_fill_color(46, 117, 182); pdf.set_text_color(255, 255, 255)
                    pdf.cell(30, 10, 'Stanza', 1); pdf.cell(90, 10, 'Articolo', 1); pdf.cell(35, 10, 'Totale', 1); pdf.cell(35, 10, 'Versato', 1, 1)
                    pdf.set_font('Arial','',9); pdf.set_text_color(0,0,0)
                    for _, r in df.iterrows():
                        y = pdf.get_y(); pdf.set_xy(40,y); pdf.multi_cell(90, 10, str(r['DV']).encode('latin-1','replace').decode('latin-1'), 1); h = max(pdf.get_y()-y, 10)
                        pdf.set_xy(10,y); pdf.cell(30,h,str(r['Stanza']),1); pdf.set_xy(130,y); pdf.cell(35,h,f"{r['Importo Totale']:,.2f}",1); pdf.cell(35,h,f"{r['Versato']:,.2f}",1,1)
                    pdf.set_font('Arial','B',10); pdf.cell(120, 10, 'TOTALI GENERALI', 1, 0, 'R'); pdf.cell(35, 10, f"{conf:,.2f}", 1, 0, 'R'); pdf.cell(35, 10, f"{pag:,.2f}", 1, 1, 'R')
                    st.download_button("📥 Scarica PDF", bytes(pdf.output(dest='S')), "Report.pdf")
            with col2: st.dataframe(df[['Stanza','DV','Importo Totale','Versato']], use_container_width=True, hide_index=True)

    elif "📦" in sel:
        sn = sel.replace("📦 ", "").lower(); st.title(f"🏠 {sn.capitalize()}")
        df = safe_clean(conn.read(worksheet=sn, ttl="0")) # Cache 0 per evitare vecchi dati
        c_sn = 'Acquista S/N' if 'Acquista S/N' in df.columns else 'S/N'
        c_st = 'Stato Pagamento' if 'Stato Pagamento' in df.columns else 'Stato'

        with st.expander("📝 EDITOR NOTE AVANZATO"):
            art = st.selectbox("Seleziona Articolo:", df['DV'].tolist())
            idx_list = df[df['DV'] == art].index.tolist()
            if idx_list:
                idx = idx_list[0]
                nt = st.text_area("Nota dettagliata:", value=df.at[idx, 'Note'], height=150)
                if st.button("Aggiorna Nota Temporaneamente"):
                    df.at[idx, 'Note'] = nt
                    st.success("Nota aggiornata nel dataframe! Ora clicca SALVA TUTTO sotto.")

        with st.form(f"f_{sn}"):
            config = {
                c_sn: st.column_config.SelectboxColumn(c_sn, options=["S", "N"]),
                c_st: st.column_config.SelectboxColumn(c_st, options=["", "Acconto", "Saldato", "Preventivo"]),
                "Data Scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"),
                "Link Fattura": st.column_config.LinkColumn("📂 Doc", display_text="Apri")
            }
            # Visualizziamo solo le colonne originali per il salvataggio
            df_e = st.data_editor(df.drop(columns=['DV']), use_container_width=True, hide_index=True, num_rows="dynamic" if edit_mode else "fixed", column_config=config)
            if st.form_submit_button("💾 SALVA TUTTO"):
                with st.spinner("Salvataggio in corso..."):
                    for i in range(len(df_e)):
                        r = df_e.iloc[i]; p, s, q = float(r.get('Prezzo Pieno',0)), float(r.get('Sconto %',0)), float(r.get('Acquistato',1))
                        costo = p * (1-(s/100)) if p>0 else float(r.get('Costo',0))
                        df_e.at[df_e.index[i],'Costo'] = costo; df_e.at[df_e.index[i],'Importo Totale'] = costo*q
                        if "Saldato" in str(r.get(c_st,'')): df_e.at[df_e.index[i],'Versato'] = costo*q
                    conn.update(worksheet=sn, data=df_e.fillna(''))
                    st.cache_data.clear() # Pulizia cache profonda
                    st.success("Dati salvati con successo su Google Sheets!")
                    st.balloons()
                    time.sleep(1.5) # Pausa per permettere a Sheets di aggiornarsi
                    st.rerun()

    elif "✨" in sel:
        st.title("✨ Wishlist"); dfw = safe_clean(conn.read(worksheet="desideri", ttl="0"))
        w_config = {"Link": st.column_config.LinkColumn("🔗 Web", display_text="Apri Sito"), "Foto": st.column_config.LinkColumn("📸 Foto", display_text="Vedi Foto")}
        dfew = st.data_editor(dfw.drop(columns=['DV']), use_container_width=True, hide_index=True, column_config=w_config, num_rows="dynamic" if edit_mode else "fixed")
        if st.button("Salva Wishlist"):
            conn.update(worksheet="desideri", data=dfew.fillna('')); st.cache_data.clear(); st.success("Wishlist salvata!"); st.balloons(); time.sleep(1); st.rerun()
