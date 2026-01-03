import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento V6.3", layout="wide", page_icon="🏠")

# Palette Colori Professionale
COLOR_PALETTE = ["#2E75B6", "#FFD700", "#1F4E78", "#F4B400", "#4472C4"]

# --- CLASSE PER IL PDF AGGIORNATA ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(46, 117, 182)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 20, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 11)
        # Regola fissa richiesta: Proprietà con à
        testo_header = f'Proprietà: Jacopo - {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo_header.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}', align='C')

# --- LOGIN ---
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
    conn = st.connection("gsheets", type=GSheetsConnection)

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

    # --- 1. RIEPILOGO GENERALE (DASHBOARD FINANZIARIA) ---
    if selezione == "Riepilogo Generale":
        st.title("🏠 Dashboard Riepilogo")
        try:
            df_imp = conn.read(worksheet="impostazioni", ttl="5s")
            budget_max = float(df_imp[df_imp['Parametro'] == 'Budget Totale']['Valore'].values[0])
        except: budget_max = 10000.0

        lista_dettaglio = []
        tot_conf, tot_versato = 0, 0
        dati_per_grafico = []

        for s in stanze_reali:
            try:
                df_s = conn.read(worksheet=s, ttl="5s")
                if df_s is not None and not df_s.empty:
                    df_s.columns = [str(c).strip() for c in df_s.columns]
                    col_s = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df_s.columns), 'Acquista S/N')

                    # Filtriamo solo i confermati "S" per il budget e i pagamenti
                    conf_mask = df_s[col_s].astype(str).str.upper() == 'S'
                    df_c = df_s[conf_mask].copy()

                    # Calcolo spesa totale per stanza (indipendente dalla scelta S/N per il grafico)
                    importo_stanza = pd.to_numeric(df_s['Importo Totale'], errors='coerce').fillna(0).sum()
                    if importo_stanza > 0:
                        dati_per_grafico.append({"Stanza": s.capitalize(), "Budget": importo_stanza})

                    if not df_c.empty:
                        df_c['Ambiente'] = s.capitalize()
                        df_c['Importo Totale'] = pd.to_numeric(df_c['Importo Totale'], errors='coerce').fillna(0)
                        df_c['Versato'] = pd.to_numeric(df_c['Versato'], errors='coerce').fillna(0)

                        tot_conf += df_c['Importo Totale'].sum()
                        tot_versato += df_c['Versato'].sum()

                        col_o = next((c for c in ['Oggetto', 'Articolo'] if c in df_c.columns), df_c.columns[0])
                        col_stat = 'Stato Pagamento' if 'Stato Pagamento' in df_c.columns else None

                        temp_df = df_c[['Ambiente', col_o, 'Importo Totale', 'Versato']].copy()
                        temp_df.rename(columns={col_o: 'Oggetto'}, inplace=True)
                        temp_df['Stato'] = df_c[col_stat] if col_stat else "-"
                        lista_dettaglio.append(temp_df)
            except: continue

        # Visualizzazione Metriche
        st.subheader(f"📊 Stato del Budget (Limite: {budget_max:,.2f} €)")
        percentuale = min(tot_conf / budget_max, 1.2)
        st.progress(percentuale)

        m1, m2, m3 = st.columns(3)
        m1.metric("CONFERMATO (S)", f"{tot_conf:,.2f} €")
        m2.metric("RESIDUO BUDGET", f"{(budget_max - tot_conf):,.2f} €")
        m3.metric("% SPESA", f"{percentuale:.1%}")

        st.divider()
        st.subheader("💳 Analisi Pagamenti (Cash Flow)")
        c1, c2, c3 = st.columns(3)
        c1.metric("TOTALE IMPEGNATO", f"{tot_conf:,.2f} €")
        c2.metric("GIÀ VERSATO", f"{tot_versato:,.2f} €")
        residuo_paga = tot_conf - tot_versato
        c3.metric("RESIDUO DA SALDARE", f"{residuo_paga:,.2f} €", delta=f"-{residuo_paga:,.2f}", delta_color="inverse")

        col_left, col_right = st.columns(2)
        with col_left:
            if dati_per_grafico:
                fig_pie = px.pie(pd.DataFrame(dati_per_grafico), values='Budget', names='Stanza', title="Ripartizione Spese", hole=0.4, color_discrete_sequence=COLOR_PALETTE)
                st.plotly_chart(fig_pie, use_container_width=True)
        with col_right:
            df_cash_plot = pd.DataFrame({"Stato": ["Versato", "Residuo"], "Euro": [tot_versato, max(0, residuo_paga)]})
            fig_bar = px.bar(df_cash_plot, x="Stato", y="Euro", color="Stato", color_discrete_map={"Versato": "#2ECC71", "Residuo": "#E74C3C"}, title="Copertura Pagamenti")
            st.plotly_chart(fig_bar, use_container_width=True)

        if lista_dettaglio:
            df_final = pd.concat(lista_dettaglio)
            st.subheader("📝 Dettaglio Pagamenti Confermati")
            st.dataframe(df_final, use_container_width=True, hide_index=True)

            # PDF GENERATION
            pdf = PDF()
