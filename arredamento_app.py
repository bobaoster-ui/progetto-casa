import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import time

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Monitoraggio Arredamento V7.6", layout="wide", page_icon="🏠")

# Colori
COLOR_AZZURRO = (46, 117, 182)

# --- CLASSE PDF RINFORZATA ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(*COLOR_AZZURRO)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'ESTRATTO CONTO ARREDAMENTO', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        # Regola: Proprietà con à
        testo = f'Proprietà: Jacopo - Report del {datetime.now().strftime("%d/%m/%Y")}'
        self.cell(0, 10, testo.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}', align='C')

# --- FUNZIONE PULIZIA DATI INTELLIGENTE ---
def safe_clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    # Pulizia nomi colonne da spazi extra
    df.columns = [str(c).strip() for c in df.columns]

    # Assicuriamoci che le colonne critiche esistano sempre (evita KeyError)
    colonne_necessarie = {
        'Oggetto': '',
        'Importo Totale': 0.0,
        'Versato': 0.0,
        'Stato Pagamento': 'Da definire',
        'Prezzo Pieno': 0.0,
        'Sconto %': 0.0,
        'Acquistato': 1.0,
        'Costo': 0.0
    }

    for col, default in colonne_necessarie.items():
        if col not in df.columns:
            df[col] = default

    # Conversione numerica sicura
    num_cols = ['Prezzo Pieno', 'Sconto %', 'Acquistato', 'Costo', 'Versato', 'Importo Totale']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

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
    stanze_reali = ["camera", "cucina", "salotto", "tavolo", "lavori"]

    with st.sidebar:
        st.markdown("### 🛠 Sicurezza")
        can_edit_structure = st.toggle("Modifica Struttura", value=False)
        selezione = st.selectbox("Menu Principale:", ["Riepilogo Generale", "✨ Wishlist"] + stanze_reali)
        if st.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()

    # --- 1. RIEPILOGO GENERALE ---
    if selezione == "Riepilogo Generale":
        st.title("🏠 Dashboard Riepilogo")
        try:
            df_imp = conn.read(worksheet="impostazioni", ttl=0)
            budget_max = float(df_imp[df_imp['Parametro'] == 'Budget Totale']['Valore'].values[0])
        except: budget_max = 10000.0

        all_data = []
        tot_conf, tot_versato = 0.0, 0.0

        for s in stanze_reali:
            try:
                raw_s = conn.read(worksheet=s, ttl=0)
                df_s = safe_clean_df(raw_s)
                if not df_s.empty:
                    # Cerca la colonna di conferma (S/N) con nomi flessibili
                    col_conf = next((c for c in ['Acquista S/N', 'S/N', 'Scelta'] if c in df_s.columns), 'Acquista S/N')
                    if col_conf not in df_s.columns: df_s[col_conf] = 'N'

                    df_c = df_s[df_s[col_conf].astype(str).str.upper() == 'S'].copy()
                    if not df_c.empty:
                        df_c['Ambiente'] = s.capitalize()
                        all_data.append(df_c)
                        tot_conf += df_c['Importo Totale'].sum()
                        tot_versato += df_c['Versato'].sum()
            except: continue

        # Metriche
        st.subheader(f"📊 Budget Totale: {budget_max:,.2f} €")
        st.progress(min(tot_conf / budget_max, 1.0) if budget_max > 0 else 0)
        m1, m2, m3 = st.columns(3)
        m1.metric("CONFERMATO", f"{tot_conf:,.2f} €")
        m2.metric("PAGATO", f"{tot_versato:,.2f} €")
        m3.metric("RESIDUO", f"{(tot_conf - tot_versato):,.2f} €")

        if all_data:
            df_final = pd.concat(all_data)

            # Grafici protetti
            g1, g2 = st.columns(2)
            with g1:
                df_pie = df_final.groupby('Ambiente')['Importo Totale'].sum().reset_index()
                st.plotly_chart(px.pie(df_pie, values='Importo Totale', names='Ambiente', title="Spesa per Stanza", hole=0.4), use_container_width=True)
            with g2:
                df_bar = pd.DataFrame({"Stato": ["Pagato", "Residuo"], "Euro": [tot_versato, max(0, tot_conf - tot_versato)]})
                st.plotly_chart(px.bar(df_bar, x="Stato", y="Euro", color="Stato", color_discrete_map={"Pagato":"#2ECC71","Residuo":"#E74C3C"}), use_container_width=True)

            st.dataframe(df_final[['Ambiente', 'Oggetto', 'Importo Totale', 'Versato', 'Stato Pagamento']], use_container_width=True, hide_index=True)

            # --- PDF FIX ---
            if st.button("📄 Genera Report PDF"):
                try:
                    pdf = PDF()
                    pdf.add_page()
                    pdf.set_font('Arial', 'B', 10)
                    pdf.set_fill_color(*COLOR_AZZURRO); pdf.set_text_color(255,255,255)
                    pdf.cell(30, 10, 'Stanza', 1, 0, 'C', True)
                    pdf.cell(80, 10, 'Oggetto', 1, 0, 'C', True)
                    pdf.cell(35, 10, 'Totale', 1, 0, 'C', True)
                    pdf.cell(35, 10, 'Versato', 1, 1, 'C', True)

                    pdf.set_font('Arial', '', 9); pdf.set_text_color(0,0,0)
                    for _, row in df_final.iterrows():
                        pdf.cell(30, 8, str(row['Ambiente']), 1)
                        # Pulizia testo per PDF
                        ogg = str(row['Oggetto'])[:40].encode('latin-1', 'replace').decode('latin-1')
                        pdf.cell(80, 8, ogg, 1)
                        pdf.cell(35, 8, f"{row['Importo Totale']:,.2f}", 1, 0, 'R')
                        pdf.cell(35, 8, f"{row['Versato']:,.2f}", 1, 1, 'R')

                    pdf_out = pdf.output(dest='S')
                    # Forza formato byte per Streamlit
                    if isinstance(pdf_out, str): pdf_out = pdf_out.encode('latin-1')
                    st.download_button("📥 Scarica Report", data=pdf_out, file_name="Report_Jacopo.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"Errore PDF: {e}")
        else:
            st.info("Nessun articolo confermato (S) trovato. I grafici appariranno quando confermerai gli acquisti!")

    # --- 2. STANZE ---
    elif selezione in stanze_reali:
        st.title(f"🏠 {selezione.capitalize()}")
        try:
            raw_data = conn.read(worksheet=selezione, ttl=0)
            df = safe_clean_df(raw_data)

            with st.form(f"form_{selezione}"):
                df_edit = st.data_editor(df, use_container_width=True, hide_index=True,
                                        num_rows="dynamic" if can_edit_structure else "fixed")
                submit = st.form_submit_button("💾 SALVA")

            if submit:
                for i in range(len(df_edit)):
                    try:
                        p = float(df_edit.at[i, 'Prezzo Pieno'])
                        s = float(df_edit.at[i, 'Sconto %'])
                        q = float(df_edit.at[i, 'Acquistato'])
                        costo = p * (1 - (s/100)) if p > 0 else float(df_edit.at[i, 'Costo'])
                        df_edit.at[i, 'Costo'] = costo
                        df_edit.at[i, 'Importo Totale'] = costo * q
                        if str(df_edit.at[i, 'Stato Pagamento']) == "Saldato":
                            df_edit.at[i, 'Versato'] = df_edit.at[i, 'Importo Totale']
                    except: continue

                conn.update(worksheet=selezione, data=df_edit)
                st.success("Dati sincronizzati!"); time.sleep(1); st.rerun()
        except Exception as e:
            st.error(f"Errore caricamento: {e}")

    # --- 3. WISHLIST ---
    elif selezione == "✨ Wishlist":
        st.title("✨ Wishlist")
        try:
            df_w = safe_clean_df(conn.read(worksheet="desideri", ttl=0))
            df_ed_w = st.data_editor(df_w, use_container_width=True, hide_index=True)
            if st.button("Salva Wishlist"):
                conn.update(worksheet="desideri", data=df_ed_w)
                st.success("Wishlist salvata!"); st.rerun()
        except: st.error("Errore wishlist.")
