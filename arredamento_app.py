import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime
from fpdf import FPDF

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento v2.5", layout="wide", page_icon="🏠")

# --- CLASSE PER IL PDF ---
class PDF(FPDF):
    def header(self):
        # Colore Blu Professionale
        self.set_fill_color(46, 117, 182)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(0, 20, 'REPORT SPESE ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 12)
        self.cell(0, 10, 'Proprietà: Jacopo', ln=True, align='C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()} - Generato il {datetime.now().strftime("%d/%m/%Y")}', align='C')

# --- FUNZIONE DI LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 Accesso Riservato")
        u = st.text_input("Utente")
        p = st.text_input("Password", type="password")
        if st.button("Accedi"):
            if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Credenziali errate")
        return False
    return True

if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)

    if st.sidebar.button("Logout 🚪"):
        st.session_state.clear()
        st.rerun()

    st.title("🏠 Gestione Arredamento Professionale")

    stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]
    selezione = st.sidebar.selectbox("Menu:", ["Riepilogo Generale"] + stanze_reali)

if selezione == "Riepilogo Generale":
        lista_completa = []
        tot_conf = 0

        for s in stanze_reali:
            try:
                df_s = conn.read(worksheet=s, ttl=0)
                if df_s is not None and not df_s.empty:
                    # Pulizia nomi colonne
                    df_s.columns = [str(c).strip() for c in df_s.columns]

                    # Cerchiamo il prezzo tra varie opzioni possibili
                    col_p = next((c for c in ['Importo Totale', 'Totale', 'Prezzo', 'Costo'] if c in df_s.columns), None)
                    # Cerchiamo la scelta S/N
                    col_s = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df_s.columns), None)

                    if col_p and col_s:
                        df_s[col_p] = pd.to_numeric(df_s[col_p], errors='coerce').fillna(0)
                        df_s_conf = df_s[df_s[col_s].astype(str).str.upper() == 'S'].copy()
                        if not df_s_conf.empty:
                            df_s_conf['Ambiente'] = s.capitalize()
                            # Prendiamo solo le colonne che esistono davvero
                            lista_completa.append(df_s_conf[['Ambiente', 'Oggetto', col_p]])
                            tot_conf += df_s_conf[col_p].sum()
                    else:
                        st.warning(f"Nella stanza {s} mancano le colonne 'Totale' o 'S/N'. Controlla il foglio Google!")
            except Exception as e:
                st.error(f"Errore nella stanza {s}: {e}")

        if lista_completa:
            df_final = pd.concat(lista_completa)

            st.subheader(f"Totale Confermato: {tot_conf:,.2f} €")
            st.dataframe(df_final, use_container_width=True, hide_index=True)

            # --- GENERAZIONE PDF ---
            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 12)

            # Intestazione Tabella
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(40, 10, 'Ambiente', 1, 0, 'C', True)
            pdf.cell(100, 10, 'Oggetto', 1, 0, 'C', True)
            pdf.cell(50, 10, 'Importo', 1, 1, 'C', True)

            # Corpo Tabella
            pdf.set_font("Arial", '', 10)
            for _, row in df_final.iterrows():
                pdf.cell(40, 8, str(row['Ambiente']), 1)
                pdf.cell(100, 8, str(row['Oggetto'])[:50], 1)
                pdf.cell(50, 8, f"{row.iloc[2]:,.2f} EUR", 1, 1, 'R')

            pdf.ln(5)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(140, 10, 'TOTALE GENERALE', 0)
            pdf.cell(50, 10, f"{tot_conf:,.2f} EUR", 0, 1, 'R')

            pdf_output = pdf.output()

            st.sidebar.download_button(
                label="📄 Scarica Report PDF Professionale",
                data=bytes(pdf_output),
                file_name=f"Report_Arredamento_Jacopo_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
            st.success("Report PDF pronto nella barra laterale!")
