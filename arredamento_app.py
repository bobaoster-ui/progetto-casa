import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime
from fpdf import FPDF

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento v2.6", layout="wide", page_icon="🏠")

# --- CLASSE PER IL PDF ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 20)
        self.set_text_color(255, 255, 255)
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

                    # Identificazione colonne flessibile
                    col_p = next((c for c in ['Importo Totale', 'Totale', 'Prezzo', 'Costo'] if c in df_s.columns), None)
                    col_s = next((c for c in ['Acquista S/N', 'S/N', 'Scelta', 'Acquista'] if c in df_s.columns), None)

                    if col_p:
                        df_s[col_p] = pd.to_numeric(df_s[col_p], errors='coerce').fillna(0)
                        s_pot = df_s[col_p].sum()
                        tot_potenziale += s_pot

                        s_conf = 0
                        if col_s:
                            # Pulizia della colonna S/N (toglie spazi e rende maiuscolo)
                            df_s[col_s] = df_s[col_s].astype(str).str.strip().str.upper()
                            df_s_conf = df_s[df_s[col_s] == 'S'].copy()
                            if not df_s_conf.empty:
                                s_conf = df_s_conf[col_p].sum()
                                tot_conf += s_conf
                                df_s_conf['Ambiente'] = s.capitalize()
                                lista_completa.append(df_s_conf[['Ambiente', 'Oggetto', col_p]])

                        dati_grafico.append({"Stanza": s.capitalize(), "Spesa": s_conf})
            except: continue

        # Metriche in primo piano
        c1, c2 = st.columns(2)
        c1.metric("TOTALE CONFERMATO (S)", f"{tot_conf:,.2f} €")
        c2.metric("BUDGET TOTALE (S+N)", f"{tot_potenziale:,.2f} €")

        if lista_completa:
            df_final = pd.concat(lista_completa)
            st.write("### Dettaglio oggetti confermati")
            st.dataframe(df_final, use_container_width=True, hide_index=True)

            # Grafico
            df_plot = pd.DataFrame(dati_grafico)
            fig = px.pie(df_plot, values='Spesa', names='Stanza', title="Distribuzione Spese Confermate")
            st.plotly_chart(fig)

            # --- GENERAZIONE PDF ---
            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(40, 10, 'Ambiente', 1, 0, 'C', True)
            pdf.cell(100, 10, 'Oggetto', 1, 0, 'C', True)
            pdf.cell(50, 10, 'Importo', 1, 1, 'C', True)

            pdf.set_font("Arial", '', 10)
            for _, row in df_final.iterrows():
                pdf.cell(40, 8, str(row['Ambiente']), 1)
                pdf.cell(100, 8, str(row['Oggetto'])[:50], 1)
                pdf.cell(50, 8, f"{row.iloc[2]:,.2f} EUR", 1, 1, 'R')

            pdf_output = pdf.output()
            st.sidebar.download_button("📄 Scarica Report PDF", data=bytes(pdf_output), file_name="Report_Jacopo.pdf")
        else:
            st.info("Nessun oggetto con 'S' trovato. Controlla che la colonna S/N contenga solo la lettera S.")

    else:
        # STANZA SINGOLA
        st.subheader(f"Ambiente: {selezione.capitalize()}")
        try:
            df = conn.read(worksheet=selezione, ttl=0)
            if df is not None:
                df.columns = [str(c).strip() for c in df.columns]
                col_scelta = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df.columns), None)

                # Ripristiniamo il menu a tendina S/N nell'editor
                config = {}
                if col_scelta:
                    config[col_scelta] = st.column_config.SelectboxColumn("Acquista?", options=["S", "N"])

                df_edit = st.data_editor(df, use_container_width=True, hide_index=True, column_config=config, key=f"ed_{selezione}")

                if st.button(f"💾 SALVA {selezione.upper()}"):
                    conn.update(worksheet=selezione, data=df_edit)
                    st.success("Dati aggiornati!")
                    st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")
