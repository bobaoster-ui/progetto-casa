import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime
from fpdf import FPDF

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento v2.9", layout="wide", page_icon="🏠")

# --- CLASSE PER IL PDF ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(0, 20, 'REPORT SPESE ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 12)
        self.cell(0, 10, f'Proprietà: Jacopo - {datetime.now().strftime("%d/%m/%Y")}', ln=True, align='C')
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
        lista_solo_confermati = []
        tot_conf = 0
        tot_potenziale = 0
        dati_per_grafico_totale = []

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
                        spesa_stanza_totale = df_s[col_p].sum()
                        tot_potenziale += spesa_stanza_totale

                        # Dati per il grafico (sempre presenti, S + N)
                        dati_per_grafico_totale.append({"Stanza": s.capitalize(), "Budget": spesa_stanza_totale})

                        if col_s:
                            df_s[col_s] = df_s[col_s].astype(str).str.strip().str.upper()
                            df_s_conf = df_s[df_s[col_s] == 'S'].copy()
                            if not df_s_conf.empty:
                                tot_conf += df_s_conf[col_p].sum()
                                temp_df = pd.DataFrame({
                                    'Ambiente': s.capitalize(),
                                    'Oggetto': df_s_conf[col_o].astype(str),
                                    'Importo': df_s_conf[col_p]
                                })
                                lista_solo_confermati.append(temp_df)
            except: continue

        # Visualizzazione Metriche
        m1, m2, m3 = st.columns(3)
        m1.metric("CONFERMATO (S)", f"{tot_conf:,.2f} EUR")
        m2.metric("DA DECIDERE (N)", f"{(tot_potenziale - tot_conf):,.2f} EUR")
        m3.metric("BUDGET TOTALE (S+N)", f"{tot_potenziale:,.2f} EUR")

        # GRAFICI (Sempre visibili se ci sono dati)
        if dati_per_grafico_totale:
            st.write("### 📊 Analisi Budget per Stanza (S + N)")
            df_plot = pd.DataFrame(dati_per_grafico_totale)
            fig = px.bar(df_plot, x='Stanza', y='Budget', color='Stanza', title="Potenziale di spesa totale")
            st.plotly_chart(fig, use_container_width=True)

        # TABELLA E PDF (Solo se ci sono "S")
        if lista_solo_confermati:
            st.write("### 📋 Dettaglio Acquisti Confermati (S)")
            df_final = pd.concat(lista_solo_confermati)
            st.dataframe(df_final, use_container_width=True, hide_index=True)

            # Export PDF
            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(40, 10, 'Ambiente', 1, 0, 'C', True)
            pdf.cell(100, 10, 'Oggetto', 1, 0, 'C', True)
            pdf.cell(50, 10, 'Importo', 1, 1, 'C', True)

            pdf.set_font("Arial", '', 10)
            for _, row in df_final.iterrows():
                ogg_clean = str(row['Oggetto']).encode('latin-1', 'ignore').decode('latin-1')
                amb_clean = str(row['Ambiente']).encode('latin-1', 'ignore').decode('latin-1')
                pdf.cell(40, 8, amb_clean, 1)
                pdf.cell(100, 8, ogg_clean[:50], 1)
                pdf.cell(50, 8, f"{row['Importo']:,.2f} EUR", 1, 1, 'R')

            pdf_output = pdf.output()
            st.download_button("📄 Scarica Report PDF (Solo S)", data=bytes(pdf_output), file_name="Report_Jacopo.pdf")
        else:
            st.info("💡 Suggerimento: Per generare il PDF e la tabella di dettaglio, imposta 'S' nella colonna Acquista delle singole stanze.")

    else:
        # STANZA SINGOLA (Codice invariato e stabile)
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
                    st.success("Dati salvati!")
                    st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")