# --- TABELLA PDF CON TESTO A CAPO ---
            pdf.cell(30, 10, 'Ambiente', 1, 0, 'C', True)
            pdf.cell(60, 10, 'Oggetto', 1, 0, 'C', True)
            pdf.cell(35, 10, 'Importo Tot.', 1, 0, 'C', True)
            pdf.cell(35, 10, 'Versato', 1, 0, 'C', True)
            pdf.cell(30, 10, 'Stato', 1, 1, 'C', True)

            pdf.set_font("Arial", '', 8)
            for _, row in df_final.iterrows():
                # Memorizziamo la posizione Y iniziale della riga
                y_inizio = pdf.get_y()
                x_inizio = pdf.get_x()

                # 1. Scriviamo l'Oggetto con MultiCell (che può andare a capo)
                # Spostiamoci alla X della seconda colonna (30)
                pdf.set_xy(x_inizio + 30, y_inizio)
                pdf.multi_cell(60, 5, str(row['Oggetto']).encode('latin-1', 'replace').decode('latin-1'), 1)

                # Calcoliamo quanto è diventata alta la cella dell'oggetto
                y_fine = pdf.get_y()
                altezza_riga = y_fine - y_inizio

                # 2. Torniamo all'inizio della riga per disegnare le altre celle con l'altezza calcolata
                pdf.set_xy(x_inizio, y_inizio)
                pdf.cell(30, altezza_riga, str(row['Ambiente']), 1)

                # Saltiamo la colonna oggetto (già scritta) e facciamo le altre
                pdf.set_xy(x_inizio + 90, y_inizio)
                pdf.cell(35, altezza_riga, f"{row['Importo Totale']:,.2f}", 1, 0, 'R')
                pdf.cell(35, altezza_riga, f"{row['Versato']:,.2f}", 1, 0, 'R')
                pdf.cell(30, altezza_riga, str(row['Stato']), 1, 1, 'C')

            pdf.ln(5)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(125, 10, 'TOTALE IMPEGNATO (S)', 0, 0, 'R')
            pdf.cell(65, 10, f"{tot_conf:,.2f} EUR", 0, 1, 'R')
            pdf.cell(125, 10, 'TOTALE GIÀ VERSATO', 0, 0, 'R')
            pdf.set_text_color(0, 128, 0)
            pdf.cell(65, 10, f"{tot_versato:,.2f} EUR", 0, 1, 'R')

            st.download_button("📄 Scarica Estratto Conto PDF", data=bytes(pdf.output()), file_name="Estratto_Conto_Jacopo.pdf")

    # --- 2. WISHLIST ---
    elif selezione == "✨ Wishlist":
        st.title("✨ Wishlist Visiva")
        df_wish = conn.read(worksheet="desideri", ttl="5s")
        if df_wish is not None:
            df_wish.columns = [str(c).strip() for c in df_wish.columns]
            for col in ['Oggetto', 'Note', 'Foto']:
                if col in df_wish.columns: df_wish[col] = df_wish[col].astype(str).replace('nan', '')

            df_display = df_wish.copy()
            df_display['Anteprima'] = df_display['Foto']
            cols_order = ['Oggetto', 'Anteprima', 'Prezzo Stimato', 'Link', 'Note', 'Foto']
            df_display = df_display[[c for c in cols_order if c in df_display.columns]]

            config_wish = {
                "Anteprima": st.column_config.ImageColumn("Preview", width="medium"),
                "Link": st.column_config.LinkColumn("🔗 Link", display_text="Apri"),
                "Note": st.column_config.TextColumn("Note", width="large"),
                "Prezzo Stimato": st.column_config.NumberColumn("Budget €", format="%.2f"),
            }
            df_edit_wish = st.data_editor(df_display, use_container_width=True, hide_index=True, num_rows="dynamic", column_config=config_wish, key="wish_v6_3")

            if st.button("💾 SALVA WISHLIST"):
                df_to_save = df_edit_wish.drop(columns=['Anteprima'])
                conn.update(worksheet="desideri", data=df_to_save)
                st.balloons()
                st.success("Wishlist salvata!")
                time.sleep(1)
                st.rerun()

    # --- 3. STANZE ---
    else:
        st.title(f"🏠 {selezione.capitalize()}")
        df = conn.read(worksheet=selezione, ttl="5s")
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.columns:
                if col not in ['Prezzo Pieno', 'Sconto %', 'Costo', 'Importo Totale', 'Acquistato', 'Versato']:
                    df[col] = df[col].astype(str).replace('nan', '')

            config_stanza = {
                "Acquista S/N": st.column_config.SelectboxColumn("Scelta", options=["S", "N"]),
                "Stato Pagamento": st.column_config.SelectboxColumn("Stato", options=["Da Pagare", "Acconto", "Saldato"]),
                "Prezzo Pieno": st.column_config.NumberColumn("Listino €", format="%.2f"),
                "Sconto %": st.column_config.NumberColumn("Sconto %"),
                "Costo": st.column_config.NumberColumn("Costo Unit. €", format="%.2f"),
                "Acquistato": st.column_config.NumberColumn("Quantità", format="%.2f", step=0.1),
                "Importo Totale": st.column_config.NumberColumn("Totale Riga €", format="%.2f", disabled=True),
                "Versato": st.column_config.NumberColumn("Versato €", format="%.2f"),
                "Link Fattura": st.column_config.LinkColumn("🔗 Doc", display_text="Vedi"),
                "Note": st.column_config.TextColumn("Note", width="large")
            }

            df_edit = st.data_editor(df, use_container_width=True, hide_index=True, num_rows="dynamic", column_config=config_stanza, key=f"ed_{selezione}")

            if st.button("💾 SALVA E RICALCOLA"):
                with st.spinner("Calcolo in corso..."):
                    # Trasformazione numerica rigorosa
                    for col in ['Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo', 'Versato']:
                        df_edit[col] = pd.to_numeric(df_edit[col], errors='coerce').fillna(0)

                    for i in range(len(df_edit)):
                        # Logica Sconto -> Costo
                        if df_edit.at[i, 'Prezzo Pieno'] > 0:
                            df_edit.at[i, 'Costo'] = df_edit.at[i, 'Prezzo Pieno'] * (1 - (df_edit.at[i, 'Sconto %'] / 100))

                        # Logica Quantità -> Totale
                        it = df_edit.at[i, 'Costo'] * df_edit.at[i, 'Acquistato']
                        df_edit.at[i, 'Importo Totale'] = it

                        # Automazione "Saldato"
                        if df_edit.at[i, 'Stato Pagamento'] == "Saldato":
                            df_edit.at[i, 'Versato'] = it

                    conn.update(worksheet=selezione, data=df_edit)
                    st.balloons()
                    st.success("Tutto salvato!")
                    time.sleep(1)
                    st.rerun()
