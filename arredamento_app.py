import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# --- SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V21.2", layout="wide", page_icon="🚀")

# --- STILE ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
bc, cc, tc = ("#0e1117", "#1d2129", "#ffffff") if st.session_state.dark_mode else ("#f8f9fc", "#ffffff", "#1f2937")
grad = "linear-gradient(90deg, #0f2027, #203a43, #2c5364)" if st.session_state.dark_mode else "linear-gradient(90deg, #2e5a88, #4a90e2)"
st.markdown(f"""<style>
    .stApp {{background-color: {bc}; color: {tc};}}
    .main-header {{background: {grad}; padding: 30px; border-radius: 15px; color: white; margin-bottom: 25px;}}
    .metric-card {{background-color: {cc}; padding: 15px; border-radius: 10px; border-bottom: 4px solid #2e5a88; text-align: center; color: {tc}; margin-bottom: 10px;}}
    .metric-value-mini {{font-size: 1.4em; font-weight: 700; color: #2e5a88;}}
    .metric-value {{font-size: 1.8em; font-weight: 800; color: #2e5a88;}}
</style>""", unsafe_allow_html=True)

class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10); t = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, t.encode('latin-1','replace').decode('latin-1'), ln=True, align='C'); self.ln(15)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(128, 128, 128)
        self.cell(0, 10, "Prodotto di Proprietà: Roberto & Gemini".encode('latin-1','replace').decode('latin-1'), 0, 0, 'C')

def clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    df['DV'] = df['Articolo'] if 'Articolo' in df.columns else df.get('Oggetto', 'N/A')
    for c in ['Note', 'Acquista S/N', 'S/N', 'Stato Pagamento', 'Stato', 'Link Fattura', 'Link', 'Foto']:
        if c in df.columns: df[c] = df[c].astype(str).replace(['None', 'nan', '<NA>', 'null', ''], '')
    for c in ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    if 'Data Scadenza' in df.columns: df['Data Scadenza'] = pd.to_datetime(df['Data Scadenza'], errors='coerce')
    return df

