import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from fpdf import FPDF
import time

# --- 1. IL SIGILLO DI SICUREZZA ---
if st.secrets.get("sicurezza", {}).get("sigillo") != "ATTIVATO":
    st.error("⚠️ LICENZA NON TROVATA")
    st.stop()

# --- 2. CONFIGURAZIONE TEMA ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

st.set_page_config(page_title="Monitoraggio Arredamento V18.5", layout="wide", page_icon="🚀")

# Stili CSS
if st.session_state.dark_mode:
    bg_color, card_color, text_color = "#0e1117", "#1d2129", "#ffffff"
    header_grad = "linear-gradient(90deg, #0f2027, #203a43, #2c5364)"
else:
    bg_color, card_color, text_color = "#f8f9fc", "#ffffff", "#1f2937"
    header_grad = "linear-gradient(90deg, #2e5a88, #4a90e2)"

st.markdown(f"<style>.stApp {{ background-color: {bg_color}; color: {text_color}; }} .main-header {{ background: {header_grad}; padding: 30px; border-radius: 15px; color: white; margin-bottom: 25px; }} .metric-card {{ background-color: {card_color}; padding: 20px; border-radius: 12px; border-bottom: 5px solid #2e5a88; text-align: center; color: {text_color}; }} .prediction-box {{ background-color: {card_color}; padding: 15px; border-left: 5px solid #f39c12; border-radius: 8px; margin-top: 10px; }} .alert-box {{ background-color: #fff3cd; color: #856404; padding: 10px; border-radius: 5px; border-left: 5px solid #ffeeba; margin-bottom: 10px; font-weight: bold; }}</style>", unsafe_allow_html=True)

# --- 3. BLOCCO PDF BLINDATO ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182); self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        # Regola Proprietà con à
        testo = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C'); self.ln(15)

def safe_clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    # Logica per descrizione (Articolo prioritario)
    df['Descrizione_Visualizzata'] = df['Articolo'] if 'Articolo' in df.columns else (df['Oggetto'] if 'Oggetto' in df.columns else "Elemento")
    for c in ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    return df

