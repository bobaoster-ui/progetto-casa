import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento V6.2", layout="wide", page_icon="🏠")

# Palette Colori Professionale
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
        # Regola fissa: Proprietà con à
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

    # --- 1. RIEPILOGO GENERALE ---
    if selezione == "Riepilogo Generale":
        st.title("🏠 Dashboard Riepilogo")
        try:
            df_imp = conn.read(worksheet="impostazioni", ttl="5s")
            budget_max = float(df_imp[df_imp['Parametro'] == 'Budget Totale']['Valore'].values[0])
        except:
            budget_max = 10000.0

        lista_solo_confermati = []
        tot_conf, tot_versato = 0, 0
        dati_per_grafico = []

        for s in stanze_reali:
            try:
                df_s = conn.read(worksheet=s, ttl="5s")
                if df_s is not None and not df_s.empty:
                    df_s.columns = [str(c).strip() for c in df_s.columns]
                    col_p = 'Importo Totale'
                    col_s = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df_s.columns), 'Acquista S/N')

                    if col_p in df_s.columns:
                        df_s[col_p] = pd.to_numeric(df_s[col_p], errors='coerce').fillna(0)
                        val_s = df_s[col_p].sum()
                        if val_s > 0: dati_per_grafico.append({"Stanza": s.capitalize(), "Budget": val_s})

                        # Calcolo Confermati (S)
                        conf_mask = df_s[col_s].astype(str).str.upper() == 'S'
                        tot_conf += df_s.loc[conf_mask, col_p].sum()

                        # Calcolo Versato
                        if 'Versato' in df_s.columns:
                            tot_versato += pd.to_numeric(df_s['Versato'], errors='coerce').fillna(0).sum()

                        # Dettaglio per tabella
                        df_s_c = df_s[conf_mask].copy()
                        if not df_s_c.empty:
                            col_o = next((c for c in ['Oggetto', 'Articolo', 'Descrizione'] if c in df_s.columns), df_s.columns[0])
                            temp_df = pd.DataFrame({'Ambiente': s.capitalize(), 'Oggetto': df_s_c[col_o].astype(str), 'Importo': df_s_c[col_p]})
                            lista_solo_confermati.append(temp_df)
            except: continue

        # Budget Alert
        percentuale = min(tot_conf / budget_max, 1.2)
        st.subheader(f"📊 Stato del Budget (Target: {budget_max:,.2f} €)")
        st.progress(percentuale)

        m1, m2, m3 = st.columns(3)
        m1.metric("CONFERMATO (S)", f"{tot_conf:,.2f} €")
        m2.metric("RESIDUO BUDGET", f"{(budget_max - tot_conf):,.2f} €")
        m3.metric("% UTILIZZATA", f"{percentuale:.1%}")

        # Cash Flow Analysis
        st.divider()
        st.subheader("💳 Analisi Pagamenti")
        c1, c2, c3 = st.columns(3)
        c1.metric("DA VERSARE (Tot. S)", f"{tot_conf:,.2f} €")
        c2.metric("GIÀ VERSATO", f"{tot_versato:,.2f} €")
        residuo_pagamento = tot_conf - tot_versato
        c3.metric("RESIDUO DA SALDARE", f"{residuo_pagamento:,.2f} €", delta=f"-{residuo_pagamento:,.2f}", delta_color="inverse")

        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            if dati_per_grafico:
                fig_pie = px.pie(pd.DataFrame(dati_per_grafico), values='Budget', names='Stanza', title="Spesa per Stanza", hole=0.4, color_discrete_sequence=COLOR_PALETTE)
                st.plotly_chart(fig_pie, use_container_width=True)
        with col_graf2:
            df_cash_plot = pd.DataFrame({"Stato": ["Versato", "Residuo"], "Euro": [tot_versato, max(0, residuo_pagamento)]})
            fig_bar = px.bar(df_cash_plot, x="Stato", y="Euro", color="Stato", color_discrete_map={"Versato": "#2ECC71", "Residuo": "#E74C3C"}, title="Copertura Pagamenti")
            st.plotly_chart(fig_bar, use_container_width=True)

        if lista_solo_confermati:
            st.subheader("📝 Dettaglio Acquisti Confermati")
            df_final = pd.concat(lista_solo_confermati)
            st.dataframe(df_final, use_container_width=True, hide_index=True)

            # PDF Generation
            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(40, 10, 'Ambiente', 1, 0, 'C', True)
            pdf.cell(100, 10, 'Oggetto', 1, 0, 'C', True)
            pdf.cell(50, 10, 'Importo (EUR)', 1, 1, 'C', True)
            pdf.set_font("Arial", '', 9)
            for _, row in df_final.iterrows():
                pdf.cell(40, 8, str(row['Ambiente']).encode('latin-1', 'replace').decode('latin-1'), 1)
                pdf.cell(100, 8, str(row['Oggetto']).encode('latin-1', 'replace').decode('latin-1')[:55], 1)
                pdf.cell(50, 8, f"{row['Importo']:,.2f}", 1, 1, 'R')
            pdf.cell(140, 10, 'TOTALE CONFERMATO', 1, 0, 'R')
            pdf.cell(50, 10, f"{tot_conf:,.2f}", 1, 1, 'R')
            st.download_button("📄 Scarica Report PDF", data=bytes(pdf.output()), file_name="Report_Arredamento.pdf")

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
                "Oggetto": st.column_config.TextColumn("Nome"),
                "Link": st.column_config.LinkColumn("🔗 Link", display_text="Apri"),
                "Note": st.column_config.TextColumn("Note", width="large"),
                "Prezzo Stimato": st.column_config.NumberColumn("Budget €", format="%.2f"),
            }
            df_edit_wish = st.data_editor(df_display, use_container_width=True, hide_index=True, num_rows="dynamic", column_config=config_wish, key="wish_v6_2")

            if st.button("💾 SALVA WISHLIST"):
                df_to_save = df_edit_wish.drop(columns=['Anteprima'])
                conn.update(worksheet="desideri", data=df_to_save)
                st.balloons()
                st.success("Salvato!")
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
                with st.spinner("Aggiornamento..."):
                    # Trasformazione numerica
                    for col in ['Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo', 'Versato']:
                        df_edit[col] = pd.to_numeric(df_edit[col], errors='coerce').fillna(0)

                    for i in range(len(df_edit)):
                        # Ricalcolo Costo se ci sono PP e Sconto
                        if df_edit.at[i, 'Prezzo Pieno'] > 0 and df_edit.at[i, 'Sconto %'] > 0:
                            df_edit.at[i, 'Costo'] = df_edit.at[i, 'Prezzo Pieno'] * (1 - (df_edit.at[i, 'Sconto %'] / 100))

                        # Ricalcolo Totale
                        tot_riga = df_edit.at[i, 'Costo'] * df_edit.at[i, 'Acquistato']
                        df_edit.at[i, 'Importo Totale'] = tot_riga

                        # Automazione Saldato
                        if df_edit.at[i, 'Stato Pagamento'] == "Saldato":
                            df_edit.at[i, 'Versato'] = tot_riga

                    conn.update(worksheet=selezione, data=df_edit)
                    st.balloons()
                    st.success("Tutto ricalcolato e salvato!")
                    time.sleep(1)
                    st.rerun()
