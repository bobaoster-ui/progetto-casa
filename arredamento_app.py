import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento V7.7", layout="wide", page_icon="🏠")

# Colori
COLOR_AZZURRO = (46, 117, 182)

# --- CLASSE PDF OTTIMIZZATA ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(*COLOR_AZZURRO)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        # Regola fissa: Proprietà con à
        testo = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

# --- FUNZIONE PULIZIA DATI ESTREMA ---
def safe_clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]

    # Se mancano colonne fondamentali, le creiamo noi per non far crashare l'app
    target_cols = {
        'Oggetto': 'Oggetto non definito',
        'Importo Totale': 0.0,
        'Versato': 0.0,
        'Stato Pagamento': 'Da definire',
        'Acquista S/N': 'N'
    }
    for col, val in target_cols.items():
        if col not in df.columns:
            df[col] = val

    # Conversione numeri
    for col in ['Importo Totale', 'Versato']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
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
    stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        st.markdown("### 🛠 Sicurezza")
        can_edit_structure = st.toggle("Modifica Struttura", value=False)
        selezione = st.selectbox("Menu:", ["Riepilogo Generale", "✨ Wishlist"] + stanze_reali)
        if st.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()

    # --- 1. RIEPILOGO GENERALE ---
    if selezione == "Riepilogo Generale":
        st.title("🏠 Dashboard Riepilogo")
        all_rows = []

        for s in stanze_reali:
            try:
                df_s = safe_clean_df(conn.read(worksheet=s, ttl=0))
                if not df_s.empty:
                    # Troviamo la colonna di scelta (S/N)
                    col_scelta = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df_s.columns), 'Acquista S/N')
                    df_c = df_s[df_s[col_scelta].astype(str).str.upper() == 'S'].copy()
                    if not df_c.empty:
                        df_c['Ambiente'] = s.capitalize()
                        all_rows.append(df_c)
            except: continue

        if all_rows:
            df_final = pd.concat(all_rows)
            tot_conf = df_final['Importo Totale'].sum()
            tot_versato = df_final['Versato'].sum()

            m1, m2, m3 = st.columns(3)
            m1.metric("CONFERMATO", f"{tot_conf:,.2f} €")
            m2.metric("PAGATO", f"{tot_versato:,.2f} €")
            m3.metric("DA SALDARE", f"{(tot_conf - tot_versato):,.2f} €")

            st.dataframe(df_final[['Ambiente', 'Oggetto', 'Importo Totale', 'Versato', 'Stato Pagamento']], use_container_width=True, hide_index=True)

            # --- PDF FIX DEFINITIVO ---
            if st.button("📄 Genera Report PDF"):
                try:
                    pdf = PDF()
                    pdf.add_page()
                    pdf.set_font('Arial', 'B', 10)
                    pdf.set_fill_color(*COLOR_AZZURRO); pdf.set_text_color(255,255,255)
                    pdf.cell(30, 10, 'Stanza', 1, 0, 'C', True)
                    pdf.cell(90, 10, 'Oggetto', 1, 0, 'C', True)
                    pdf.cell(35, 10, 'Totale', 1, 0, 'C', True)
                    pdf.cell(35, 10, 'Versato', 1, 1, 'C', True)

                    pdf.set_font('Arial', '', 9); pdf.set_text_color(0,0,0)
                    for _, row in df_final.iterrows():
                        pdf.cell(30, 8, str(row['Ambiente']), 1)
                        clean_obj = str(row['Oggetto'])[:45].encode('latin-1', 'replace').decode('latin-1')
                        pdf.cell(90, 8, clean_obj, 1)
                        pdf.cell(35, 8, f"{row['Importo Totale']:,.2f}", 1, 0, 'R')
                        pdf.cell(35, 8, f"{row['Versato']:,.2f}", 1, 1, 'R')

                    # Trucco: convertiamo esplicitamente in stringa di byte standard
                    pdf_output = pdf.output(dest='S')
                    if not isinstance(pdf_output, bytes):
                        pdf_output = bytes(pdf_output, 'latin-1') if isinstance(pdf_output, str) else bytes(pdf_output)

                    st.download_button("📥 Scarica Report PDF", data=pdf_output, file_name="Report_Arredamento.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"Errore PDF: {e}")
        else:
            st.warning("Nessun articolo confermato (S) trovato nelle stanze.")

    # --- 2. STANZE ---
    elif selezione in stanze_reali:
        st.title(f"🏠 {selezione.capitalize()}")
        df = safe_clean_df(conn.read(worksheet=selezione, ttl=0))
        with st.form(f"form_{selezione}"):
            df_edit = st.data_editor(df, use_container_width=True, hide_index=True,
                                     num_rows="dynamic" if can_edit_structure else "fixed")
            if st.form_submit_button("💾 SALVA"):
                # Ricalcolo
                for i in range(len(df_edit)):
                    try:
                        p = float(df_edit.at[i, 'Prezzo Pieno'])
                        s = float(df_edit.at[i, 'Sconto %'])
                        q = float(df_edit.at[i, 'Acquistato'])
                        costo = p * (1 - (s/100)) if p > 0 else float(df_edit.at[i, 'Costo'])
                        df_edit.at[i, 'Costo'] = costo
                        df_edit.at[i, 'Importo Totale'] = costo * q
                        if str(df_edit.at[i, 'Stato Pagamento']) == "Saldato":
                            df_edit.at[i, 'Versato'] = df_edit.at[i, 'Importo Totale']
                    except: continue
                conn.update(worksheet=selezione, data=df_edit)
                st.success("Salvato!"); time.sleep(1); st.rerun()

    # --- 3. WISHLIST ---
    elif selezione == "✨ Wishlist":
        st.title("✨ Wishlist")
        df_w = safe_clean_df(conn.read(worksheet="desideri", ttl=0))
        df_ed_w = st.data_editor(df_w, use_container_width=True, hide_index=True)
        if st.button("Salva Wishlist"):
            conn.update(worksheet="desideri", data=df_ed_w)
            st.rerun()
