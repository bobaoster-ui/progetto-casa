import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento RC 1.2", layout="wide", page_icon="🏠")

# Palette Colori Professionale (Coordinata al Logo)
COLOR_PALETTE = ["#2E75B6", "#FFD700", "#1F4E78", "#F4B400", "#4472C4"]

# --- CLASSE PER IL PDF ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 20, 'REPORT SPESE ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 11)
        # Rispetto istruzione specifica: Proprietà con à
        testo_header = f'Proprietà: Jacopo - {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo_header.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}', align='C')

# --- FUNZIONE DI LOGIN ---
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
else:
    # Connessione a Google Sheets
    conn = st.connection("gsheets", type=GSheetsConnection)

    # --- SIDEBAR ---
    with st.sidebar:
        try:
            st.image("logo.png", width=180)
        except:
            st.image("https://cdn-icons-png.flaticon.com/512/619/619153.png", width=80)
        st.markdown("### Gestione Jacopo")
        st.divider()
        if st.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()

    stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]
    selezione = st.sidebar.selectbox("Menu Principale:", ["Riepilogo Generale", "✨ Wishlist"] + stanze_reali)

    # --- 1. RIEPILOGO GENERALE ---
    if selezione == "Riepilogo Generale":
        st.title("🏠 Dashboard Riepilogo")
        lista_solo_confermati = []
        tot_conf, tot_potenziale = 0, 0
        dati_per_grafico = []

        with st.spinner("Sincronizzazione dati in corso..."):
            for s in stanze_reali:
                try:
                    df_s = conn.read(worksheet=s, ttl=15)
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
        m1.metric("CONFERMATO (S)", f"{tot_conf:,.2f} EUR")
        m2.metric("RESIDUO (N)", f"{(tot_potenziale - tot_conf):,.2f} EUR")
        m3.metric("BUDGET TOTALE", f"{tot_potenziale:,.2f} EUR")

        if dati_per_grafico:
            df_plot = pd.DataFrame(dati_per_grafico)
            fig = px.pie(df_plot, values='Budget', names='Stanza', title="Ripartizione Budget per Ambiente", color_discrete_sequence=COLOR_PALETTE)
            fig.update_traces(textinfo='percent+label', hole=.4)
            st.plotly_chart(fig, use_container_width=True)

        if lista_solo_confermati:
            st.markdown("---")
            st.write("### 📋 Dettaglio Acquisti Confermati (S)")
            df_final = pd.concat(lista_solo_confermati)
            st.dataframe(df_final.style.format(subset=['Importo'], formatter="{:.2f} EUR"), use_container_width=True, hide_index=True)

            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(40, 10, 'Ambiente', 1)
            pdf.cell(100, 10, 'Oggetto', 1)
            pdf.cell(50, 10, 'Importo (EUR)', 1, 1)
            pdf.set_font("Arial", '', 9)
            for _, row in df_final.iterrows():
                ogg = str(row['Oggetto']).encode('latin-1', 'ignore').decode('latin-1')
                pdf.cell(40, 8, str(row['Ambiente']), 1)
                pdf.cell(100, 8, ogg[:50], 1)
                pdf.cell(50, 8, f"{row['Importo']:,.2f}", 1, 1, 'R')
            st.download_button("📄 Esporta Report PDF", data=bytes(pdf.output()), file_name="Report_Arredamento.pdf")

    # --- 2. WISHLIST ---
    elif selezione == "✨ Wishlist":
        st.title("✨ Lista dei Desideri")
        st.info("Gli oggetti inseriti qui non vengono conteggiati nel budget del Riepilogo Generale.")
        try:
            df_wish = conn.read(worksheet="desideri", ttl=20)
            if df_wish is None or df_wish.empty:
                df_wish = pd.DataFrame(columns=['Oggetto', 'Link', 'Prezzo Stimato', 'Note'])

            config_wish = {
                "Link": st.column_config.LinkColumn("🔗 Link Sito"),
                "Prezzo Stimato": st.column_config.NumberColumn("Prezzo Stimato (EUR)", format="%.2f EUR"),
                "Oggetto": st.column_config.TextColumn("Nome Oggetto"),
                "Note": st.column_config.TextColumn("Dettagli")
            }

            df_edit_wish = st.data_editor(df_wish, use_container_width=True, hide_index=True, num_rows="dynamic", column_config=config_wish, key="wish_stable")

            if st.button("💾 SALVA WISHLIST"):
                with st.spinner("Salvataggio..."):
                    conn.update(worksheet="wishlist", data=df_edit_wish)
                st.success("Lista desideri aggiornata!")
                st.balloons()
        except Exception as e:
            st.error("Il foglio 'wishlist' non risponde o Google Sheets è occupato. Attendi un momento.")

    # --- 3. STANZE SINGOLE ---
    else:
        st.title(f"🏠 Gestione {selezione.capitalize()}")
        try:
            df = conn.read(worksheet=selezione, ttl=10)
            if df is not None:
                df.columns = [str(c).strip() for c in df.columns]
                col_s = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df.columns), None)
                config = {col_s: st.column_config.SelectboxColumn("Acquista?", options=["S", "N"])} if col_s else {}
                df_edit = st.data_editor(df, use_container_width=True, hide_index=True, column_config=config, num_rows="dynamic", key=f"ed_{selezione}")

                c1, c2 = st.columns([1, 4])
                if c1.button("💾 SALVA"):
                    with st.spinner("Aggiornamento Google Sheets..."):
                        conn.update(worksheet=selezione, data=df_edit)
                    st.success(f"Dati di {selezione} salvati correttamente!")
                    st.balloons()
                if c2.button("Aggiorna Vista 🔄"): st.rerun()
        except Exception as e:
            st.error(f"Google Sheets è momentaneamente occupato. Riprova tra 60 secondi.")
