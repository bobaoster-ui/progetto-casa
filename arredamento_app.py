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

# --- 2. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Monitoraggio Arredamento V16.1", layout="wide", page_icon="🏠")

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

    # Fix Bug Colonne: Allineiamo "Articolo" su "Oggetto" se necessario
    if 'Articolo' in df.columns and ('Oggetto' not in df.columns or df['Oggetto'].replace(['None', 'nan', ''], pd.NA).dropna().empty):
        df['Oggetto'] = df['Articolo']

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
        st.markdown("---")
        can_edit_structure = st.toggle("⚙️ Modifica Struttura", value=False)
        selezione = st.selectbox("Vai a:", ["🏠 Riepilogo Generale", "✨ Wishlist"] + [f"📦 {s.capitalize()}" for s in stanze_reali])
        st.markdown("---")
        if st.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()
        st.markdown("<div style='text-align: center; color: grey; font-size: 0.8em; margin-top: 50px;'>© 2026 - Roberto & Gemini<br>Proprietà: Jacopo</div>", unsafe_allow_html=True)

    # --- RIEPILOGO GENERALE ---
    if "Riepilogo" in selezione:
        st.title("🏠 Dashboard Riepilogo")
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

            c1, c2, c3 = st.columns(3)
            c1.metric("BUDGET TOTALE", f"{budget_iniziale:,.2f} €")
            c2.metric("CONFERMATO", f"{tot_conf:,.2f} €", delta=f"{budget_iniziale-tot_conf:,.2f} Disp.")
            c3.metric("PAGATO EFFETTIVO", f"{tot_versato:,.2f} €")

            percentuale = min(tot_conf / budget_iniziale, 1.0)
            colore_barra = "#2e75b6" if tot_conf <= budget_iniziale else "#ff4b4b"
            st.markdown(f"""
                <div style="background-color: #f0f2f6; border-radius: 10px; padding: 5px; margin: 10px 0;">
                    <div style="background-color: {colore_barra}; width: {percentuale*100}%;
                    height: 25px; border-radius: 7px; text-align: center; color: white; font-weight: bold; line-height: 25px;">
                        {percentuale*100:.1f}% del Budget Utilizzato
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.divider()

            # SEZIONE PDF E TABELLA
            col_dx, col_sx = st.columns([1, 2])
            with col_dx:
                if st.button("📄 Genera Report PDF"):
                    try:
                        pdf = PDF()
                        pdf.add_page()
                        pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(*COLOR_AZZURRO); pdf.set_text_color(255, 255, 255)
                        pdf.cell(30, 10, 'Stanza', 1, 0, 'C', True); pdf.cell(90, 10, 'Articolo', 1, 0, 'C', True)
                        pdf.cell(35, 10, 'Totale', 1, 0, 'C', True); pdf.cell(35, 10, 'Versato', 1, 1, 'C', True)
                        pdf.set_font('Arial', '', 9); pdf.set_text_color(0, 0, 0)
                        for _, row in df_final.iterrows():
                            # Fix PDF: usa Oggetto (che ora contiene anche Articolo)
                            art_val = str(row['Oggetto']).strip()
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
                        pdf.ln(2); pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(230, 230, 230)
                        pdf.cell(120, 10, 'TOTALI GENERALI', 1, 0, 'R', True)
                        pdf.cell(35, 10, f"{tot_conf:,.2f}", 1, 0, 'R', True)
                        pdf.cell(35, 10, f"{tot_versato:,.2f}", 1, 1, 'R', True)
                        st.download_button("📥 Scarica Report", data=bytes(pdf.output(dest='S')), file_name="Report_Arredi.pdf", mime="application/pdf")
                    except Exception as e: st.error(f"Errore PDF: {e}")

            with col_sx:
                st.subheader("Dettaglio Confermati")
                st.dataframe(df_final[['Ambiente', 'Oggetto', 'Importo Totale', 'Versato', 'Note']], use_container_width=True, hide_index=True)

            st.divider()
            g1, g2 = st.columns(2)
            with g1:
                df_pie = df_final.groupby('Ambiente')['Importo Totale'].sum().reset_index()
                st.plotly_chart(px.pie(df_pie, values='Importo Totale', names='Ambiente', title="Distribuzione Spesa", hole=0.4), use_container_width=True)
            with g2:
                df_bar = pd.DataFrame({"Voce": ["Budget", "Confermato", "Pagato"], "Euro": [budget_iniziale, tot_conf, tot_versato]})
                st.plotly_chart(px.bar(df_bar, x="Voce", y="Euro", color="Voce", title="Confronto Economico"), use_container_width=True)

    # --- STANZE E WISHLIST --- (Invariati)
    elif "📦" in selezione:
        stanza_nome = selezione.replace("📦 ", "").lower()
        st.title(f"🏠 {stanza_nome.capitalize()}")
        df = safe_clean_df(conn.read(worksheet=stanza_nome, ttl=0))
        col_sn = 'Acquista S/N' if 'Acquista S/N' in df.columns else 'S/N'
        col_stato = 'Stato Pagamento' if 'Stato Pagamento' in df.columns else 'Stato'
        with st.form(f"form_{stanza_nome}"):
            config = {
                col_sn: st.column_config.SelectboxColumn(col_sn, options=["S", "N"], width="small"),
                col_stato: st.column_config.SelectboxColumn("Stato", options=["", "Acconto", "Saldato", "Ordinato", "Preventivo"]),
                "Link Fattura": st.column_config.LinkColumn("📂 Doc", display_text="Apri"),
                "Note": st.column_config.TextColumn("Note", width="large")
            }
            df_edit = st.data_editor(df, use_container_width=True, hide_index=True, column_config=config, num_rows="dynamic" if can_edit_structure else "fixed")
            if st.form_submit_button("💾 SALVA MODIFICHE"):
                with st.spinner("Salvataggio..."):
                    for i in range(len(df_edit)):
                        try:
                            p, s, q = float(df_edit.iloc[i]['Prezzo Pieno']), float(df_edit.iloc[i]['Sconto %']), float(df_edit.iloc[i]['Acquistato'])
                            costo = p * (1 - (s/100)) if p > 0 else float(df_edit.iloc[i]['Costo'])
                            totale = costo * q
                            df_edit.at[df_edit.index[i], 'Costo'] = costo
                            df_edit.at[df_edit.index[i], 'Importo Totale'] = totale
                            stato_val = str(df_edit.iloc[i][col_stato]).strip()
                            if stato_val in ["", "None", "nan"]: df_edit.at[df_edit.index[i], 'Versato'] = 0.0
                            elif stato_val == "Saldato": df_edit.at[df_edit.index[i], 'Versato'] = totale
                        except: continue
                    conn.update(worksheet=stanza_nome, data=df_edit)
                    st.success("Dati aggiornati!"); st.balloons(); time.sleep(1); st.rerun()

    elif "✨" in selezione:
        st.title("✨ La tua Wishlist")
        df_w = safe_clean_df(conn.read(worksheet="desideri", ttl=0))
        if 'Foto' in df_w.columns: df_w['Anteprima'] = df_w['Foto']
        w_config = {"Foto": st.column_config.TextColumn("🔗 Link Foto"), "Anteprima": st.column_config.ImageColumn("Visualizzazione"), "Link": st.column_config.LinkColumn("🛒 Negozio", display_text="Vai")}
        df_ed_w = st.data_editor(df_w, use_container_width=True, hide_index=True, column_config=w_config, num_rows="dynamic" if can_edit_structure else "fixed")
        if st.button("Salva Preferiti"):
            df_save = df_ed_w.drop(columns=['Anteprima']) if 'Anteprima' in df_ed_w.columns else df_ed_w
            conn.update(worksheet="desideri", data=df_save); st.balloons(); time.sleep(1); st.rerun()
