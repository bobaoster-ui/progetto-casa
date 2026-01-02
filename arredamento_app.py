import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento V5.1", layout="wide", page_icon="🏠")

# Palette Colori
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

    # --- 1. RIEPILOGO GENERALE (Con Budget Alert!) ---
    if selezione == "Riepilogo Generale":
        st.title("🏠 Dashboard Riepilogo")

        # Lettura Impostazioni
        try:
            df_imp = conn.read(worksheet="impostazioni", ttl="5s")
            budget_max = float(df_imp[df_imp['Parametro'] == 'Budget Totale']['Valore'].values[0])
        except:
            budget_max = 10000.0 # Valore di backup
            st.warning("Impossibile leggere il Budget Totale dal foglio 'impostazioni'. Uso valore predefinito 10.000€")

        lista_solo_confermati = []
        tot_conf, tot_potenziale = 0, 0
        dati_per_grafico = []

        for s in stanze_reali:
            try:
                df_s = conn.read(worksheet=s, ttl="10s")
                if df_s is not None and not df_s.empty:
                    df_s.columns = [str(c).strip() for c in df_s.columns]
                    col_p = next((c for c in ['Importo Totale', 'Totale', 'Prezzo', 'Costo'] if c in df_s.columns), None)
                    col_s = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df_s.columns), None)
                    col_o = next((c for c in ['Oggetto', 'Articolo', 'Descrizione'] if c in df_s.columns), df_s.columns[0])

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

        # --- SEZIONE BUDGET ALERT ---
        percentuale = min(tot_conf / budget_max, 1.2) # Max 120% per la barra

        st.subheader(f"📊 Stato del Budget (Limite: {budget_max:,.2f} EUR)")

        if percentuale < 0.7:
            st.progress(percentuale, text=f"Ottimo! Hai speso il {percentuale:.1%}")
            st.success(f"Sei ampiamente nel budget. Ti restano {(budget_max - tot_conf):,.2f} EUR")
        elif percentuale < 0.9:
            st.progress(percentuale, text=f"Attenzione! Sei al {percentuale:.1%}")
            st.warning(f"Ti stai avvicinando al limite. Budget residuo: {(budget_max - tot_conf):,.2f} EUR")
        else:
            st.progress(percentuale, text=f"ALLERTA! Sei al {percentuale:.1%}")
            st.error(f"⚠️ Budget quasi esaurito o superato! Residuo: {(budget_max - tot_conf):,.2f} EUR")

        st.divider()

        m1, m2, m3 = st.columns(3)
        m1.metric("CONFERMATO (S)", f"{tot_conf:,.2f} EUR")
        m2.metric("RESIDUO (N)", f"{(tot_potenziale - tot_conf):,.2f} EUR")
        m3.metric("EFFETTIVO vs TARGET", f"{percentuale:.1%}")

        if dati_per_grafico:
            df_plot = pd.DataFrame(dati_per_grafico)
            fig = px.pie(df_plot, values='Budget', names='Stanza', title="Ripartizione Budget Totale", color_discrete_sequence=COLOR_PALETTE)
            st.plotly_chart(fig, use_container_width=True)

        if lista_solo_confermati:
            df_final = pd.concat(lista_solo_confermati)
            st.dataframe(df_final, use_container_width=True, hide_index=True)
            pdf = PDF()
            pdf.add_page()
            st.download_button("📄 Scarica Report PDF", data=bytes(pdf.output()), file_name="Report_Arredamento.pdf")

    # --- 2. WISHLIST ---
    elif selezione == "✨ Wishlist":
        st.title("✨ La Tua Wishlist Visiva")
        df_wish = conn.read(worksheet="desideri", ttl="5s")
        if df_wish is not None:
            df_wish.columns = [str(c).strip() for c in df_wish.columns]
            df_display = df_wish.copy()
            df_display['Anteprima'] = df_display['Foto']
            config_wish = {
                "Anteprima": st.column_config.ImageColumn("Preview", width="medium"),
                "Oggetto": st.column_config.TextColumn("Nome Oggetto", width="medium"),
                "Foto": st.column_config.TextColumn("🔗 Link Foto"),
                "Prezzo Stimato": st.column_config.NumberColumn("Prezzo (EUR)", format="%.2f"),
            }
            df_edit_wish = st.data_editor(df_display, use_container_width=True, hide_index=True, num_rows="dynamic", column_config=config_wish, key="wish_v5_1")
            if st.button("💾 SALVA MODIFICHE"):
                with st.spinner("Salvataggio..."):
                    df_to_save = df_edit_wish.drop(columns=['Anteprima'])
                    conn.update(worksheet="desideri", data=df_to_save)
                    st.success("Salvato!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()

    # --- 3. STANZE ---
    else:
        st.title(f"🏠 {selezione.capitalize()}")
        df = conn.read(worksheet=selezione, ttl="5s")
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            col_s = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df.columns), None)
            col_p = next((c for c in ['Importo Totale', 'Totale', 'Prezzo', 'Costo'] if c in df.columns), None)
            config_stanza = {
                col_s: st.column_config.SelectboxColumn("Scelta", options=["S", "N"]),
                "Prezzo Pieno": st.column_config.NumberColumn("Prezzo Listino", format="%.2f EUR"),
                "Sconto %": st.column_config.NumberColumn("Sconto %", format="%d%%"),
                col_p: st.column_config.NumberColumn("Prezzo Finale", format="%.2f EUR")
            }
            df_edit = st.data_editor(df, use_container_width=True, hide_index=True, num_rows="dynamic", column_config=config_stanza, key=f"ed_{selezione}")
            if st.button("💾 SALVA E CALCOLA"):
                with st.spinner("Aggiornamento..."):
                    if "Prezzo Pieno" in df_edit.columns and "Sconto %" in df_edit.columns and col_p:
                        df_edit[col_p] = df_edit.apply(
                            lambda row: row["Prezzo Pieno"] * (1 - (row["Sconto %"] / 100))
                            if pd.notnull(row["Prezzo Pieno"]) and pd.notnull(row["Sconto %"])
                            else row[col_p], axis=1
                        )
                    conn.update(worksheet=selezione, data=df_edit)
                    st.success("Salvataggio e calcoli completati!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
