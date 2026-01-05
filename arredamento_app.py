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

st.set_page_config(page_title="Monitoraggio Arredamento V22.0", layout="wide", page_icon="🏆")

# --- STILE GOLD EDITION ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
bc, cc, tc = ("#0e1117", "#1d2129", "#ffffff") if st.session_state.dark_mode else ("#f8f9fc", "#ffffff", "#1f2937")
grad = "linear-gradient(90deg, #d4af37, #f1c40f)" if st.session_state.dark_mode else "linear-gradient(90deg, #2e5a88, #4a90e2)"
st.markdown(f"""<style>
    .stApp {{background-color: {bc}; color: {tc};}}
    .main-header {{background: {grad}; padding: 30px; border-radius: 15px; color: white; margin-bottom: 25px;}}
    .metric-card {{background-color: {cc}; padding: 15px; border-radius: 10px; border-bottom: 4px solid #d4af37; text-align: center; color: {tc}; margin-bottom: 10px;}}
    .gold-seal {{background: linear-gradient(145deg, #ffdf00, #d4af37); padding: 20px; border-radius: 15px; text-align: center; color: black; font-weight: bold; border: 2px solid #b8860b; margin: 20px 0;}}
    .metric-value-mini {{font-size: 1.4em; font-weight: 700; color: #d4af37;}}
</style>""", unsafe_allow_html=True)

# ... [Classe PDF e funzioni clean_df rimangono invariate per blindatura] ...
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
    df.columns = [str(c).strip() for c in df.columns]
    df['DV'] = df['Articolo'] if 'Articolo' in df.columns else df.get('Oggetto', 'N/A')
    for c in ['Note', 'Acquista S/N', 'S/N', 'Stato Pagamento', 'Stato', 'Link Fattura', 'Link', 'Foto']:
        if c in df.columns: df[c] = df[c].astype(str).replace(['None', 'nan', '<NA>', 'null', ''], '')
    for c in ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    if 'Data Scadenza' in df.columns: df['Data Scadenza'] = pd.to_datetime(df['Data Scadenza'], errors='coerce')
    return df

# --- LOGICA CORE ---
if "password_correct" not in st.session_state:
    st.title("🔒 Accesso")
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]: st.session_state.password_correct = True; st.rerun()
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        st.session_state.dark_mode = st.toggle("🌙 Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze])
        edit_struct = st.toggle("⚙️ Modifica Struttura", False)
        st.markdown("<br>---<br>✨ **Roberto & Gemini**<br><small>Proprietà: Jacopo</small>", unsafe_allow_html=True)

    if "Riepilogo" in sel:
        st.markdown('<div class="main-header"><h1>Command Center 🏆</h1><p>Proprietà: Jacopo</p></div>', unsafe_allow_html=True)
        # ... [Riepilogo e Scadenzario rimangono invariati per blindatura] ...
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

    elif "📦" in sel:
        sn = sel.replace("📦 ", "").lower(); st.title(f"📦 {sn.capitalize()}")
        try:
            df = clean_df(conn.read(worksheet=sn, ttl="0"))

            # TOTALI DI STANZA
            t_imp, t_ver = df['Importo Totale'].sum(), df['Versato'].sum()
            col_t1, col_t2 = st.columns(2)
            col_t1.markdown(f'<div class="metric-card">TOTALE STANZA<div class="metric-value-mini">{t_imp:,.2f}€</div></div>', unsafe_allow_html=True)
            col_t2.markdown(f'<div class="metric-card">PAGATO STANZA<div class="metric-value-mini">{t_ver:,.2f}€</div></div>', unsafe_allow_html=True)

            # MIRABILIA: SIGILLO ORO
            c_st = ('Stato Pagamento' if 'Stato Pagamento' in df.columns else 'Stato')
            if not df.empty and all(str(x).strip() == "Saldato" for x in df[df['Acquista S/N'] == 'S'][c_st]):
                st.markdown(f'<div class="gold-seal">🏆 COMPLIMENTI! La stanza {sn.capitalize()} è stata ufficialmente completata e saldata!</div>', unsafe_allow_html=True)

            # DATA EDITOR
            with st.form(f"f_{sn}"):
                cfg = {c_st: st.column_config.SelectboxColumn(c_st, options=["", "Acconto", "Saldato", "Preventivo"]), "Data Scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"), "Link Fattura": st.column_config.LinkColumn("📂 Doc Drive", display_text="Apri")}
                df_e = st.data_editor(df.drop(columns=['DV']), use_container_width=True, hide_index=True, num_rows="dynamic" if edit_struct else "fixed", column_config=cfg)
                if st.form_submit_button("💾 SALVA MODIFICHE"):
                    # Logica ricalcolo e azzeramento scadenza saldati
                    for i in range(len(df_e)):
                        try:
                            r = df_e.iloc[i]; p, q = float(r.get('Prezzo Pieno',0)), float(r.get('Acquistato',1))
                            if "Saldato" in str(r.get(c_st,'')):
                                df_e.at[df_e.index[i],'Versato'] = r['Importo Totale']
                                df_e.at[df_e.index[i],'Data Scadenza'] = pd.NaT
                        except: continue
                    conn.update(worksheet=sn, data=df_e.fillna('')); st.cache_data.clear(); st.balloons(); st.rerun()

            # MIRABILIA: CHECKLIST COLLAUDO
            st.markdown("---")
            st.subheader("🏁 Checklist Fine Lavori")
            c1, c2, c3 = st.columns(3)
            with c1: st.checkbox(f"Montaggio {sn.capitalize()} Verificato", key=f"check1_{sn}")
            with c2: st.checkbox("Assenza Graffi/Danni", key=f"check2_{sn}")
            with c3: st.checkbox("Pulizia Post-Cantiere", key=f"check3_{sn}")

        except Exception as e: st.error(f"Attesa Google... {e}")

    elif "✨" in sel:
        # ... [Wishlist rimane invariata] ...
        st.title("✨ Wishlist")
        df_w = clean_df(conn.read(worksheet="desideri", ttl="0"))
        df_ew = st.data_editor(df_w.drop(columns=['DV']), use_container_width=True, hide_index=True)
        if st.button("Salva Wishlist"): conn.update(worksheet="desideri", data=df_ew.fillna('')); st.balloons(); st.rerun()