# --- 4. ACCESSO E SIDEBAR ---
if "password_correct" not in st.session_state:
    st.title("🔒 Accesso Riservato")
    u = st.text_input("Utente"); p = st.text_input("Password", type="password")
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
        selezione = st.selectbox("NAVIGAZIONE", ["🏠 Riepilogo", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze_reali])
        st.markdown("---")
        can_edit_structure = st.toggle("⚙️ Modifica Struttura", value=False)
        st.markdown("<br><br>---<br>✨ **Roberto & Gemini**<br><small>Proprietà: Jacopo</small>", unsafe_allow_html=True)
        if st.button("Logout 🚪"): st.session_state.clear(); st.rerun()

    # --- RIEPILOGO GENERALE ---
    if "Riepilogo" in selezione:
        st.markdown(f'<div class="main-header"><h1 style="color:white; margin:0;">Command Center</h1><p style="margin:0; opacity:0.8;">Proprietà: Jacopo</p></div>', unsafe_allow_html=True)
        all_rows = []; potential_cost = 0; scadenze_imminenti = []
        try:
            df_imp = conn.read(worksheet="Impostazioni", ttl=0)
            budget_totale = pd.to_numeric(df_imp.iloc[0, 1], errors='coerce')
        except: budget_totale = 15000.0

        for s in stanze_reali:
            try:
                df_s = safe_clean_df(conn.read(worksheet=s, ttl=0))
                if not df_s.empty:
                    c_sn = 'Acquista S/N' if 'Acquista S/N' in df_s.columns else 'S/N'
                    df_c = df_s[df_s[c_sn].str.upper().str.strip() == 'S'].copy()
                    df_c['Ambiente'] = s.capitalize()
                    all_rows.append(df_c)
                    potential_cost += df_s[df_s[c_sn].str.upper().str.strip() != 'S']['Importo Totale'].sum()
                    if 'Data Scadenza' in df_s.columns:
                        for _, r in df_s.iterrows():
                            if r.get('Data Scadenza') and str(r.get('Stato Pagamento')) != 'Saldato':
                                try:
                                    dt = pd.to_datetime(r['Data Scadenza'], dayfirst=True)
                                    if dt <= datetime.now() + timedelta(days=7):
                                        scadenze_imminenti.append(f"⏰ {s.capitalize()}: {r['Descrizione_Visualizzata']} ({r['Data Scadenza']})")
                                except: pass
            except: continue

        if scadenze_imminenti:
            for alert in scadenze_imminenti: st.markdown(f'<div class="alert-box">{alert}</div>', unsafe_allow_html=True)

        if all_rows:
            df_final = pd.concat(all_rows); tot_conf = df_final['Importo Totale'].sum(); tot_versato = df_final['Versato'].sum(); residuo = budget_totale - tot_conf
            st.progress(min(tot_conf / budget_totale, 1.0) if budget_totale > 0 else 0)
            st.markdown(f'<div class="prediction-box">🔍 <b>Analisi Predittiva:</b> Potenziale spesa in attesa: {potential_cost:,.2f}€.</div>', unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            with m1: st.markdown(f'<div class="metric-card"><div class="metric-label">Budget</div><div class="metric-value">{budget_totale:,.0f}€</div></div>', unsafe_allow_html=True)
            with m2: st.markdown(f'<div class="metric-card"><div class="metric-label">Confermato</div><div class="metric-value">{tot_conf:,.0f}€</div></div>', unsafe_allow_html=True)
            with m3: st.markdown(f'<div class="metric-card"><div class="metric-label">Pagato</div><div class="metric-value">{tot_versato:,.0f}€</div></div>', unsafe_allow_html=True)
            with m4:
                color = "#28a745" if residuo >= 0 else "#dc3545"
                st.markdown(f'<div class="metric-card"><div class="metric-label">Disponibile</div><div class="metric-value" style="color:{color}">{residuo:,.0f}€</div></div>', unsafe_allow_html=True)

            if st.button("📄 Genera Report PDF"):
                pdf = PDF(); pdf.add_page(); pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(46, 117, 182); pdf.set_text_color(255, 255, 255)
                pdf.cell(30, 10, 'Stanza', 1, 0, 'C', True); pdf.cell(90, 10, 'Articolo', 1, 0, 'C', True); pdf.cell(35, 10, 'Totale', 1, 0, 'C', True); pdf.cell(35, 10, 'Versato', 1, 1, 'C', True)
                pdf.set_font('Arial', '', 9); pdf.set_text_color(0, 0, 0)
                for _, row in df_final.iterrows():
                    txt = str(row['Descrizione_Visualizzata']).encode('latin-1', 'replace').decode('latin-1')
                    start_y = pdf.get_y(); pdf.set_xy(40, start_y); pdf.multi_cell(90, 10, txt, border=1)
                    h = max(pdf.get_y() - start_y, 10); pdf.set_xy(10, start_y); pdf.cell(30, h, str(row['Ambiente']), 1)
                    pdf.set_xy(130, start_y); pdf.cell(35, h, f"{row['Importo Totale']:,.2f}", 1, 0, 'R'); pdf.cell(35, h, f"{row['Versato']:,.2f}", 1, 1, 'R')
                pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(230, 230, 230); pdf.cell(120, 10, 'TOTALI GENERALI', 1, 0, 'R', True)
                pdf.cell(35, 10, f"{tot_conf:,.2f}", 1, 0, 'R', True); pdf.cell(35, 10, f"{tot_versato:,.2f}", 1, 1, 'R', True)
                st.download_button("📥 Scarica PDF", data=bytes(pdf.output(dest='S')), file_name="Report.pdf")

    # --- STANZE (IL CUORE DELLA CORREZIONE) ---
    elif "📦" in selezione:
        stanza_nome = selezione.replace("📦 ", "").lower()
        st.title(f"🏠 {stanza_nome.capitalize()}")
        df = safe_clean_df(conn.read(worksheet=stanza_nome, ttl=0))

        with st.form(f"f_{stanza_nome}"):
            # CONFIGURAZIONE DINAMICA: Evita l'errore mappendo solo colonne esistenti
            c_config = {}
            col_sn = 'Acquista S/N' if 'Acquista S/N' in df.columns else ('S/N' if 'S/N' in df.columns else None)
            col_stato = 'Stato Pagamento' if 'Stato Pagamento' in df.columns else ('Stato' if 'Stato' in df.columns else None)

            if col_sn: c_config[col_sn] = st.column_config.SelectboxColumn(col_sn, options=["S", "N"])
            if col_stato: c_config[col_stato] = st.column_config.SelectboxColumn(col_stato, options=["", "Acconto", "Saldato", "Preventivo"])
            if "Link Fattura" in df.columns: c_config["Link Fattura"] = st.column_config.LinkColumn("📂 Doc", display_text="Apri")
            if "Data Scadenza" in df.columns: c_config["Data Scadenza"] = st.column_config.DateColumn("📅 Scadenza", format="DD/MM/YYYY")

            df_vis = df.drop(columns=['Descrizione_Visualizzata', 'Oggetto'], errors='ignore')
            df_edit = st.data_editor(df_vis, use_container_width=True, hide_index=True, column_config=c_config, num_rows="dynamic" if can_edit_structure else "fixed")

            if st.form_submit_button("💾 SALVA"):
                for i in range(len(df_edit)):
                    try:
                        row = df_edit.iloc[i]
                        p, s, q = float(row.get('Prezzo Pieno',0)), float(row.get('Sconto %',0)), float(row.get('Acquistato',1))
                        costo = p * (1 - (s/100)) if p > 0 else float(row.get('Costo',0))
                        df_edit.at[df_edit.index[i], 'Costo'] = costo
                        df_edit.at[df_edit.index[i], 'Importo Totale'] = costo * q
                        if str(row.get(col_stato, "")).strip() == "Saldato": df_edit.at[df_edit.index[i], 'Versato'] = costo * q
                    except: continue
                conn.update(worksheet=stanza_nome, data=df_edit)
                st.cache_data.clear(); st.balloons(); st.rerun()

    # --- WISHLIST ---
    elif "✨" in selezione:
        st.title("✨ Wishlist")
        df_w = safe_clean_df(conn.read(worksheet="desideri", ttl=0))
        c_wish = {}
        if "Foto" in df_w.columns: c_wish["Foto"] = st.column_config.ImageColumn("Anteprima")
        if "Link" in df_w.columns: c_wish["Link"] = st.column_config.LinkColumn("Sito", display_text="Apri")
        df_ed_w = st.data_editor(df_w.drop(columns=['Descrizione_Visualizzata', 'Oggetto'], errors='ignore'), use_container_width=True, hide_index=True, column_config=c_wish, num_rows="dynamic" if can_edit_structure else "fixed")
        if st.button("Salva Wishlist"):
            conn.update(worksheet="desideri", data=df_ed_w); st.cache_data.clear(); st.balloons(); st.rerun()
