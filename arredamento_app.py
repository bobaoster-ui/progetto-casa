import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# --- [SICUREZZA E LICENZA] ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA"); st.stop()

st.set_page_config(page_title="Monitoraggio Arredamento V22.9.8", layout="wide", page_icon="🏆")

# --- [STILE CSS ORIGINALE] ---
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
bc, cc, tc = ("#0e1117", "#1d2129", "#ffffff") if st.session_state.dark_mode else ("#f8f9fc", "#ffffff", "#1f2937")
grad = "linear-gradient(90deg, #0f2027, #203a43, #2c5364)" if st.session_state.dark_mode else "linear-gradient(90deg, #2e5a88, #4a90e2)"

st.markdown(f"""<style>
    .stApp {{background-color: {bc}; color: {tc};}}
    .main-header {{background: {grad}; padding: 30px; border-radius: 15px; color: white; margin-bottom: 25px;}}
    .metric-card {{background-color: {cc}; padding: 20px; border-radius: 12px; border-bottom: 5px solid #2e5a88; text-align: center; color: {tc};}}
    .metric-value {{font-size: 1.8em; font-weight: 800; color: #2e5a88;}}
    .gold-seal {{background: linear-gradient(145deg, #ffdf00, #d4af37); padding: 20px; border-radius: 15px; text-align: center; color: black; font-weight: bold; border: 2px solid #b8860b; margin: 20px 0; box-shadow: 0px 4px 15px rgba(212, 175, 55, 0.4);}}
</style>""", unsafe_allow_html=True)

# --- [FUNZIONI CORE] ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182); self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10); t = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, t.encode('latin-1','replace').decode('latin-1'), ln=True, align='C'); self.ln(15)

def clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    df['DV'] = df['Articolo'] if 'Articolo' in df.columns else df.get('Oggetto', 'N/A')
    for c in ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    for c in ['Link Fattura', 'Link', 'Foto', 'Stanza Chiusa']:
        if c in df.columns: df[c] = df[c].astype(str).replace(['None', 'nan', ''], '')
    return df

# --- [ACCESSO RIPRISTINATO] ---
if "password_correct" not in st.session_state:
    st.title("🔒 Accesso")
    col1, col2 = st.columns(2)
    user = col1.text_input("Username")
    pwd = col2.text_input("Password", type="password")
    if st.button("Accedi"):
        if user == st.secrets["auth"]["username"] and pwd == st.secrets["auth"]["password"]:
            st.session_state.password_correct = True; st.rerun()
        else: st.error("Credenziali errate")
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        st.session_state.dark_mode = st.toggle("🌙 Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze])
        edit_struct = st.toggle("⚙️ Modifica Struttura", False)
        st.markdown("---")
        st.write("**Proprietà: Jacopo**")

    if "Riepilogo" in sel:
        st.markdown('<div class="main-header"><h1>Command Center 🏆</h1></div>', unsafe_allow_html=True)
        try:
            all_data = []
            for s in stanze:
                d = clean_df(conn.read(worksheet=s, ttl="5m"))
                if not d.empty:
                    cs = 'Acquista S/N' if 'Acquista S/N' in d.columns else 'S/N'
                    temp = d[d[cs].str.upper().str.strip() == 'S'].copy()
                    temp['Stanza'] = s.capitalize(); all_data.append(temp)
            if all_data:
                fdf = pd.concat(all_data)
                c1, c2, c3 = st.columns(3)
                c1.markdown(f'<div class="metric-card">CONFERMATO<div class="metric-value">{fdf["Importo Totale"].sum():,.2f}€</div></div>', unsafe_allow_html=True)
                c2.markdown(f'<div class="metric-card">PAGATO<div class="metric-value">{fdf["Versato"].sum():,.2f}€</div></div>', unsafe_allow_html=True)
                c3.markdown(f'<div class="metric-card">RESTANTE<div class="metric-value">{fdf["Importo Totale"].sum()-fdf["Versato"].sum():,.2f}€</div></div>', unsafe_allow_html=True)
                st.plotly_chart(px.pie(fdf, values='Importo Totale', names='Stanza', hole=0.4), use_container_width=True)
        except: st.error("Errore di caricamento dati.")

    elif "📦" in sel:
        sn = sel.replace("📦 ", "").lower(); st.title(f"🏠 {sn.capitalize()}")
        df = clean_df(conn.read(worksheet=sn, ttl="0"))
        is_closed = any(df['Stanza Chiusa'].astype(str).str.upper() == "TRUE") if 'Stanza Chiusa' in df.columns else False

        if is_closed:
            st.markdown(f'<div class="gold-seal">🏆 COMPLIMENTI! La stanza {sn.capitalize()} è completata!</div>', unsafe_allow_html=True)

        with st.form(f"form_{sn}"):
            chiudi = st.checkbox("🔒 Chiudi Stanza (Sigillo)", value=is_closed)
            show_cols = [c for c in df.columns if c not in ['DV', 'Stanza Chiusa']]
            df_e = st.data_editor(df[show_cols], use_container_width=True, hide_index=True, num_rows="dynamic" if edit_struct else "fixed", column_config={
                "Link Fattura": st.column_config.LinkColumn("📂 Doc Drive")
            })
            if st.form_submit_button("💾 SALVA"):
                df_e['Stanza Chiusa'] = "TRUE" if chiudi else "FALSE"
                conn.update(worksheet=sn, data=df_e)
                st.cache_data.clear(); st.success("Salvato!"); st.rerun()

    elif "✨" in sel:
        st.title("✨ Wishlist")
        df_w = clean_df(conn.read(worksheet="desideri", ttl="0"))
        df_ew = st.data_editor(df_w, use_container_width=True, hide_index=True, column_config={
            "Link": st.column_config.LinkColumn("🔗 Web", display_text="Apri Sito"),
            "Foto": st.column_config.LinkColumn("📸 Foto", display_text="Vedi Foto")
        }, num_rows="dynamic" if edit_struct else "fixed")
        if st.button("Salva Wishlist"):
            conn.update(worksheet="desideri", data=df_ew); st.success("Aggiornato!"); st.rerun()
