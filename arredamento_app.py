import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento V7.4", layout="wide", page_icon="🏠")

# Palette Colori Coerente
COLOR_AZZURRO = (46, 117, 182)  # Il blu dell'app (RGB)
COLOR_GRIGIO_LUCE = (240, 240, 240)

# --- CLASSE PDF AVANZATA ---
class PDF(FPDF):
    def header(self):
        # Rettangolo blu in alto
        self.set_fill_color(*COLOR_AZZURRO)
        self.rect(0, 0, 210, 45, 'F')

        # Titolo bianco
        self.set_font('Arial', 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')

        # Sottotitolo con Proprietà scritta correttamente (à)
        self.set_font('Arial', 'I', 11)
        testo_header = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo_header.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}', align='C')

    def chapter_title(self, label):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(*COLOR_GRIGIO_LUCE)
        self.set_text_color(*COLOR_AZZURRO)
        self.cell(0, 10, f" {label}", 0, 1, 'L', True)
        self.ln(4)

# --- FUNZIONE PULIZIA DATI ---
def safe_clean_df(df):
    if df is None: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    num_cols = ['Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo', 'Versato', 'Importo Totale']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    for col in df.columns:
        if col not in num_cols:
            df[col] = df[col].astype(str).replace(['nan', 'None', '<NA>'], '')
    return df

