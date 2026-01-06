import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time
import requests

# --- SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V22.10.12", layout="wide", page_icon="🚀")

# --- CONNESSIONE SUPABASE ---
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

sb = get_supabase()

# --- STILE ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
bc, cc, tc = ("#0e1117", "#1d2129", "#ffffff") if st.session_state.dark_mode else ("#f8f9fc", "#ffffff", "#1f2937")
grad = "linear-gradient(90deg, #0f2027, #203a43, #2c5364)" if st.session_state.dark_mode else "linear-gradient(90deg, #2e5a88, #4a90e2)"
st.markdown(f"""<style>
    .stApp {{background-color: {bc}; color: {tc};}}
    .main-header {{background: {grad}; padding: 30px; border-radius: 15px; color: white; margin-bottom: 25px;}}
    .metric-card {{background-color: {cc}; padding: 15px; border-radius: 10px; border-bottom: 4px solid #2e5a88; text-align: center; color: {tc}; margin-bottom: 10px;}}
    .metric-value {{font-size: 1.8em; font-weight: 800; color: #2e5a88;}}
    .metric-savings {{font-size: 1.8em; font-weight: 800; color: #28a745;}} /* Verde per il risparmio */
    .gold-seal {{background: linear-gradient(145deg, #ffdf00, #d4af37); padding: 20px; border-radius: 15px; text-align: center; color: black; font-weight: bold; border: 2px solid #b8860b; margin-bottom: 20px; box-shadow: 0px 4px 15px rgba(212, 175, 55, 0.4);}}
    .manual-container {{background-color: {cc}; padding: 30px; border-radius: 15px; border: 1px solid #e0e0e0; line-height: 1.6;}}
</style>""", unsafe_allow_html=True)

class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182); self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10); t = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, t.encode('latin-1','replace').decode('latin-1'), ln=True, align='C'); self.ln(15)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(128, 128, 128)
        self.cell(0, 10, "Prodotto di Proprietà: Roberto & Gemini".encode('latin-1','replace').decode('latin-1'), 0, 0, 'C')

def clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    mapping = {'articolo': 'Articolo', 'acquistato': 'Acquistato', 'costo': 'Costo', 'importo_totale': 'Importo Totale', 'acquista_sn': 'Acquista S/N', 'note': 'Note', 'versato': 'Versato', 'prezzo_pieno': 'Prezzo Pieno', 'sconto_perc': 'Sconto %', 'stato_pagamento': 'Stato Pagamento', 'link_fattura': 'Link Fattura', 'link': 'Link', 'foto': 'Foto', 'data_scadenza': 'Data Scadenza', 'stanza_chiusa': 'Stanza Chiusa'}
    df = df.rename(columns=mapping)
    df['Stanza Chiusa'] = df['Stanza Chiusa'].apply(lambda x: str(x).upper().strip() in ['TRUE', '1', 'T'])
    df['DV'] = df['Articolo']
    for c in ['Note', 'Acquista S/N', 'Stato Pagamento', 'Link Fattura', 'Link', 'Foto']:
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
    stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]
    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: pass
        st.session_state.dark_mode = st.toggle("🌙 Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze] + ["📖 Manuale"])
        edit_struct = st.toggle("⚙️ Modifica Struttura", False)
        st.markdown("<br>---<br>✨ **Roberto & Gemini**<br><small>Proprietà: Jacopo</small>", unsafe_allow_html=True)
        if st.button("Logout 🚪"): st.session_state.clear(); st.rerun()

    if sel == "🏠 Riepilogo":
        st.markdown('<div class="main-header"><h1>Command Center</h1><p>Proprietà: Jacopo</p></div>', unsafe_allow_html=True)
        bud = 15000.0
        res = sb.table("arredamento").select("*").execute()
        df_all = clean_df(pd.DataFrame(res.data))

        if not df_all.empty:
            df_r = df_all[df_all['Acquista S/N'].str.upper().str.strip() == 'S'].copy()
            conf, pag = df_r['Importo Totale'].sum(), df_r['Versato'].sum()

            # --- ANALISI RISPARMIO ---
            # Calcoliamo il valore teorico (Prezzo Pieno * Quantità) vs Importo Totale (quello scontato)
            valore_teorico = (df_r['Prezzo Pieno'] * df_r['Acquistato']).sum()
            risparmio_totale = valore_teorico - conf
            # --------------------------

            # Prima riga metriche (Budget e Pagamenti)
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f'<div class="metric-card">BUDGET<div class="metric-value">{bud:,.0f}€</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card">CONFERMATO<div class="metric-value">{conf:,.0f}€</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card">PAGATO<div class="metric-value">{pag:,.0f}€</div></div>', unsafe_allow_html=True)
            m4.markdown(f'<div class="metric-card">DISPONIBILE<div class="metric-value">{bud-conf:,.0f}€</div></div>', unsafe_allow_html=True)

            # Seconda riga metriche (Nuova: Analisi Risparmio)
            s1, s2 = st.columns(2)
            s1.markdown(f'<div class="metric-card">VALORE REALE MERCE<div class="metric-value">{valore_teorico:,.0f}€</div></div>', unsafe_allow_html=True)
            s2.markdown(f'<div class="metric-card">RISPARMIO TOTALIZZATO 🟢<div class="metric-savings">{risparmio_totale:,.0f}€</div></div>', unsafe_allow_html=True)

            st.subheader("🗓️ Scadenzario")
            sc = df_r[df_r['Data Scadenza'].notna()].copy()
            sc = sc[sc['Versato'] < sc['Importo Totale']]
            if not sc.empty:
                oggi = pd.Timestamp(datetime.now().date())
                sc['gg'] = (sc['Data Scadenza'] - oggi).dt.days
                sc['Stato'] = sc['gg'].apply(lambda x: "🔴 SCADUTO" if x < 0 else ("🟠 IMMINENTE" if x <= 7 else "🟢 OK"))
                sc_display = sc.sort_values('gg').copy()
                sc_display['Data Scadenza'] = sc_display['Data Scadenza'].dt.strftime('%d/%m/%Y')
                st.dataframe(sc_display[['stanza','DV','Data Scadenza','Stato']], use_container_width=True, hide_index=True)
            else: st.info("Nessuna scadenza imminente trovata.")

            c_p, c_t = st.columns([1, 1.2])
            with c_p:
                st.plotly_chart(px.pie(df_r, values='Importo Totale', names='stanza', hole=0.5), use_container_width=True)
                if st.button("📄 PDF"):
                    p = PDF(); p.add_page(); p.set_font('Arial','B',10); p.set_fill_color(46,117,182); p.set_text_color(255,255,255)
                    p.cell(30,10,'Stanza',1,0,'C',1); p.cell(90,10,'Articolo',1,0,'C',1); p.cell(35,10,'Totale',1,0,'C',1); p.cell(35,10,'Versato',1,1,'C',1)
                    p.set_font('Arial','',9); p.set_text_color(0,0,0)
                    for _, r in df_r.iterrows():
                        y=p.get_y(); p.set_xy(40,y); p.multi_cell(90,10,str(r['DV']).encode('latin-1','replace').decode('latin-1'),1); h=max(p.get_y()-y,10)
                        p.set_xy(10,y); p.cell(30,h,str(r['stanza']),1); p.set_xy(130,y); p.cell(35,h,f"{r['Importo Totale']:,.2f}",1); p.cell(35,h,f"{r['Versato']:,.2f}",1,1)
                    st.download_button("📥 Scarica PDF", bytes(p.output(dest='S')), "Report.pdf")
            c_t.dataframe(df_r[['stanza','DV','Importo Totale', 'Versato']], use_container_width=True, hide_index=True)

    elif sel == "📖 Manuale":
        st.markdown('<div class="main-header"><h1>Manuale d\'Uso</h1><p>Proprietà: Jacopo</p></div>', unsafe_allow_html=True)
        try:
            url_manuale = f"https://raw.githubusercontent.com/{st.secrets['github']['user']}/{st.secrets['github']['repo']}/main/manuale.md"
            response = requests.get(url_manuale)
            if response.status_code == 200:
                st.markdown(f'<div class="manual-container">', unsafe_allow_html=True)
                st.markdown(response.text)
                st.markdown('</div>', unsafe_allow_html=True)
            else: st.warning("⚠️ Manuale non trovato su GitHub.")
        except: st.error("❌ Errore connessione Manuale.")

    elif "📦" in sel or "✨" in sel:
        is_wish = "✨" in sel
        sn = "Wishlist" if is_wish else sel.replace("📦 ", "").capitalize()
        st.title(f"{sel}")
        res = sb.table("arredamento").select("*").eq("stanza", sn).execute()
        df = clean_df(pd.DataFrame(res.data))
        if not df.empty:
            is_closed = any(df['Stanza Chiusa'] == True)
            if is_closed and not is_wish: st.markdown(f'<div class="gold-seal">🏆 COMPLIMENTI! La stanza {sn} è completata!</div>', unsafe_allow_html=True)
            t_imp, t_ver = df['Importo Totale'].sum(), df['Versato'].sum()
            c1, c2 = st.columns(2)
            c1.markdown(f'<div class="metric-card">TOTALE STANZA<div class="metric-value">{t_imp:,.2f}€</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card">PAGATO STANZA<div class="metric-value">{t_ver:,.2f}€</div></div>', unsafe_allow_html=True)
            with st.expander("📝 NOTE"):
                art = st.selectbox("Seleziona Articolo:", df['DV'].tolist())
                idx_n = df[df['DV'] == art].index[0]
                nt_key = f"note_val_{sn}_{idx_n}"
                if nt_key not in st.session_state: st.session_state[nt_key] = str(df.at[idx_n, 'Note'])
                nt = st.text_area("Nota:", value=st.session_state[nt_key], height=100)
                if st.button("Conferma Nota"): st.session_state[nt_key] = nt; st.success("Nota pronta!")
            with st.form(f"f_{sn}"):
                check_chiusura = st.checkbox("🔒 Chiudi Stanza (Attiva Sigillo Oro)", value=is_closed) if not is_wish else False
                cfg = {"Acquista S/N": st.column_config.SelectboxColumn("Acquista S/N", options=["S", "N"]), "Stato Pagamento": st.column_config.SelectboxColumn("Stato Pagamento", options=["", "Acconto", "Saldato", "Preventivo"]), "Data Scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"), "Link Fattura": st.column_config.LinkColumn("📂 Doc", display_text="Apri"), "Link": st.column_config.LinkColumn("🔗 Web", display_text="Apri"), "Foto": st.column_config.LinkColumn("📸 Foto", display_text="Vedi")}
                df_e = st.data_editor(df.drop(columns=['DV','stanza']), use_container_width=True, hide_index=True, num_rows="dynamic" if edit_struct else "fixed", column_config=cfg)
                if st.form_submit_button("💾 SALVA TUTTO"):
                    df_e['Stanza Chiusa'] = check_chiusura
                    for i in range(len(df_e)):
                        k = f"note_val_{sn}_{i}"
                        if k in st.session_state: df_e.at[df_e.index[i], 'Note'] = st.session_state[k]
                        p, s, q = float(df_e.iloc[i].get('Prezzo Pieno',0)), float(df_e.iloc[i].get('Sconto %',0)), float(df_e.iloc[i].get('Acquistato',1))
                        c = p * (1-(s/100)) if p>0 else float(df_e.iloc[i].get('Costo',0))
                        df_e.at[df_e.index[i],'Costo'] = c; df_e.at[df_e.index[i],'Importo Totale'] = c*q
                        if "Saldato" in str(df_e.iloc[i].get('Stato Pagamento','')):
                            df_e.at[df_e.index[i],'Versato'] = c*q
                            df_e.at[df_e.index[i],'Data Scadenza'] = None
                    sb.table("arredamento").delete().eq("stanza", sn).execute()
                    inv_map = {v: k for k, v in {'articolo': 'Articolo', 'acquistato': 'Acquistato', 'costo': 'Costo', 'importo_totale': 'Importo Totale', 'acquista_sn': 'Acquista S/N', 'note': 'Note', 'versato': 'Versato', 'prezzo_pieno': 'Prezzo Pieno', 'sconto_perc': 'Sconto %', 'stato_pagamento': 'Stato Pagamento', 'link_fattura': 'Link Fattura', 'link': 'Link', 'foto': 'Foto', 'data_scadenza': 'Data Scadenza', 'stanza_chiusa': 'Stanza Chiusa'}.items()}
                    df_db = df_e.rename(columns=inv_map)
                    df_db['stanza'] = sn
                    if 'data_scadenza' in df_db.columns:
                        df_db['data_scadenza'] = df_db['data_scadenza'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else None)
                    sb.table("arredamento").insert(df_db.to_dict(orient='records')).execute()
                    st.balloons(); st.success("Salvato su Database!"); time.sleep(1); st.rerun()
