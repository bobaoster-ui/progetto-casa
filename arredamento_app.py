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
    st.write("Questo software è un'opera dell'ingegno di **Roberto & Gemini**.")
    st.info("Per utilizzare questa applicazione è necessario il permesso dell'autore.")
    st.stop()

# --- 2. CONFIGURAZIONE PAGINA & CSS (Il "Motore Estetico") ---
st.set_page_config(page_title="Monitoraggio Arredamento V17.0", layout="wide", page_icon="🏠")

st.markdown("""
    <style>
    /* Sfondo dell'intera app */
    .stApp {
        background-color: #f8f9fc;
    }

    /* Header Blu come nel Mockup */
    .main-header {
        background-color: #2e5a88;
        padding: 30px;
        border-radius: 15px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }

    /* Stile delle Card Metriche */
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-bottom: 5px solid #2e5a88;
        text-align: center;
    }

    .metric-label {
        color: #5a5a5a;
        font-size: 0.9em;
        font-weight: bold;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .metric-value {
        color: #2e5a88;
        font-size: 1.8em;
        font-weight: 800;
    }

    /* Pulizia Sidebar */
    [data-testid="stSidebar"] {
        background-color: white;
        border-right: 1px solid #e0e0e0;
    }
    </style>
    """, unsafe_allow_html=True)

COLOR_AZZURRO = (46, 117, 182)

class PDF(FPDF):
    def header(self):
        self.set_fill_color(*COLOR_AZZURRO)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        # Regola memorizzata: Proprietà con à accentata
        testo = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

def safe_clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    if 'Articolo' in df.columns:
        df['Descrizione_Visualizzata'] = df['Articolo']
    elif 'Oggetto' in df.columns:
        df['Descrizione_Visualizzata'] = df['Oggetto']
    else:
        df['Descrizione_Visualizzata'] = ""
    text_cols = ['Oggetto', 'Articolo', 'Note', 'Acquista S/N', 'S/N', 'Stato Pagamento', 'Stato', 'Link Fattura', 'Link', 'Foto']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).replace(['None', 'nan', '104807', '<NA>', 'undefined', 'null'], '')
    cols_num = ['Importo Totale', 'Versato', 'Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo']
    for c in cols_num:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    return df

