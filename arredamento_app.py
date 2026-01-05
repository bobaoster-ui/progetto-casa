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

st.set_page_config(page_title="Monitoraggio Arredamento V22.9.7", layout="wide", page_icon="🏆")

# --- [STILE E CSS PERSONALIZZATO] ---
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

# --- [FUNZIONI PDF E DATI] ---
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

# --- [LOGICA PRINCIPALE] ---
if "password_correct" not in st.session_state:
    st.title("🔒 Accesso Riservato")
    if st.text_input("Password", type="password") == st.secrets["auth"]["password"]:
        if st.button("Entra"): st.session_state.password_correct = True; st.rerun()
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    stanze = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        st.session_state.dark_mode = st.toggle("🌙 Notte", st.session_state.dark_mode)
        sel = st.selectbox("MENU", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze])
        edit_struct = st.toggle("⚙️ Struttura", False)
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
                full_df = pd.concat(all_data)
                c1, c2, c3 = st.columns(3)
                c1.markdown(f'<div class="metric-card">CONFERMATO<div class="metric-value">{full_df["Importo Totale"].sum():,.2f}€</div></div>', unsafe_allow_html=True)
                c2.markdown(f'<div class="metric-card">PAGATO<div class="metric-value">{full_df["Versato"].sum():,.2f}€</div></div>', unsafe_allow_html=True)
                c3.markdown(f'<div class="metric-card">DA PAGARE<div class="metric-value">{full_df["Importo Totale"].sum()-full_df["Versato"].sum():,.2f}€</div></div>', unsafe_allow_html=True)

                if st.button("📄 Genera Report PDF"):
                    pdf = PDF(); pdf.add_page(); pdf.set_font("Arial", size=10)
                    for i, r in full_df.iterrows(): pdf.cell(0, 8, f"{r['Stanza']} - {r['DV']}: {r['Importo Totale']}€", ln=True)
                    st.download_button("📥 Scarica PDF", bytes(pdf.output(dest='S')), "Report_Arredamento.pdf")

                st.plotly_chart(px.pie(full_df, values='Importo Totale', names='Stanza', hole=0.4), use_container_width=True)
        except Exception as e: st.error(f"Errore caricamento: {e}")

    elif "📦" in sel:
        sn = sel.replace("📦 ", "").lower(); st.title(f"🏠 {sn.capitalize()}")
        try:
            df = clean_df(conn.read(worksheet=sn, ttl="0"))
            is_closed = any(df['Stanza Chiusa'].astype(str).str.upper() == "TRUE") if 'Stanza Chiusa' in df.columns else False

            if is_closed:
                st.markdown(f'<div class="gold-seal">🏆 COMPLIMENTI! La stanza {sn.capitalize()} è stata ufficialmente completata!</div>', unsafe_allow_html=True)

            with st.form(f"f_{sn}"):
                check_chiusura = st.checkbox("🔒 Stanza Completata (Attiva Sigillo Oro)", value=is_closed)
                cols_to_show = [c for c in df.columns if c not in ['DV', 'Stanza Chiusa']]
                df_e = st.data_editor(df[cols_to_show], use_container_width=True, hide_index=True, num_rows="dynamic" if edit_struct else "fixed", column_config={
                    "Link Fattura": st.column_config.LinkColumn("📂 Doc Drive")
                })
                if st.form_submit_button("💾 SALVA TUTTO"):
                    df_e['Stanza Chiusa'] = "TRUE" if check_chiusura else "FALSE"
                    # Logica calcolo automatico rinvigorita
                    for i in range(len(df_e)):
                        p, s, q = float(df_e.iloc[i].get('Prezzo Pieno', 0)), float(df_e.iloc[i].get('Sconto %', 0)), float(df_e.iloc[i].get('Acquistato', 1))
                        df_e.at[df_e.index[i], 'Importo Totale'] = (p * (1 - s/100)) * q
                    conn.update(worksheet=sn, data=df_e)
                    st.cache_data.clear(); st.success("Dati Salvati!"); st.balloons(); time.sleep(1); st.rerun()
        except Exception as e: st.error(f"Errore: {e}")

    elif "✨" in sel:
        st.title("✨ Wishlist")
        try:
            df_w = clean_df(conn.read(worksheet="desideri", ttl="0"))
            df_ew = st.data_editor(df_w, use_container_width=True, hide_index=True, column_config={
                "Link": st.column_config.LinkColumn("🔗 Web", display_text="Apri Sito"),
                "Foto": st.column_config.LinkColumn("📸 Foto", display_text="Guarda Foto")
            }, num_rows="dynamic" if edit_struct else "fixed")
            if st.button("Salva Wishlist"):
                conn.update(worksheet="desideri", data=df_ew); st.success("Wishlist aggiornata!"); st.rerun()
        except: st.error("Errore Wishlist")