# --- LOGIN ---
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

    with st.sidebar:
        st.markdown("### 🛠 Sicurezza")
        can_edit_structure = st.toggle("Modifica Struttura", value=False)
        st.divider()
        if st.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()

    stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]
    selezione = st.sidebar.selectbox("Menu Principale:", ["Riepilogo Generale", "✨ Wishlist"] + stanze_reali)

    # --- 1. RIEPILOGO GENERALE ---
    if selezione == "Riepilogo Generale":
        st.title("🏠 Dashboard Riepilogo")
        try:
            df_imp = conn.read(worksheet="impostazioni", ttl=0)
            budget_max = float(df_imp[df_imp['Parametro'] == 'Budget Totale']['Valore'].values[0])
        except: budget_max = 10000.0

        lista_dettaglio = []
        tot_conf, tot_versato = 0.0, 0.0
        dati_per_grafico = []
        dati_residuo_stanze = []

        for s in stanze_reali:
            try:
                df_s = conn.read(worksheet=s, ttl=0)
                if df_s is not None and not df_s.empty:
                    df_s = safe_clean_df(df_s)
                    col_s = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df_s.columns), 'Acquista S/N')
                    imp_stanza = df_s['Importo Totale'].sum()
                    if imp_stanza > 0: dati_per_grafico.append({"Stanza": s.capitalize(), "Budget": imp_stanza})
                    conf_mask = df_s[col_s].astype(str).str.upper() == 'S'
                    df_c = df_s[conf_mask].copy()
                    if not df_c.empty:
                        tot_conf += df_c['Importo Totale'].sum()
                        tot_versato += df_c['Versato'].sum()
                        dati_residuo_stanze.append({"Stanza": s.capitalize(), "Tipo": "Pagato", "Valore": df_c['Versato'].sum()})
                        dati_residuo_stanze.append({"Stanza": s.capitalize(), "Tipo": "Residuo", "Valore": max(0, df_c['Importo Totale'].sum() - df_c['Versato'].sum())})
                        col_o = next((c for c in ['Oggetto', 'Articolo'] if c in df_c.columns), df_c.columns[0])
                        temp_df = pd.DataFrame({
                            'Ambiente': s.capitalize(), 'Oggetto': df_c[col_o],
                            'Importo Totale': df_c['Importo Totale'], 'Versato': df_c['Versato'],
                            'Stato': df_c['Stato Pagamento'] if 'Stato Pagamento' in df_c.columns else "-"
                        })
                        lista_dettaglio.append(temp_df)
            except: continue

        # Metriche Dashboard
        st.subheader(f"📊 Budget Totale: {budget_max:,.2f} €")
        st.progress(min(tot_conf / budget_max, 1.0) if budget_max > 0 else 0)
        m1, m2, m3 = st.columns(3)
        m1.metric("CONFERMATO", f"{tot_conf:,.2f} €")
        m2.metric("PAGATO", f"{tot_versato:,.2f} €")
        m3.metric("DA SALDARE", f"{(tot_conf - tot_versato):,.2f} €")

        # Visualizzazione Grafici (Omessi qui per brevità, ma rimangono quelli della 7.3)
        # ... [Codice Grafici 7.3] ...

        if lista_dettaglio:
            df_final = pd.concat(lista_dettaglio)
            st.subheader("📝 Dettaglio Pagamenti")
            st.dataframe(df_final, use_container_width=True, hide_index=True)

            # --- IL NUOVO PULSANTE PDF ELEGANTE ---
            st.divider()
            if st.button("📄 Genera Report PDF Professionale"):
                pdf = PDF(); pdf.add_page()
                pdf.chapter_title("DETTAGLIO ACQUISTI CONFERMATI")

                # Header Tabella
                pdf.set_font('Arial', 'B', 9)
                pdf.set_fill_color(*COLOR_AZZURRO); pdf.set_text_color(255, 255, 255)
                pdf.cell(30, 10, 'Ambiente', 1, 0, 'C', True)
                pdf.cell(75, 10, 'Oggetto', 1, 0, 'C', True)
                pdf.cell(30, 10, 'Totale EUR', 1, 0, 'C', True)
                pdf.cell(30, 10, 'Versato', 1, 0, 'C', True)
                pdf.cell(25, 10, 'Stato', 1, 1, 'C', True)

                # Righe Tabella
                pdf.set_font('Arial', '', 8); pdf.set_text_color(0, 0, 0)
                for i, row in df_final.iterrows():
                    # Alternanza colori righe
                    fill = (i % 2 == 0)
                    pdf.set_fill_color(245, 245, 245) if fill else pdf.set_fill_color(255, 255, 255)

                    pdf.cell(30, 8, str(row['Ambiente']), 1, 0, 'L', fill)
                    pdf.cell(75, 8, str(row['Oggetto'])[:45].encode('latin-1', 'replace').decode('latin-1'), 1, 0, 'L', fill)
                    pdf.cell(30, 8, f"{row['Importo Totale']:,.2f}", 1, 0, 'R', fill)
                    pdf.cell(30, 8, f"{row['Versato']:,.2f}", 1, 0, 'R', fill)
                    pdf.cell(25, 8, str(row['Stato']), 1, 1, 'C', fill)

                # Riepilogo Finale nel PDF
                pdf.ln(10)
                pdf.chapter_title("SINTESI ECONOMICA")
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(135, 10, 'TOTALE IMPEGNATO:', 0, 0, 'R')
                pdf.cell(55, 10, f'{tot_conf:,.2f} EUR', 1, 1, 'R')
                pdf.cell(135, 10, 'TOTALE GIA\' VERSATO:', 0, 0, 'R')
                pdf.set_text_color(0, 128, 0) # Verde per il pagato
                pdf.cell(55, 10, f'{tot_versato:,.2f} EUR', 1, 1, 'R')
                pdf.set_text_color(200, 0, 0) # Rosso per il debito
                pdf.cell(135, 10, 'RESIDUO DA SALDARE:', 0, 0, 'R')
                pdf.cell(55, 10, f'{(tot_conf - tot_versato):,.2f} EUR', 1, 1, 'R')

                pdf_data = pdf.output(dest='S').encode('latin-1')
                st.download_button("📩 Scarica Report PDF", data=pdf_data, file_name="Report_Jacopo_Arredi.pdf", mime="application/pdf")

    # --- 2. STANZE (Logica 7.2) ---
    elif selezione in stanze_reali:
        st.title(f"🏠 {selezione.capitalize()}")
        df_raw = conn.read(worksheet=selezione, ttl=0)
        df = safe_clean_df(df_raw)

        config = {
            "Acquista S/N": st.column_config.SelectboxColumn("Scelta", options=["S", "N"]),
            "Stato Pagamento": st.column_config.SelectboxColumn("Stato", options=["Da Pagare", "Acconto", "Saldato"]),
            "Importo Totale": st.column_config.NumberColumn("Totale €", format="%.2f", disabled=True),
        }

        with st.form(key=f"form_{selezione}"):
            df_edit = st.data_editor(df, use_container_width=True, hide_index=True,
                                     num_rows="dynamic" if can_edit_structure else "fixed",
                                     column_config=config)
            submit = st.form_submit_button("💾 SALVA E CALCOLA")

        if submit:
            for i in range(len(df_edit)):
                try:
                    pp = float(df_edit.at[i, 'Prezzo Pieno'])
                    sc = float(df_edit.at[i, 'Sconto %'])
                    qta = float(df_edit.at[i, 'Acquistato'])
                    costo = pp * (1 - (sc / 100)) if pp > 0 else float(df_edit.at[i, 'Costo'])
                    df_edit.at[i, 'Costo'] = costo
                    totale = costo * qta
                    df_edit.at[i, 'Importo Totale'] = totale
                    if str(df_edit.at[i, 'Stato Pagamento']) == "Saldato":
                        df_edit.at[i, 'Versato'] = totale
                except: continue
            conn.update(worksheet=selezione, data=df_edit)
            st.session_state["saved_success"] = True
            st.rerun()

        if st.session_state.get("saved_success"):
            st.balloons(); st.success("Dati aggiornati!"); del st.session_state["saved_success"]

    # --- 3. WISHLIST ---
    elif selezione == "✨ Wishlist":
        st.title("✨ Wishlist")
        df_wish = conn.read(worksheet="desideri", ttl=0)
        if df_wish is not None:
            df_wish = safe_clean_df(df_wish)
            df_edit_w = st.data_editor(df_wish, use_container_width=True, hide_index=True,
                                       num_rows="dynamic" if can_edit_structure else "fixed")
            if st.button("💾 SALVA WISHLIST"):
                conn.update(worksheet="desideri", data=df_edit_w)
                st.rerun()
