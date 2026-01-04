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

# --- 2. CONFIGURAZIONE PAGINA & TEMA (DARK/LIGHT) ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

st.set_page_config(page_title="Monitoraggio Arredamento V18.0", layout="wide", page_icon="🚀")

# Definizione colori in base al tema
if st.session_state.dark_mode:
    bg_color = "#0e1117"
    card_color = "#1d2129"
    text_color = "#ffffff"
    header_grad = "linear-gradient(90deg, #0f2027, #203a43, #2c5364)"
else:
    bg_color = "#f8f9fc"
    card_color = "#ffffff"
    text_color = "#1f2937"
    header_grad = "linear-gradient(90deg, #2e5a88, #4a90e2)"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .main-header {{
        background: {header_grad}; padding: 30px; border-radius: 15px;
        color: white; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }}
    .metric-card {{
        background-color: {card_color}; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-bottom: 5px solid #2e5a88; text-align: center;
        color: {text_color};
    }}
    .metric-label {{ color: #888; font-size: 0.9em; font-weight: bold; text-transform: uppercase; }}
    .metric-value {{ font-size: 1.8em; font-weight: 800; color: #2e5a88; }}
    .prediction-box {{
        background-color: {card_color}; padding: 15px; border-left: 5px solid #f39c12;
        border-radius: 8px; margin-top: 10px; font-size: 0.95em;
    }}
    </style>
    """, unsafe_allow_html=True)

COLOR_AZZURRO = (46, 117, 182)

# --- 3. BLOCCO PDF BLINDATO ---
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

def safe_clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    if 'Articolo' in df.columns: df['Descrizione_Visualizzata'] = df['Articolo']
    elif 'Oggetto' in df.columns: df['Descrizione_Visualizzata'] = df['Oggetto']
    else: df['Descrizione_Visualizzata'] = ""
    text_cols = ['Oggetto', 'Articolo', 'Note', 'Acquista S/N', 'S/N', 'Stato Pagamento', 'Stato', 'Link Fattura', 'Link', 'Foto']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).replace(['None', 'nan', '<NA>', 'undefined', 'null'], '')
    cols_num = ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']
    for c in cols_num:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    return df

# --- 4. LOGICA ACCESSO E SIDEBAR ---
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

        # Switch Tema
        st.session_state.dark_mode = st.toggle("🌙 Modalità Notte", value=st.session_state.dark_mode)

        selezione = st.selectbox("MENU NAVIGAZIONE", ["🏠 Riepilogo Generale", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze_reali])
        st.markdown("---")
        can_edit_structure = st.toggle("⚙️ Modifica Struttura", value=False)
        if st.button("Logout 🚪"): st.session_state.clear(); st.rerun()

    # --- RIEPILOGO GENERALE + ANALISI PREDITTIVA ---
    if "Riepilogo" in selezione:
        st.markdown(f'<div class="main-header"><h1 style="color:white; margin:0;">Command Center Arredamento</h1><p style="margin:0; opacity:0.8;">Proprietà: Jacopo</p></div>', unsafe_allow_html=True)

        try:
            df_imp = conn.read(worksheet="Impostazioni", ttl="5m")
            budget_totale = pd.to_numeric(df_imp.iloc[0, 1], errors='coerce')
        except: budget_totale = 15000.0

        all_rows = []
        potential_cost = 0 # Per analisi predittiva

        for s in stanze_reali:
            try:
                df_s = safe_clean_df(conn.read(worksheet=s, ttl="1m"))
                if not df_s.empty:
                    c_sn = 'Acquista S/N' if 'Acquista S/N' in df_s.columns else 'S/N'
                    # Confermato (S)
                    df_c = df_s[df_s[c_sn].str.upper().str.strip() == 'S'].copy()
                    df_c['Ambiente'] = s.capitalize()
                    all_rows.append(df_c)
                    # Potenziale (N)
                    df_n = df_s[df_s[c_sn].str.upper().str.strip() != 'S']
                    potential_cost += df_n['Importo Totale'].sum()
            except: continue

        if all_rows:
            df_final = pd.concat(all_rows)
            tot_conf = df_final['Importo Totale'].sum()
            tot_versato = df_final['Versato'].sum()
            percentuale = min(tot_conf / budget_totale, 1.0) if budget_totale > 0 else 0

            # Sezione Avanzamento e Predizione
            st.write(f"**Avanzamento Spesa Reale: {tot_conf:,.2f}€ / {budget_totale:,.2f}€**")
            st.progress(percentuale)

            # --- BLOCCO ANALISI PREDITTIVA ---
            residuo = budget_totale - tot_conf
            st.markdown(f"""
            <div class="prediction-box">
                🔍 <b>Analisi Predittiva:</b><br>
                Hai ancora <b>{potential_cost:,.2f}€</b> di articoli in lista ma non confermati.<br>
                {'✅ Il tuo budget copre tutti i potenziali acquisti!' if potential_cost <= residuo
                 else f'⚠️ Attenzione: se confermi tutto, supererai il budget di <b>{(potential_cost - residuo):,.2f}€</b>'}
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            with m1: st.markdown(f'<div class="metric-card"><div class="metric-label">Budget</div><div class="metric-value">{budget_totale:,.0f}€</div></div>', unsafe_allow_html=True)
            with m2: st.markdown(f'<div class="metric-card"><div class="metric-label">Confermato</div><div class="metric-value">{tot_conf:,.0f}€</div></div>', unsafe_allow_html=True)
            with m3: st.markdown(f'<div class="metric-card"><div class="metric-label">Pagato</div><div class="metric-value">{tot_versato:,.0f}€</div></div>', unsafe_allow_html=True)
            with m4:
                c_rim = "#28a745" if residuo >= 0 else "#dc3545"
                st.markdown(f'<div class="metric-card"><div class="metric-label">Disponibile</div><div class="metric-value" style="color:{c_rim}">{residuo:,.0f}€</div></div>', unsafe_allow_html=True)

            col_dx, col_sx = st.columns([1, 1.5])
            with col_dx:
                st.plotly_chart(px.pie(df_final, values='Importo Totale', names='Ambiente', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True)
                if st.button("📄 Report PDF"):
                    pdf = PDF(); pdf.add_page()
                    pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(*COLOR_AZZURRO); pdf.set_text_color(255, 255, 255)
                    pdf.cell(30, 10, 'Stanza', 1, 0, 'C', True); pdf.cell(90, 10, 'Articolo', 1, 0, 'C', True)
                    pdf.cell(35, 10, 'Totale', 1, 0, 'C', True); pdf.cell(35, 10, 'Versato', 1, 1, 'C', True)
                    pdf.set_font('Arial', '', 9); pdf.set_text_color(0, 0, 0)
                    for _, row in df_final.iterrows():
                        txt = str(row['Descrizione_Visualizzata']).encode('latin-1', 'replace').decode('latin-1')
                        start_y = pdf.get_y(); pdf.set_xy(40, start_y)
                        pdf.multi_cell(90, 10, txt, border=1)
                        h = max(pdf.get_y() - start_y, 10)
                        pdf.set_xy(10, start_y); pdf.cell(30, h, str(row['Ambiente']), 1)
                        pdf.set_xy(130, start_y); pdf.cell(35, h, f"{row['Importo Totale']:,.2f}", 1, 0, 'R')
                        pdf.cell(35, h, f"{row['Versato']:,.2f}", 1, 1, 'R')
                    st.download_button("📥 Scarica PDF", data=bytes(pdf.output(dest='S')), file_name="Report_Home.pdf")
            with col_sx:
                st.dataframe(df_final[['Ambiente', 'Descrizione_Visualizzata', 'Importo Totale', 'Versato']], use_container_width=True, hide_index=True)

    # --- STANZE BLINDATE ---
    elif "📦" in selezione:
        stanza_nome = selezione.replace("📦 ", "").lower()
        st.title(f"🏠 {stanza_nome.capitalize()}")
        df = safe_clean_df(conn.read(worksheet=stanza_nome, ttl="1m"))
        col_sn = 'Acquista S/N' if 'Acquista S/N' in df.columns else 'S/N'
        col_stato = 'Stato Pagamento' if 'Stato Pagamento' in df.columns else 'Stato'
        with st.form(f"f_{stanza_nome}"):
            c_config = {
                col_sn: st.column_config.SelectboxColumn(col_sn, options=["S", "N"]),
                col_stato: st.column_config.SelectboxColumn(col_stato, options=["", "Acconto", "Saldato", "Preventivo"]),
                "Link Fattura": st.column_config.LinkColumn("📂 Doc", display_text="Apri"),
                "Note": st.column_config.TextColumn("Note", width="large")
            }
            df_edit = st.data_editor(df.drop(columns=['Descrizione_Visualizzata'], errors='ignore'), use_container_width=True, hide_index=True, column_config=c_config, num_rows="dynamic" if can_edit_structure else "fixed")
            if st.form_submit_button("💾 SALVA"):
                for i in range(len(df_edit)):
                    try:
                        p, s, q = float(df_edit.iloc[i]['Prezzo Pieno']), float(df_edit.iloc[i]['Sconto %']), float(df_edit.iloc[i]['Acquistato'])
                        costo = p * (1 - (s/100)) if p > 0 else float(df_edit.iloc[i]['Costo'])
                        df_edit.at[df_edit.index[i], 'Costo'] = costo
                        df_edit.at[df_edit.index[i], 'Importo Totale'] = costo * q
                        if str(df_edit.iloc[i][col_stato]).strip() == "Saldato":
                            df_edit.at[df_edit.index[i], 'Versato'] = costo * q
                    except: continue
                conn.update(worksheet=stanza_nome, data=df_edit)
                st.cache_data.clear(); st.balloons(); st.success("Salvato!"); time.sleep(1); st.rerun()

    # --- WISHLIST BLINDATA ---
    elif "✨" in selezione:
        st.title("✨ Wishlist")
        df_w = safe_clean_df(conn.read(worksheet="desideri", ttl="1m"))
        c_wish = {"Foto": st.column_config.ImageColumn("Anteprima"), "Link": st.column_config.LinkColumn("Sito", display_text="Apri")}
        df_ed_w = st.data_editor(df_w.drop(columns=['Descrizione_Visualizzata'], errors='ignore'), use_container_width=True, hide_index=True, column_config=c_wish, num_rows="dynamic" if can_edit_structure else "fixed")
        if st.button("Salva Wishlist"):
            conn.update(worksheet="desideri", data=df_ed_w)
            st.cache_data.clear(); st.balloons(); st.rerun()
