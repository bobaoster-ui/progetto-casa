import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento v2.1", layout="wide", page_icon="🏠")

# --- FUNZIONE DI LOGIN ---
def check_password():
    def password_entered():
        if (st.session_state["username"] == st.secrets["auth"]["username"] and
            st.session_state["password"] == st.secrets["auth"]["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Accesso Riservato")
        st.text_input("Utente", key="username")
        st.text_input("Password", type="password", key="password")
        if st.button("Accedi"):
            password_entered()
            st.rerun()
        return False
    return st.session_state.get("password_correct", False)

# --- ESECUZIONE APP ---
if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)

    if st.sidebar.button("Logout 🚪"):
        st.session_state.clear()
        st.rerun()

    st.title("🏠 Gestione Arredamento Professionale")

    stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]
    opzioni_menu = ["Riepilogo Generale"] + stanze_reali
    selezione = st.sidebar.selectbox("Naviga tra le sezioni:", opzioni_menu)

    if selezione == "Riepilogo Generale":
        st.subheader("📊 Analisi Budget e Investimenti")

        totale_confermato = 0
        totale_potenziale = 0
        dati_per_grafico = []
        lista_completa_acquisto = []

        with st.spinner("Calcolo in corso..."):
            for s in stanze_reali:
                try:
                    temp_df = conn.read(worksheet=s, ttl=0)
                    if temp_df is not None and not temp_df.empty:
                        temp_df.columns = [str(c).strip() for c in temp_df.columns]
                        col_prezzo = next((c for c in ['Importo Totale', 'Totale'] if c in temp_df.columns), None)
                        col_scelta = next((c for c in ['Acquista S/N', 'S/N'] if c in temp_df.columns), None)

                        if col_prezzo:
                            temp_df[col_prezzo] = pd.to_numeric(temp_df[col_prezzo], errors='coerce').fillna(0)
                            s_pot = temp_df[col_prezzo].sum()
                            totale_potenziale += s_pot

                            s_conf = 0
                            if col_scelta:
                                temp_df[col_scelta] = temp_df[col_scelta].astype(str).str.upper()
                                df_conf = temp_df[temp_df[col_scelta] == 'S'].copy()
                                s_conf = df_conf[col_prezzo].sum()
                                totale_confermato += s_conf
                                if not df_conf.empty:
                                    df_conf['Stanza'] = s.capitalize()
                                    lista_completa_acquisto.append(df_conf)

                            dati_per_grafico.append({"Stanza": s.capitalize(), "Confermato": s_conf, "Totale": s_pot})
                except: continue

        # Metriche
        c1, c2, c3 = st.columns(3)
        c1.metric("DA PAGARE (S)", f"{totale_confermato:,.2f} €")
        c2.metric("BUDGET TOTALE (S+N)", f"{totale_potenziale:,.2f} €")
        c3.metric("RISPARMIO POTENZIALE", f"{totale_potenziale - totale_confermato:,.2f} €")

        # --- EXPORT EXCEL PROFESSIONALE ---
        if lista_completa_acquisto:
            df_final_export = pd.concat(lista_completa_acquisto, ignore_index=True)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final_export.to_excel(writer, index=False, sheet_name='Lista_Spesa', startrow=4)

                workbook  = writer.book
                worksheet = writer.sheets['Lista_Spesa']

                # Formati
                fmt_header = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': 'white', 'bg_color': '#2E75B6', 'align': 'center'})
                fmt_date = workbook.add_format({'italic': True, 'font_size': 10})
                fmt_money = workbook.add_format({'num_format': '#,##0.00 €'})

                # Intestazione Grafica
                worksheet.merge_range('A1:E1', 'REPORT SPESE ARREDAMENTO - JACOPO', fmt_header)
                worksheet.write('A2', f'Data generazione: {datetime.now().strftime("%d/%m/%Y %H:%M")}', fmt_date)
                worksheet.write('A3', f'Totale Investimento Confermato: {totale_confermato:,.2f} €', workbook.add_format({'bold': True}))

                # Regolazione larghezza colonne
                for i, col in enumerate(df_final_export.columns):
                    worksheet.set_column(i, i, 20)

            st.sidebar.download_button(
                label="📥 Scarica Report Jacopo (Excel)",
                data=output.getvalue(),
                file_name=f"Report_Arredamento_Jacopo_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        if dati_per_grafico:
            df_plot = pd.DataFrame(dati_per_grafico)
            fig = px.bar(df_plot, x="Stanza", y=["Confermato", "Totale"], barmode="group",
                         title="Analisi per Stanza", color_discrete_sequence=["#2ecc71", "#3498db"])
            st.plotly_chart(fig, use_container_width=True)

    else:
        # (Codice stanza singola rimane identico a prima per stabilità)
        st.subheader(f"Ambiente: {selezione.capitalize()}")
        try:
            df = conn.read(worksheet=selezione, ttl=0)
            if df is not None:
                df.columns = [str(c).strip() for c in df.columns]
                col_prezzo = next((c for c in ['Costo', 'Prezzo'] if c in df.columns), None)
                col_quantita = next((c for c in ['Acquistato', 'Quantità'] if c in df.columns), None)
                col_totale = next((c for c in ['Importo Totale', 'Totale'] if c in df.columns), None)
                col_scelta = next((c for c in ['Acquista S/N', 'S/N'] if c in df.columns), None)

                if col_totale in df.columns:
                    df = df.sort_values(by=col_totale, ascending=False)

                config_colonne = {
                    col_prezzo: st.column_config.NumberColumn(format="%.2f €"),
                    col_totale: st.column_config.NumberColumn(format="%.2f €", disabled=True)
                }
                if col_scelta:
                    config_colonne[col_scelta] = st.column_config.SelectboxColumn("Stato", options=["S", "N"])

                df_edit = st.data_editor(df, use_container_width=True, hide_index=True,
                                         column_config=config_colonne, num_rows="dynamic", key=f"ed_{selezione}")

                if st.button(f"💾 SALVA {selezione.upper()}"):
                    df_save = df_edit.dropna(how='all').copy()
                    if col_prezzo and col_quantita and col_totale:
                        p = pd.to_numeric(df_save[col_prezzo].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                        q = pd.to_numeric(df_save[col_quantita], errors='coerce').fillna(0)
                        df_save[col_totale] = (p * q).round(2)
                    conn.update(worksheet=selezione, data=df_save)
                    st.success("Salvataggio completato!")
                    st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")