if "password_correct" not in st.session_state:
    st.title("🔒 Accesso")
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]: st.session_state.password_correct = True; st.rerun()
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: pass
        st.session_state.dark_mode = st.toggle("🌙 Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze])
        edit_struct = st.toggle("⚙️ Modifica Struttura", False)
        st.markdown("<br>---<br>✨ **Roberto & Gemini**<br><small>Proprietà: Jacopo</small>", unsafe_allow_html=True)
        if st.button("Logout 🚪"): st.session_state.clear(); st.rerun()

    if "Riepilogo" in sel:
        st.markdown('<div class="main-header"><h1>Command Center</h1><p>Proprietà: Jacopo</p></div>', unsafe_allow_html=True)
        try: bud = pd.to_numeric(conn.read(worksheet="Impostazioni", ttl="5m").iloc[0,1], errors='coerce')
        except: bud = 15000.0

        all_d = []
        for s in stanze:
            try:
                d = clean_df(conn.read(worksheet=s, ttl="1m"))
                if not d.empty:
                    cs = 'Acquista S/N' if 'Acquista S/N' in d.columns else 'S/N'
                    dc = d[d[cs].str.upper().str.strip() == 'S'].copy(); dc['Stanza'] = s.capitalize(); all_d.append(dc)
            except: continue

        if all_d:
            df_r = pd.concat(all_d); conf, pag = df_r['Importo Totale'].sum(), df_r['Versato'].sum()
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f'<div class="metric-card">BUDGET<div class="metric-value">{bud:,.0f}€</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card">CONFERMATO<div class="metric-value">{conf:,.0f}€</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card">PAGATO<div class="metric-value">{pag:,.0f}€</div></div>', unsafe_allow_html=True)
            m4.markdown(f'<div class="metric-card">DISPONIBILE<div class="metric-value">{bud-conf:,.0f}€</div></div>', unsafe_allow_html=True)

            st.subheader("🗓️ Scadenzario")
            sc = df_r[df_r['Data Scadenza'].notna() & (df_r['Versato'] < df_r['Importo Totale'])].copy()
            if not sc.empty:
                sc['gg'] = (sc['Data Scadenza'] - pd.Timestamp(datetime.now().date())).dt.days
                sc['Stato'] = sc['gg'].apply(lambda x: "🔴 SCADUTO" if x < 0 else ("🟠 IMMINENTE" if x <= 7 else "🟢 OK"))
                sc['Data Scadenza'] = sc['Data Scadenza'].dt.date
                st.dataframe(sc.sort_values('gg')[['Stanza','DV','Data Scadenza','Stato']], use_container_width=True, hide_index=True, column_config={"Data Scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY")})

            c_p, c_t = st.columns([1, 1.2])
            with c_p:
                st.plotly_chart(px.pie(df_r, values='Importo Totale', names='Stanza', hole=0.5), use_container_width=True)
                if st.button("📄 PDF"):
                    p = PDF(); p.add_page(); p.set_font('Arial','B',10); p.set_fill_color(46,117,182); p.set_text_color(255,255,255)
                    p.cell(30,10,'Stanza',1,0,'C',1); p.cell(90,10,'Articolo',1,0,'C',1); p.cell(35,10,'Totale',1,0,'C',1); p.cell(35,10,'Versato',1,1,'C',1)
                    p.set_font('Arial','',9); p.set_text_color(0,0,0)
                    for _, r in df_r.iterrows():
                        y=p.get_y(); p.set_xy(40,y); p.multi_cell(90,10,str(r['DV']).encode('latin-1','replace').decode('latin-1'),1); h=max(p.get_y()-y,10)
                        p.set_xy(10,y); p.cell(30,h,str(r['Stanza']),1); p.set_xy(130,y); p.cell(35,h,f"{r['Importo Totale']:,.2f}",1); p.cell(35,h,f"{r['Versato']:,.2f}",1,1)
                    p.set_font('Arial','B',10); p.cell(120,10,'TOTALI',1,0,'R'); p.cell(35,10,f"{conf:,.2f}",1,0,'R'); p.cell(35,10,f"{pag:,.2f}",1,1,'R')
                    st.download_button("📥 Scarica PDF", bytes(p.output(dest='S')), "Report.pdf")
            c_t.dataframe(df_r[['Stanza','DV','Importo Totale', 'Versato']], use_container_width=True, hide_index=True)

    elif "📦" in sel:
        sn = sel.replace("📦 ", "").lower(); st.title(f"🏠 {sn.capitalize()}")
        try:
            df = clean_df(conn.read(worksheet=sn, ttl="0"))

            # --- NOVITÀ: TOTALI DI STANZA ---
            t_imp, t_ver = df['Importo Totale'].sum(), df['Versato'].sum()
            col_t1, col_t2 = st.columns(2)
            col_t1.markdown(f'<div class="metric-card">TOTALE STANZA<div class="metric-value-mini">{t_imp:,.2f}€</div></div>', unsafe_allow_html=True)
            col_t2.markdown(f'<div class="metric-card">PAGATO STANZA<div class="metric-value-mini">{t_ver:,.2f}€</div></div>', unsafe_allow_html=True)

            c_sn, c_st = ('Acquista S/N' if 'Acquista S/N' in df.columns else 'S/N'), ('Stato Pagamento' if 'Stato Pagamento' in df.columns else 'Stato')

            with st.expander("📝 NOTE"):
                art = st.selectbox("Seleziona Articolo:", df['DV'].tolist())
                idx_n = df[df['DV'] == art].index[0]
                nt_key = f"note_val_{sn}_{idx_n}"
                if nt_key not in st.session_state: st.session_state[nt_key] = str(df.at[idx_n, 'Note'])
                nt = st.text_area("Nota:", value=st.session_state[nt_key], height=100)
                if st.button("Conferma Nota"):
                    st.session_state[nt_key] = nt; st.success("Nota pronta per il salvataggio!")

            with st.form(f"f_{sn}"):
                cfg = {c_sn: st.column_config.SelectboxColumn(c_sn, options=["S", "N"]), c_st: st.column_config.SelectboxColumn(c_st, options=["", "Acconto", "Saldato", "Preventivo"]), "Data Scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"), "Link Fattura": st.column_config.LinkColumn("📂 Doc", display_text="Apri")}
                df_e = st.data_editor(df.drop(columns=['DV']), use_container_width=True, hide_index=True, num_rows="dynamic" if edit_struct else "fixed", column_config=cfg)
                if st.form_submit_button("💾 SALVA TUTTO"):
                    for i in range(len(df_e)):
                        k = f"note_val_{sn}_{i}"
                        if k in st.session_state: df_e.at[i, 'Note'] = st.session_state[k]
                        try:
                            r = df_e.iloc[i]; p, s, q = float(r.get('Prezzo Pieno',0)), float(r.get('Sconto %',0)), float(r.get('Acquistato',1))
                            c = p * (1-(s/100)) if p>0 else float(r.get('Costo',0))
                            df_e.at[df_e.index[i],'Costo'] = c; df_e.at[df_e.index[i],'Importo Totale'] = c*q
                            if "Saldato" in str(r.get(c_st,'')): df_e.at[df_e.index[i],'Versato'] = c*q
                        except: continue
                    conn.update(worksheet=sn, data=df_e.fillna('')); st.cache_data.clear(); st.success("Salvato!"); st.rerun()
        except: st.error("⚠️ Errore di connessione. Riprova tra 5 secondi.")

    elif "✨" in sel:
        st.title("✨ Wishlist")
        try:
            df_w = clean_df(conn.read(worksheet="desideri", ttl="0"))
            w_cfg = {"Link": st.column_config.LinkColumn("🔗 Web", display_text="Apri Sito"), "Foto": st.column_config.LinkColumn("📸 Foto", display_text="Vedi Foto")}
            df_ew = st.data_editor(df_w.drop(columns=['DV']), use_container_width=True, hide_index=True, column_config=w_cfg, num_rows="dynamic" if edit_struct else "fixed")
            if st.button("Salva Wishlist"):
                conn.update(worksheet="desideri", data=df_ew.fillna('')); st.cache_data.clear(); st.rerun()
        except: st.error("⚠️ Errore di connessione.")
