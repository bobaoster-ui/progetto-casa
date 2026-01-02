import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime
from fpdf import FPDF

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento v2.8", layout="wide", page_icon="🏠")

# --- CLASSE PER IL PDF ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 20)
        self.set_text_color(255, 255, 255)
        # Usiamo 'EUR' invece di '€' per evitare errori
        self.cell(0, 20, 'REPORT SPESE ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 12)
        self.cell(0, 10, f'Proprieta: Jacopo - {datetime.now().strftime("%d/%m/%Y")}', ln=True, align='C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}', align='C')

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

    stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]
    selezione = st.sidebar.selectbox("Menu:", ["Riepilogo Generale"] + stanze_reali)

    st.title("🏠 Gestione Arredamento Professionale")

    if selezione == "Riepilogo Generale":
        lista_completa = []
        tot_conf = 0
        tot_potenziale = 0
        dati_grafico = []

        for s in stanze_reali:
            try:
                df_s = conn.read(worksheet=s, ttl=0)
                if df_s is not None and not df_s.empty:
                    df_s.columns = [str(c).strip() for c in df_s.columns]
                    col_p = next((c for c in ['Importo Totale', 'Totale', 'Prezzo', 'Costo'] if c in df_s.columns), None)
                    col_s = next((c for c in ['Acquista S/N', 'S/N', 'Scelta', 'Acquista'] if c in df_s.columns), None)
                    col_o = next((c for c in ['Oggetto', 'Articolo', 'Descrizione', 'Nome'] if c in df_s.columns), df_s.columns[0])

                    if col_p:
                        df_s[col_p] = pd.to_numeric(df_s[col_p], errors='coerce').fillna(0)
                        tot_potenziale += df_s[col_p].sum()

                        if col_s:
                            df_s[col_s] = df_s[col_s].astype(str).str.strip().str.upper()
                            df_s_conf = df_s[df_s[col_s] == 'S'].copy()
                            if not df_s_conf.empty:
                                s_conf = df_s_conf[col_p].sum()
                                tot_conf += s_conf

                                temp_df = pd.DataFrame({
                                    'Ambiente': s.capitalize(),
                                    'Oggetto': df_s_conf[col_o].astype(str),
                                    'Importo': df_s_conf[col_p]
                                })
                                lista_completa.append(temp_df)
                                dati_grafico.append({"Stanza": s.capitalize(), "Spesa": s_conf})
            except: continue

        m1, m2, m3 = st.columns(3)
        m1.metric("CONFERMATO (S)", f"{tot_conf:,.2f} EUR")
        m2.metric("DA DECIDERE (N)", f"{(tot_potenziale - tot_conf):,.2f} EUR")
        m3.metric("BUDGET TOTALE", f"{tot_potenziale:,.2f} EUR")

        if lista_completa:
            df_final = pd.concat(lista_completa)
            st.write("### 📋 Dettaglio Acquisti Confermati")
            st.dataframe(df_final, use_container_width=True, hide_index=True)

            c1, c2 = st.columns([2, 1])
            with c1:
                df_plot = pd.DataFrame(dati_grafico)
                fig = px.pie(df_plot, values='Spesa', names='Stanza', title="Ripartizione Spese")
                st.plotly_chart(fig)

            with c2:
                st.write("#### Export")
                pdf = PDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 12)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(40, 10, 'Ambiente', 1, 0, 'C', True)
                pdf.cell(100, 10, 'Oggetto', 1, 0, 'C', True)
                pdf.cell(50, 10, 'Importo', 1, 1, 'C', True)

                pdf.set_font("Arial", '', 10)
                for _, row in df_final.iterrows():
                    # Pulizia testo per evitare errori Unicode
                    ogg_clean = str(row['Oggetto']).encode('latin-1', 'ignore').decode('latin-1')
                    amb_clean = str(row['Ambiente']).encode('latin-1', 'ignore').decode('latin-1')

                    pdf.cell(40, 8, amb_clean, 1)
                    pdf.cell(100, 8, ogg_clean[:50], 1)
                    # Sostituito € con EUR per evitare il crash
                    pdf.cell(50, 8, f"{row['Importo']:,.2f} EUR", 1, 1, 'R')

                pdf.ln(5)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(140, 10, 'TOTALE GENERALE', 0)
                pdf.cell(50, 10, f"{tot_conf:,.2f} EUR", 0, 1, 'R')

                pdf_output = pdf.output()
                st.download_button("📄 Scarica Report PDF", data=bytes(pdf_output), file_name="Report_Jacopo.pdf")
        else:
            st.warning("⚠️ Nessun oggetto contrassegnato con 'S'.")

    else:
        st.subheader(f"Ambiente: {selezione.capitalize()}")
        try:
            df = conn.read(worksheet=selezione, ttl=0)
            if df is not None:
                df.columns = [str(c).strip() for c in df.columns]
                col_s = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df.columns), None)
                config = {col_s: st.column_config.SelectboxColumn("Acquista?", options=["S", "N"])} if col_s else {}
                df_edit = st.data_editor(df, use_container_width=True, hide_index=True, column_config=config, key=f"ed_{selezione}")
                if st.button(f"💾 SALVA {selezione.upper()}"):
                    conn.update(worksheet=selezione, data=df_edit)
                    st.success("Dati aggiornati!")
                    st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")
