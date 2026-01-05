import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# --- 1. IL SIGILLO DI SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA")
    st.stop()

# --- 2. CONFIGURAZIONE PAGINA ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

st.set_page_config(page_title="Monitoraggio Arredamento V19.4", layout="wide", page_icon="🚀")

if st.session_state.dark_mode:
    bg_color, card_color, text_color = "#0e1117", "#1d2129", "#ffffff"
    header_grad = "linear-gradient(90deg, #0f2027, #203a43, #2c5364)"
else:
    bg_color, card_color, text_color = "#f8f9fc", "#ffffff", "#1f2937"
    header_grad = "linear-gradient(90deg, #2e5a88, #4a90e2)"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .main-header {{ background: {header_grad}; padding: 30px; border-radius: 15px; color: white; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }}
    .metric-card {{ background-color: {card_color}; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-bottom: 5px solid #2e5a88; text-align: center; color: {text_color}; }}
    .metric-label {{ color: #888; font-size: 0.9em; font-weight: bold; text-transform: uppercase; }}
    .metric-value {{ font-size: 1.8em; font-weight: 800; color: #2e5a88; }}
    .prediction-box {{ background-color: {card_color}; padding: 15px; border-left: 5px solid #f39c12; border-radius: 8px; margin-top: 10px; font-size: 0.95em; }}
    </style>
    """, unsafe_allow_html=True)

COLOR_AZZURRO = (46, 117, 182)

class PDF(FPDF):
    def header(self):
        self.set_fill_color(*COLOR_AZZURRO)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        testo = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(128, 128, 128)
        firma = "Prodotto di Proprietà: Roberto & Gemini"
        self.cell(0, 10, firma.encode('latin-1', 'replace').decode('latin-1'), 0, 0, 'C')

def safe_clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    if 'Articolo' in df.columns: df['Descrizione_Visualizzata'] = df['Articolo']
    elif 'Oggetto' in df.columns: df['Descrizione_Visualizzata'] = df['Oggetto']

    text_cols = ['Oggetto', 'Articolo', 'Note', 'Acquista S/N', 'S/N', 'Stato Pagamento', 'Stato', 'Link Fattura', 'Link', 'Foto']
    for col in text_cols:
        if col in df.columns: df[col] = df[col].astype(str).replace(['None', 'nan', '<NA>', 'undefined', 'null'], '')

    cols_num = ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']
    for c in cols_num:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)

    # --- CURA DELLE DATE (V19.4) ---
    if 'Data Scadenza' in df.columns:
        # Trasformiamo e forziamo a rimanere solo data (senza orario)
        df['Data Scadenza'] = pd.to_datetime(df['Data Scadenza'], errors='coerce')
        # Rimuoviamo il 1899 trasformandolo in valore vuoto (NaT)
        df.loc[df['Data Scadenza'].dt.year < 1950, 'Data Scadenza'] = pd.NaT
    return df

# --- 3. ACCESSO ---
if "password_correct" not in st.session_state:
    st.title("🔒 Accesso Riservato")
    u, p = st.text_input("Utente"), st.text_input("Password", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
            st.session_state["password_correct"] = True; st.rerun()
        else: st.error("Credenziali errate")
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: pass
        st.session_state.dark_mode = st.toggle("🌙 Modalità Notte", value=st.session_state.dark_mode)
        selezione = st.selectbox("MENU NAVIGAZIONE", ["🏠 Riepilogo Generale", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze_reali])
        st.markdown("---")
        can_edit_structure = st.toggle("⚙️ Modifica Struttura", value=False)
        st.markdown("<br><br><br>---<br>✨ **Roberto & Gemini**", unsafe_allow_html=True)
        st.markdown("<small>Proprietà: Jacopo</small>", unsafe_allow_html=True)
        if st.button("Logout 🚪"): st.session_state.clear(); st.rerun()

    if "Riepilogo" in selezione:
        st.markdown(f'<div class="main-header"><h1 style="color:white; margin:0;">Command Center Arredamento</h1><p style="margin:0; opacity:0.8;">Proprietà: Jacopo</p></div>', unsafe_allow_html=True)
        try:
            df_imp = conn.read(worksheet="Impostazioni", ttl="5m")
            budget_totale = pd.to_numeric(df_imp.iloc[0, 1], errors='coerce')
        except: budget_totale = 15000.0
        all_rows = []
        potential_cost = 0
        for s in stanze_reali:
            try:
                df_s = safe_clean_df(conn.read(worksheet=s, ttl="1m"))
                if not df_s.empty:
                    c_sn = 'Acquista S/N' if 'Acquista S/N' in df_s.columns else 'S/N'
                    df_c = df_s[df_s[c_sn].str.upper().str.strip() == 'S'].copy()
                    df_c['Stanza'] = s.capitalize(); all_rows.append(df_c)
                    potential_cost += df_s[df_s[c_sn].str.upper().str.strip() != 'S']['Importo Totale'].sum()
            except: continue
        if all_rows:
            df_final = pd.concat(all_rows)
            tot_conf, tot_versato = df_final['Importo Totale'].sum(), df_final['Versato'].sum()
            st.markdown(f'<div class="prediction-box">🔍 <b>Analisi Predittiva:</b> Potenziale spesa residua: <b>{potential_cost:,.2f}€</b></div>', unsafe_allow_html=True)
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.markdown(f'<div class="metric-card"><div class="metric-label">Budget</div><div class="metric-value">{budget_totale:,.0f}€</div></div>', unsafe_allow_html=True)
            with m2: st.markdown(f'<div class="metric-card"><div class="metric-label">Confermato</div><div class="metric-value">{tot_conf:,.0f}€</div></div>', unsafe_allow_html=True)
            with m3: st.markdown(f'<div class="metric-card"><div class="metric-label">Pagato</div><div class="metric-value">{tot_versato:,.0f}€</div></div>', unsafe_allow_html=True)
            with m4: st.markdown(f'<div class="metric-card"><div class="metric-label">Disponibile</div><div class="metric-value">{budget_totale - tot_conf:,.0f}€</div></div>', unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("🗓️ Scadenzario Pagamenti")
            df_scad = df_final[(df_final['Data Scadenza'].notna()) & (df_final['Versato'] < df_final['Importo Totale'])].copy()
            if not df_scad.empty:
                oggi = pd.Timestamp(datetime.now().date())
                df_scad['gg'] = (df_scad['Data Scadenza'] - oggi).dt.days
                df_scad['Alert'] = df_scad['gg'].apply(lambda x: "🔴 SCADUTO" if x < 0 else ("🟠 IMMINENTE" if x <= 7 else "🟢 In tempo"))
                st.dataframe(df_scad[['Stanza', 'Descrizione_Visualizzata', 'Data Scadenza', 'gg', 'Alert']].sort_values('Data Scadenza'), use_container_width=True, hide_index=True, column_config={"Data Scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY")})
            else: st.info("✅ Nessuna scadenza imminente.")

            col_dx, col_sx = st.columns([1, 1.5])
            with col_dx:
                st.plotly_chart(px.pie(df_final, values='Importo Totale', names='Stanza', hole=0.5), use_container_width=True)
                if st.button("📄 Report PDF"):
                    pdf = PDF(); pdf.add_page(); pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(*COLOR_AZZURRO); pdf.set_text_color(255, 255, 255)
                    pdf.cell(30, 10, 'Stanza', 1, 0, 'C', True); pdf.cell(90, 10, 'Articolo', 1, 0, 'C', True); pdf.cell(35, 10, 'Totale', 1, 0, 'C', True); pdf.cell(35, 10, 'Versato', 1, 1, 'C', True)
                    pdf.set_font('Arial', '', 9); pdf.set_text_color(0, 0, 0)
                    for _, row in df_final.iterrows():
                        txt = str(row['Descrizione_Visualizzata']).encode('latin-1', 'replace').decode('latin-1')
                        y = pdf.get_y(); pdf.set_xy(40, y); pdf.multi_cell(90, 10, txt, border=1); h = max(pdf.get_y() - y, 10)
                        pdf.set_xy(10, y); pdf.cell(30, h, str(row['Stanza']), 1); pdf.set_xy(130, y); pdf.cell(35, h, f"{row['Importo Totale']:,.2f}", 1, 0, 'R'); pdf.cell(35, h, f"{row['Versato']:,.2f}", 1, 1, 'R')
                    pdf.ln(5); pdf.set_font('Arial', 'B', 10); pdf.cell(120, 10, 'TOTALI GENERALI', 1, 0, 'R'); pdf.cell(35, 10, f"{tot_conf:,.2f}", 1, 0, 'R'); pdf.cell(35, 10, f"{tot_versato:,.2f}", 1, 1, 'R')
                    st.download_button("📥 Scarica PDF", data=bytes(pdf.output(dest='S')), file_name="Report.pdf")
            with col_sx: st.dataframe(df_final[['Stanza', 'Descrizione_Visualizzata', 'Importo Totale', 'Versato']], use_container_width=True, hide_index=True)

    elif "📦" in selezione:
        stanza_nome = selezione.replace("📦 ", "").lower()
        st.title(f"🏠 {stanza_nome.capitalize()}")
        df = safe_clean_df(conn.read(worksheet=stanza_nome, ttl="1m"))
        col_sn = 'Acquista S/N' if 'Acquista S/N' in df.columns else 'S/N'
        col_stato = 'Stato Pagamento' if 'Stato Pagamento' in df.columns else 'Stato'
        with st.form(f"f_{stanza_nome}"):
            df_to_edit = df.drop(columns=['Descrizione_Visualizzata'], errors='ignore')
            c_config = {col_sn: st.column_config.SelectboxColumn(col_sn, options=["S", "N"]), col_stato: st.column_config.SelectboxColumn(col_stato, options=["", "Acconto", "Saldato", "Preventivo"]), "Data Scadenza": st.column_config.DateColumn("Data Scadenza", format="DD/MM/YYYY"), "Link Fattura": st.column_config.LinkColumn("📂 Doc", display_text="Apri")}
            df_edit = st.data_editor(df_to_edit, use_container_width=True, hide_index=True, column_config=c_config, num_rows="dynamic" if can_edit_structure else "fixed")
            if st.form_submit_button("💾 SALVA"):
                for i in range(len(df_edit)):
                    try:
                        r = df_edit.iloc[i]
                        p, s, q = float(r.get('Prezzo Pieno', 0)), float(r.get('Sconto %', 0)), float(r.get('Acquistato', 1))
                        costo = p * (1 - (s/100)) if p > 0 else float(r.get('Costo', 0))
                        df_edit.at[df_edit.index[i], 'Costo'] = costo
                        df_edit.at[df_edit.index[i], 'Importo Totale'] = costo * q
                        if str(r.get(col_stato, "")).strip() == "Saldato":
                            df_edit.at[df_edit.index[i], 'Versato'] = costo * q
                    except: continue
                # Pulizia finale prima di mandare a Google
                df_edit = df_edit.fillna('')
                conn.update(worksheet=stanza_nome, data=df_edit)
                st.cache_data.clear(); st.balloons(); time.sleep(1); st.rerun()

    elif "✨" in selezione:
        st.title("✨ Wishlist")
        df_w = safe_clean_df(conn.read(worksheet="desideri", ttl="1m"))
        df_ed_w = st.data_editor(df_w.drop(columns=['Descrizione_Visualizzata'], errors='ignore'), use_container_width=True, hide_index=True, num_rows="dynamic" if can_edit_structure else "fixed")
        if st.button("Salva Wishlist"):
            conn.update(worksheet="desideri", data=df_ed_w.fillna('')); st.cache_data.clear(); st.balloons(); st.rerun()