# --- 3. LOGICA DI ACCESSO ---
if "password_correct" not in st.session_state:
    st.title("🔒 Accesso Riservato")
    u = st.text_input("Utente")
    p = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("Credenziali errate")
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: pass
        st.markdown("<br>", unsafe_allow_html=True)
        selezione = st.selectbox("MENU NAVIGAZIONE", ["🏠 Riepilogo Generale", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze_reali])
        st.markdown("---")
        can_edit_structure = st.toggle("⚙️ Modifica Struttura", value=False)
        if st.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()
        st.markdown(f"<div style='text-align: center; color: grey; font-size: 0.8em; margin-top: 50px;'>© 2026 - Roberto & Gemini<br>Proprietà: Jacopo</div>", unsafe_allow_html=True)

    # --- RIEPILOGO GENERALE (STILE MOCKUP V3.5) ---
    if "Riepilogo" in selezione:
        # Header Blue Design
        st.markdown(f"""
            <div class="main-header">
                <h1 style="margin:0; color:white;">Gestione Spese Arredamento Professionale</h1>
                <p style="margin:0; opacity: 0.8;">Proprietà: Jacopo - Report consolidato del {datetime.now().strftime('%d/%m/%Y')}</p>
            </div>
            """, unsafe_allow_html=True)

        try:
            df_imp = conn.read(worksheet="Impostazioni", ttl=0)
            budget_iniziale = pd.to_numeric(df_imp.iloc[0, 1], errors='coerce')
            if pd.isna(budget_iniziale): budget_iniziale = 15000.0
        except: budget_iniziale = 15000.0

        all_rows = []
        for s in stanze_reali:
            try:
                df_s = safe_clean_df(conn.read(worksheet=s, ttl=0))
                if not df_s.empty:
                    c_sn = 'Acquista S/N' if 'Acquista S/N' in df_s.columns else 'S/N'
                    df_c = df_s[df_s[c_sn].str.upper().str.strip() == 'S'].copy()
                    if not df_c.empty:
                        df_c['Ambiente'] = s.capitalize()
                        all_rows.append(df_c)
            except: continue

        if all_rows:
            df_final = pd.concat(all_rows)
            tot_conf = df_final['Importo Totale'].sum()
            tot_versato = df_final['Versato'].sum()
            rimanente = budget_iniziale - tot_conf

            # Cards Metriche (come nel disegno)
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown(f'<div class="metric-card"><div class="metric-label">Budget Totale</div><div class="metric-value">{budget_iniziale:,.0f} €</div></div>', unsafe_allow_html=True)
            with m2:
                st.markdown(f'<div class="metric-card"><div class="metric-label">Confermato</div><div class="metric-value">{tot_conf:,.0f} €</div></div>', unsafe_allow_html=True)
            with m3:
                st.markdown(f'<div class="metric-card"><div class="metric-label">Pagato</div><div class="metric-value">{tot_versato:,.0f} €</div></div>', unsafe_allow_html=True)
            with m4:
                colore_disp = "#28a745" if rimanente >= 0 else "#dc3545"
                st.markdown(f'<div class="metric-card"><div class="metric-label">Disponibile</div><div class="metric-value" style="color:{colore_disp}">{rimanente:,.0f} €</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Grafico e Tabella in card bianche
            col_dx, col_sx = st.columns([1, 1.5])

            with col_dx:
                st.markdown('<div style="background-color:white; padding:20px; border-radius:12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">', unsafe_allow_html=True)
                st.subheader("Analisi Spesa")
                fig_pie = px.pie(df_final, values='Importo Totale', names='Ambiente', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
                st.plotly_chart(fig_pie, use_container_width=True)

                if st.button("📄 Esporta Report PDF"):
                    try:
                        pdf = PDF()
                        pdf.add_page()
                        pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(*COLOR_AZZURRO); pdf.set_text_color(255, 255, 255)
                        pdf.cell(30, 10, 'Stanza', 1, 0, 'C', True); pdf.cell(90, 10, 'Articolo', 1, 0, 'C', True)
                        pdf.cell(35, 10, 'Totale', 1, 0, 'C', True); pdf.cell(35, 10, 'Versato', 1, 1, 'C', True)
                        pdf.set_font('Arial', '', 9); pdf.set_text_color(0, 0, 0)
                        for _, row in df_final.iterrows():
                            art_val = str(row['Descrizione_Visualizzata']).strip()
                            txt = art_val.encode('latin-1', 'replace').decode('latin-1')
                            linee = pdf.multi_cell(90, 5, txt, split_only=True)
                            h = max(10, len(linee) * 5)
                            if pdf.get_y() + h > 260: pdf.add_page()
                            x, y = pdf.get_x(), pdf.get_y()
                            pdf.rect(x, y, 30, h); pdf.set_xy(x, y); pdf.cell(30, h, str(row['Ambiente']), 0, 0, 'L')
                            pdf.rect(x + 30, y, 90, h); pdf.set_xy(x + 30, y); pdf.multi_cell(90, 5, txt, 0, 'L')
                            pdf.rect(x + 120, y, 35, h); pdf.set_xy(x + 120, y); pdf.cell(35, h, f"{row['Importo Totale']:,.2f}", 0, 0, 'R')
                            pdf.rect(x + 155, y, 35, h); pdf.set_xy(x + 155, y); pdf.cell(35, h, f"{row['Versato']:,.2f}", 0, 1, 'R')
                            pdf.set_y(y + h)
                        st.download_button("📥 Scarica", data=bytes(pdf.output(dest='S')), file_name="Report.pdf")
                    except Exception as e: st.error(f"Errore: {e}")
                st.markdown('</div>', unsafe_allow_html=True)

            with col_sx:
                st.markdown('<div style="background-color:white; padding:20px; border-radius:12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">', unsafe_allow_html=True)
                st.subheader("Dettaglio Confermati")
                df_view = df_final[['Ambiente', 'Descrizione_Visualizzata', 'Importo Totale', 'Versato']].copy()
                df_view.rename(columns={'Descrizione_Visualizzata': 'Articolo'}, inplace=True)
                st.dataframe(df_view, use_container_width=True, hide_index=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # --- STANZE E WISHLIST --- (Mantengono lo stile standard per facilità di editing)
    elif "📦" in selezione:
        stanza_nome = selezione.replace("📦 ", "").lower()
        st.title(f"🏠 Gestione {stanza_nome.capitalize()}")
        df = safe_clean_df(conn.read(worksheet=stanza_nome, ttl=0))
        col_sn = 'Acquista S/N' if 'Acquista S/N' in df.columns else 'S/N'
        col_stato = 'Stato Pagamento' if 'Stato Pagamento' in df.columns else 'Stato'
        with st.form(f"f_{stanza_nome}"):
            c = {col_sn: st.column_config.SelectboxColumn(col_sn, options=["S", "N"]), "Note": st.column_config.TextColumn("Note", width="large")}
            df_edit = st.data_editor(df.drop(columns=['Descrizione_Visualizzata'], errors='ignore'), use_container_width=True, hide_index=True, column_config=c, num_rows="dynamic" if can_edit_structure else "fixed")
            if st.form_submit_button("💾 SALVA"):
                with st.spinner("Aggiornamento..."):
                    for i in range(len(df_edit)):
                        try:
                            p, s, q = float(df_edit.iloc[i]['Prezzo Pieno']), float(df_edit.iloc[i]['Sconto %']), float(df_edit.iloc[i]['Acquistato'])
                            costo = p * (1 - (s/100)) if p > 0 else float(df_edit.iloc[i]['Costo'])
                            totale = costo * q
                            df_edit.at[df_edit.index[i], 'Costo'] = costo
                            df_edit.at[df_edit.index[i], 'Importo Totale'] = totale
                            st_val = str(df_edit.iloc[i][col_stato]).strip()
                            if st_val in ["", "None", "nan"]: df_edit.at[df_edit.index[i], 'Versato'] = 0.0
                            elif st_val == "Saldato": df_edit.at[df_edit.index[i], 'Versato'] = totale
                        except: continue
                    conn.update(worksheet=stanza_nome, data=df_edit)
                    st.success("Dati salvati!"); st.balloons(); time.sleep(1); st.rerun()

    elif "✨" in selezione:
        st.title("✨ Wishlist")
        df_w = safe_clean_df(conn.read(worksheet="desideri", ttl=0))
        if 'Foto' in df_w.columns: df_w['Anteprima'] = df_w['Foto']
        df_ed_w = st.data_editor(df_w.drop(columns=['Descrizione_Visualizzata'], errors='ignore'), use_container_width=True, hide_index=True, column_config={"Anteprima": st.column_config.ImageColumn("Foto")})
        if st.button("Salva Wishlist"):
            df_save = df_ed_w.drop(columns=['Anteprima']) if 'Anteprima' in df_ed_w.columns else df_ed_w
            conn.update(worksheet="desideri", data=df_save); st.balloons(); time.sleep(1); st.rerun()
