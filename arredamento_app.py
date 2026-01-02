import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF

# 1. CONFIGURAZIONE PAGINA (Release Candidate)
st.set_page_config(page_title="Monitoraggio Arredamento RC1", layout="wide", page_icon="🏠")

# Palette Colori coordinata al Logo (Blu Professionale e Oro)
COLOR_PALETTE = ["#2E75B6", "#FFD700", "#1F4E78", "#F4B400", "#4472C4"]

# --- CLASSE PER IL PDF ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(0, 20, 'REPORT SPESE ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 12)
        # Rispetto della Proprietà con accento (à)
        testo_header = f'Proprietà: Jacopo - {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo_header.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}', align='C')

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
        try:
            st.image("logo.png", width=200)
        except:
            st.image("https://cdn-icons-png.flaticon.com/512/619/619153.png", width=80)
        st.markdown("### Gestione Jacopo")
        st.divider()
        if st.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()

    stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]
    selezione = st.sidebar.selectbox("Naviga tra le stanze:", ["Riepilogo Generale"] + stanze_reali)

    if selezione == "Riepilogo Generale":
        st.title("🏠 Dashboard Riepilogo")
        lista_solo_confermati = []
        tot_conf, tot_potenziale = 0, 0
        dati_per_grafico = []

        with st.spinner("Analisi budget in corso..."):
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
                            v = df_s[col_p].sum()
                            tot_potenziale += v
                            dati_per_grafico.append({"Stanza": s.capitalize(), "Budget": v})

                            if col_s:
                                df_s[col_s] = df_s[col_s].astype(str).str.strip().str.upper()
                                df_s_c = df_s[df_s[col_s] == 'S'].copy()
                                if not df_s_c.empty:
                                    tot_conf += df_s_c[col_p].sum()
                                    temp_df = pd.DataFrame({'Ambiente': s.capitalize(), 'Oggetto': df_s_c[col_o].astype(str), 'Importo': df_s_c[col_p]})
                                    lista_solo_confermati.append(temp_df)
                except: continue

        m1, m2, m3 = st.columns(3)
        # Stile migliorato per le metriche
        m1.metric("CONFERMATO (S)", f"{tot_conf:,.2f} EUR")
        m2.metric("RESIDUO (N)", f"{(tot_potenziale - tot_conf):,.2f} EUR")
        m3.metric("BUDGET TOTALE", f"{tot_potenziale:,.2f} EUR")

        if dati_per_grafico:
            df_plot = pd.DataFrame(dati_per_grafico)
            fig = px.pie(df_plot, values='Budget', names='Stanza',
                         title="Ripartizione Budget tra gli Ambienti",
                         color_discrete_sequence=COLOR_PALETTE)
            fig.update_traces(textinfo='percent+label', hole=.3) # Grafico a ciambella più moderno
            st.plotly_chart(fig, use_container_width=True)

        if lista_solo_confermati:
            st.markdown("---")
            st.write("### 📋 Dettaglio Acquisti Confermati")
            df_final = pd.concat(lista_solo_confermati)
            st.dataframe(df_final.style.format(subset=['Importo'], formatter="{:.2f} EUR"), use_container_width=True, hide_index=True)

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

            st.download_button("📄 Esporta Report PDF", data=bytes(pdf.output()), file_name="Report_Jacopo_Finale.pdf")

    else:
        st.title(f"🏠 Gestione {selezione.capitalize()}")
        try:
            df = conn.read(worksheet=selezione, ttl=0)
            if df is not None:
                df.columns = [str(c).strip() for c in df.columns]
                col_s = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df.columns), None)
                config = {col_s: st.column_config.SelectboxColumn("Acquista?", options=["S", "N"])} if col_s else {}
                df_edit = st.data_editor(df, use_container_width=True, hide_index=True, column_config=config, num_rows="dynamic", key=f"ed_{selezione}")

                c1, c2 = st.columns([1, 4])
                if c1.button("💾 SALVA"):
                    with st.spinner("Invio..."): conn.update(worksheet=selezione, data=df_edit)
                    st.success("Dati aggiornati!")
                    st.balloons()
                if c2.button("Aggiorna 🔄"): st.rerun()
        except Exception as e: st.error(f"Errore: {e}")
