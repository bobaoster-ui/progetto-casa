import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento V7.2", layout="wide", page_icon="🏠")

# Palette Colori
COLOR_PALETTE = ["#2E75B6", "#FFD700", "#1F4E78", "#F4B400", "#4472C4"]

# --- CLASSE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 20, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 11)
        testo_header = f'Proprietà: Jacopo - {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo_header.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}', align='C')

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

        for s in stanze_reali:
            try:
                df_s = conn.read(worksheet=s, ttl=0)
                if df_s is not None and not df_s.empty:
                    df_s = safe_clean_df(df_s)
                    col_s = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df_s.columns), 'Acquista S/N')

                    # Calcolo budget per stanza (Tutto ciò che ha un Importo Totale)
                    imp_stanza = df_s['Importo Totale'].sum()
                    if imp_stanza > 0:
                        dati_per_grafico.append({"Stanza": s.capitalize(), "Budget": imp_stanza})

                    # Filtraggio confermati (S)
                    conf_mask = df_s[col_s].astype(str).str.upper() == 'S'
                    df_c = df_s[conf_mask].copy()
                    if not df_c.empty:
                        tot_conf += df_c['Importo Totale'].sum()
                        tot_versato += df_c['Versato'].sum()
                        col_o = next((c for c in ['Oggetto', 'Articolo'] if c in df_c.columns), df_c.columns[0])
                        temp_df = pd.DataFrame({
                            'Ambiente': s.capitalize(),
                            'Oggetto': df_c[col_o],
                            'Importo Totale': df_c['Importo Totale'],
                            'Versato': df_c['Versato'],
                            'Stato': df_c['Stato Pagamento'] if 'Stato Pagamento' in df_c.columns else "-"
                        })
                        lista_dettaglio.append(temp_df)
            except Exception as e:
                st.warning(f"Errore caricamento {s}: {e}")

        # Visualizzazione Metriche
        st.subheader(f"📊 Budget Totale: {budget_max:,.2f} €")
        perc = min(tot_conf / budget_max, 1.2) if budget_max > 0 else 0
        st.progress(perc)

        m1, m2, m3 = st.columns(3)
        m1.metric("CONFERMATO (S)", f"{tot_conf:,.2f} €")
        m2.metric("RESIDUO BUDGET", f"{(budget_max - tot_conf):,.2f} €")
        m3.metric("% UTILIZZO", f"{perc:.1%}")

        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("IMPEGNATO", f"{tot_conf:,.2f} €")
        c2.metric("PAGATO", f"{tot_versato:,.2f} €")
        res_p = tot_conf - tot_versato
        c3.metric("DA SALDARE", f"{res_p:,.2f} €", delta=f"-{res_p:,.2f}", delta_color="inverse")

        # Grafici
        g1, g2 = st.columns(2)
        with g1:
            if dati_per_grafico:
                fig_pie = px.pie(pd.DataFrame(dati_per_grafico), values='Budget', names='Stanza', title="Spesa Totale per Stanza", hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
        with g2:
            df_bar = pd.DataFrame({"Tipo": ["Pagato", "Da Saldare"], "Euro": [tot_versato, max(0, res_p)]})
            fig_bar = px.bar(df_bar, x="Tipo", y="Euro", color="Tipo", color_discrete_map={"Pagato": "#2ECC71", "Da Saldare": "#E74C3C"})
            st.plotly_chart(fig_bar, use_container_width=True)

        if lista_dettaglio:
            df_final = pd.concat(lista_dettaglio)
            st.subheader("📝 Dettaglio Pagamenti")
            st.dataframe(df_final, use_container_width=True, hide_index=True)

            if st.button("📄 Genera Report PDF"):
                pdf = PDF(); pdf.add_page()
                pdf.set_font("Arial", 'B', 8); pdf.set_fill_color(230, 230, 230)
                # Intestazione Tabella
                pdf.cell(30, 10, 'Ambiente', 1, 0, 'C', True); pdf.cell(60, 10, 'Oggetto', 1, 0, 'C', True)
                pdf.cell(35, 10, 'Totale', 1, 0, 'C', True); pdf.cell(35, 10, 'Versato', 1, 0, 'C', True)
                pdf.cell(30, 10, 'Stato', 1, 1, 'C', True)
                pdf.set_font("Arial", '', 8)
                for _, row in df_final.iterrows():
                    y_i = pdf.get_y(); x_i = pdf.get_x()
                    pdf.set_xy(x_i + 30, y_i)
                    pdf.multi_cell(60, 5, str(row['Oggetto']).encode('latin-1', 'replace').decode('latin-1'), 1)
                    h = max(10, pdf.get_y() - y_i)
                    pdf.set_xy(x_i, y_i); pdf.cell(30, h, str(row['Ambiente']), 1)
                    pdf.set_xy(x_i + 90, y_i); pdf.cell(35, h, f"{row['Importo Totale']:,.2f}", 1, 0, 'R')
                    pdf.cell(35, h, f"{row['Versato']:,.2f}", 1, 0, 'R'); pdf.cell(30, h, str(row['Stato']), 1, 1, 'C')
                st.download_button("📩 Scarica Report", data=bytes(pdf.output()), file_name="Estratto_Conto_Arredamento.pdf")

    # --- 2. STANZE ---
    elif selezione in stanze_reali:
        st.title(f"🏠 {selezione.capitalize()}")
        df_raw = conn.read(worksheet=selezione, ttl=0)
        df = safe_clean_df(df_raw)

        config = {
            "Acquista S/N": st.column_config.SelectboxColumn("Scelta", options=["S", "N"]),
            "Stato Pagamento": st.column_config.SelectboxColumn("Stato", options=["Da Pagare", "Acconto", "Saldato"]),
            "Importo Totale": st.column_config.NumberColumn("Totale €", format="%.2f", disabled=True),
            "Link Fattura": st.column_config.LinkColumn("🔗 Doc", display_text="Vedi")
        }

        # Form per blindare il ricalcolo
        with st.form(key=f"form_{selezione}"):
            df_edit = st.data_editor(
                df,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic" if can_edit_structure else "fixed",
                column_config=config
            )
            submit = st.form_submit_button("💾 SALVA E CALCOLA")

        if submit:
            with st.spinner("Aggiornamento Proprietà..."):
                # Ricalcolo rigoroso
                for i in range(len(df_edit)):
                    try:
                        pp = float(df_edit.at[i, 'Prezzo Pieno'])
                        sc = float(df_edit.at[i, 'Sconto %'])
                        qta = float(df_edit.at[i, 'Acquistato'])
                        if pp > 0:
                            costo = pp * (1 - (sc / 100))
                            df_edit.at[i, 'Costo'] = costo
                        else:
                            costo = float(df_edit.at[i, 'Costo'])

                        totale = costo * qta
                        df_edit.at[i, 'Importo Totale'] = totale

                        if str(df_edit.at[i, 'Stato Pagamento']) == "Saldato":
                            df_edit.at[i, 'Versato'] = totale
                    except: continue

                conn.update(worksheet=selezione, data=df_edit)
                st.session_state["saved_success"] = True # Segnale per palloncini
                st.rerun()

        # Visualizzazione successo (fuori dal form)
        if st.session_state.get("saved_success"):
            st.balloons()
            st.success("Dati ricalcolati e salvati con successo!")
            del st.session_state["saved_success"]

    # --- 3. WISHLIST ---
    elif selezione == "✨ Wishlist":
        st.title("✨ Wishlist")
        df_wish = conn.read(worksheet="desideri", ttl=0)
        if df_wish is not None:
            df_wish = safe_clean_df(df_wish)
            df_disp = df_wish.copy()
            df_disp['Anteprima'] = df_disp['Foto']
            df_edit_w = st.data_editor(df_disp, use_container_width=True, hide_index=True,
                                       num_rows="dynamic" if can_edit_structure else "fixed",
                                       column_config={"Anteprima": st.column_config.ImageColumn("Preview")})
            if st.button("💾 SALVA WISHLIST"):
                conn.update(worksheet="desideri", data=df_edit_w.drop(columns=['Anteprima']))
                st.success("Salva!"); time.sleep(1); st.rerun()
